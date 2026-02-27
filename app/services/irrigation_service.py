from sqlalchemy.orm import Session
from app.models.models import Crop, SensorData, IrrigationDecision


class IrrigationService:
    """Core service that calculates water stress and makes irrigation decisions."""

    @staticmethod
    def calculate_water_stress(sensor: SensorData, crop: Crop) -> dict:
        """
        Calculate water stress index based on sensor data and crop requirements.

        Returns:
            dict with water_stress_index (0-1), stress_level, should_irrigate,
            recommended_water_mm, and reason.
        """
        # --- Water stress index calculation ---
        # Moisture deficit component (0-1): how far below optimal
        moisture_midpoint = (crop.min_soil_moisture + crop.max_soil_moisture) / 2
        if sensor.soil_moisture < crop.min_soil_moisture:
            moisture_stress = 1.0
        elif sensor.soil_moisture < moisture_midpoint:
            moisture_stress = (moisture_midpoint - sensor.soil_moisture) / (moisture_midpoint - crop.min_soil_moisture)
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

        # Adjust for recent rainfall
        if sensor.rainfall_mm and sensor.rainfall_mm > 5:
            should_irrigate = False
            reason += f" Recent rainfall ({sensor.rainfall_mm}mm) detected — irrigation skipped."

        # Recommended water amount
        recommended_water_mm = None
        if should_irrigate and crop.water_requirement_mm:
            deficit_ratio = max(moisture_stress, 0.3)
            recommended_water_mm = round(crop.water_requirement_mm * deficit_ratio, 1)

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
            raise ValueError(f"SensorData with id {sensor_
