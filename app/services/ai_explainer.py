import logging
import os
from typing import Optional

from app.models.models import Crop, SensorData

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"
REQUEST_TIMEOUT_SECONDS = 5.0


def generate_explanation(
    sensor: SensorData,
    crop: Crop,
    decision: dict,
    fallback_reason: str,
    weather: Optional[dict] = None,
    growth_stage: Optional[dict] = None,
) -> str:
    """Generate a farmer-friendly explanation via OpenRouter.

    Returns the original rule-based reason if the API key is missing or the call fails,
    so the caller can use the result unconditionally.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return fallback_reason

    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        prompt = _build_prompt(sensor, crop, decision, weather, growth_stage)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an irrigation advisor for farmers. Given sensor "
                        "readings and a computed irrigation decision, write a concise "
                        "1-2 sentence explanation that a farmer can act on. "
                        "Reference the specific numbers when relevant. "
                        "Do not greet, do not add disclaimers, do not use markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=120,
        )

        text: Optional[str] = response.choices[0].message.content
        if text:
            return text.strip()
        return fallback_reason

    except Exception as e:
        logger.warning("OpenRouter explanation failed, using rule-based reason: %s", e)
        return fallback_reason


def _build_prompt(
    sensor: SensorData,
    crop: Crop,
    decision: dict,
    weather: Optional[dict] = None,
    growth_stage: Optional[dict] = None,
) -> str:
    lines = [
        f"Crop: {crop.name}"
        + (f" ({crop.species})" if crop.species else ""),
        f"Soil moisture thresholds: {crop.min_soil_moisture}% min, {crop.max_soil_moisture}% max",
    ]
    if crop.optimal_temperature_min is not None and crop.optimal_temperature_max is not None:
        lines.append(
            f"Optimal temperature range: {crop.optimal_temperature_min}-{crop.optimal_temperature_max}°C"
        )

    lines.append("")
    lines.append("Current sensor readings:")
    lines.append(f"- Soil moisture: {sensor.soil_moisture}%")
    lines.append(f"- Temperature: {sensor.temperature}°C")
    if sensor.humidity is not None:
        lines.append(f"- Humidity: {sensor.humidity}%")
    if sensor.rainfall_mm is not None:
        lines.append(f"- Recent rainfall: {sensor.rainfall_mm}mm")

    if growth_stage:
        lines.append("")
        lines.append("Crop growth stage (estimated from GDD since planting):")
        lines.append(f"- Stage: {growth_stage.get('stage')}")
        lines.append(f"- Days since planting: {growth_stage.get('days_since_planted')}")
        lines.append(f"- Cumulative GDD: {growth_stage.get('gdd_cumulative')}")
        if growth_stage.get("description"):
            lines.append(f"- Note: {growth_stage['description']}")

    if weather:
        forecast = weather.get("forecast", {})
        lines.append("")
        lines.append("Live weather forecast (Open-Meteo):")
        if forecast.get("rainfall_next_24h_mm") is not None:
            lines.append(f"- Rainfall expected next 24h: {forecast['rainfall_next_24h_mm']}mm")
        if forecast.get("et0_today_mm"):
            lines.append(f"- Reference evapotranspiration today: {forecast['et0_today_mm']}mm")
        if forecast.get("summary"):
            lines.append(f"- Summary: {forecast['summary']}")

    lines.append("")
    lines.append("Computed decision:")
    lines.append(f"- Water stress index: {decision['water_stress_index']} (0-1 scale)")
    lines.append(f"- Stress level: {decision['stress_level']}")
    lines.append(f"- Should irrigate: {decision['should_irrigate']}")
    if decision.get("recommended_water_mm"):
        lines.append(f"- Recommended water: {decision['recommended_water_mm']}mm")

    lines.append("")
    lines.append(
        "Write the explanation now. If forecast rain is significant, mention it. "
        "If the crop is in a sensitive growth stage (flowering/fruiting), reference that."
    )
    return "\n".join(lines)
