from typing import Optional

from sqlalchemy.orm import Session
from app.models.models import Crop, SensorData, IrrigationDecision
from app.services.ai_explainer import generate_explanation
from app.services import weather_service, growth_stage_service


class IrrigationService:
    """Core service that calculates water stress and makes irrigation decisions."""

    @staticmethod
    def calculate_water_stress(
        sensor: SensorData,
        crop: Crop,
        weather: Optional[dict] = None,
        growth_stage: Optional[dict] = None,
    ) -> dict:
        """
        Calculate water stress index based on sensor data and crop requirements.

        Returns:
            dict with water_stress_index (0-1), stress_level, should_irrigate,
            recommended_water_mm, and reason.
        """
        # --- Apply growth-stage adjustments to thresholds ---
        # Flowering/fruiting crops are thirstier, so we scale up the effective
        # min_soil_moisture and water_requirement.
        moisture_min_mult = (growth_stage or {}).get("moisture_min_multiplier", 1.0)
        water_mult = (growth_stage or {}).get("water_multiplier", 1.0)
        effective_min_moisture = min(crop.min_soil_moisture * moisture_min_mult, crop.max_soil_moisture - 1)

        # --- Water stress index calculation ---
        # Moisture deficit component (0-1): how far below optimal
        moisture_midpoint = (effective_min_moisture + crop.max_soil_moisture) / 2
        if sensor.soil_moisture < effective_min_moisture:
            moisture_stress = 1.0
        elif sensor.soil_moisture < moisture_midpoint:
            moisture_stress = (moisture_midpoint - sensor.soil_moisture) / (moisture_midpoint - effective_min_moisture)
        elif sensor.soil_moisture <= crop.max_soil_moisture:
            moisture_stress = 0.0
        else:
            moisture_stress = 0.2  # Over-saturated, slight stress

        # Temperature stress component (0-1)
        temp_stress = 0.0
        if crop.optimal_temperature_min and crop.optimal_temperature_max:
            if sensor.temperature < crop.optimal_temperature_min:
                temp_stress = min((crop.optimal_temperature_min - sensor.temperature) / 10, 1.0)
            elif sensor.temperature > crop.optimal_temperature_max:
                temp_stress = min((sensor.temperature - crop.optimal_temperature_max) / 10, 1.0)

        # Humidity adjustment: low humidity increases evaporation stress
        humidity_factor = 0.0
        if sensor.humidity is not None and sensor.humidity < 30:
            humidity_factor = (30 - sensor.humidity) / 100

        # Combined water stress index (weighted)
        water_stress_index = round(
            min(moisture_stress * 0.6 + temp_stress * 0.25 + humidity_factor * 0.15, 1.0), 3
        )

        # --- Decision logic ---
        if water_stress_index >= 0.7:
            stress_level = "critical"
            should_irrigate = True
            reason = "Critical water stress detected. Immediate irrigation required."
        elif water_stress_index >= 0.5:
            stress_level = "high"
            should_irrigate = True
            reason = "High water stress. Irrigation recommended within 2 hours."
        elif water_stress_index >= 0.3:
            stress_level = "moderate"
            should_irrigate = True
            reason = "Moderate water stress. Irrigation recommended within 6 hours."
        else:
            stress_level = "low"
            should_irrigate = False
            reason = "Soil moisture and conditions are within acceptable range."

        # Adjust for recent rainfall (sensor reading)
        if sensor.rainfall_mm and sensor.rainfall_mm > 5:
            should_irrigate = False
            reason += f" Recent rainfall ({sensor.rainfall_mm}mm) detected — irrigation skipped."

        # Adjust for forecasted rainfall (live weather)
        forecast_rain = (weather or {}).get("forecast", {}).get("rainfall_next_24h_mm", 0) or 0
        if should_irrigate and forecast_rain >= 5:
            should_irrigate = False
            reason += f" Forecast shows ~{forecast_rain:.0f}mm of rain in next 24h — irrigation deferred."

        # Recommended water amount (scaled by growth stage and ET₀ if available)
        recommended_water_mm = None
        if should_irrigate and crop.water_requirement_mm:
            deficit_ratio = max(moisture_stress, 0.3)
            recommended_water_mm = round(crop.water_requirement_mm * deficit_ratio * water_mult, 1)
            et0 = (weather or {}).get("forecast", {}).get("et0_today_mm")
            if et0 and et0 > 0:
                # Scale relative to a "typical" ET₀ of 4mm/day
                et0_factor = min(max(et0 / 4.0, 0.5), 2.0)
                recommended_water_mm = round(recommended_water_mm * et0_factor, 1)

        return {
            "water_stress_index": water_stress_index,
            "stress_level": stress_level,
            "should_irrigate": should_irrigate,
            "recommended_water_mm": recommended_water_mm,
            "reason": reason,
        }

    @staticmethod
    def evaluate_and_store(db: Session, sensor_data_id: int) -> IrrigationDecision:
        """Evaluate sensor data and store an irrigation decision."""
        sensor = db.query(SensorData).filter(SensorData.id == sensor_data_id).first()
        if not sensor:
            raise ValueError(f"SensorData with id {sensor_data_id} not found")

        crop = db.query(Crop).filter(Crop.id == sensor.crop_id).first()
        if not crop:
            raise ValueError(f"Crop with id {sensor.crop_id} not found")

        weather = None
        if crop.latitude is not None and crop.longitude is not None:
            weather = weather_service.get_current_weather(crop.latitude, crop.longitude)

        growth_stage = growth_stage_service.compute_growth_stage(crop)

        result = IrrigationService.calculate_water_stress(
            sensor, crop, weather=weather, growth_stage=growth_stage
        )

        result["reason"] = generate_explanation(
            sensor=sensor,
            crop=crop,
            decision=result,
            fallback_reason=result["reason"],
            weather=weather,
            growth_stage=growth_stage,
        )

        decision = IrrigationDecision(
            crop_id=crop.id,
            sensor_data_id=sensor.id,
            water_stress_index=result["water_stress_index"],
            stress_level=result["stress_level"],
            should_irrigate=result["should_irrigate"],
            recommended_water_mm=result["recommended_water_mm"],
            reason=result["reason"],
            growth_stage=(growth_stage or {}).get("summary"),
            status="pending",
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)
        return decision
