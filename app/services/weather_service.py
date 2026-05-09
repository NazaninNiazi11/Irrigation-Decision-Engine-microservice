import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 5.0

_cache: dict[tuple, dict] = {}


def get_current_weather(lat: float, lon: float) -> Optional[dict]:
    """Fetch current weather + 24h forecast for a location.

    Returns None if the API is unreachable or returns invalid data — callers
    should fall back to sensor-only behavior in that case.
    """
    cache_key = (round(lat, 2), round(lon, 2), datetime.now(timezone.utc).strftime("%Y%m%d%H"))
    if cache_key in _cache:
        return _cache[cache_key]

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,shortwave_radiation,soil_moisture_3_to_9cm",
        "hourly": "precipitation",
        "daily": "et0_fao_evapotranspiration",
        "forecast_days": 2,
        "timezone": "auto",
    }

    try:
        response = httpx.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.warning("Open-Meteo fetch failed for (%.2f, %.2f): %s", lat, lon, e)
        return None

    try:
        result = _shape_response(data)
    except (KeyError, IndexError, TypeError, ValueError) as e:
        logger.warning("Open-Meteo response shape unexpected: %s", e)
        return None

    _cache[cache_key] = result
    return result


def _shape_response(data: dict) -> dict:
    current = data["current"]
    hourly = data.get("hourly", {})
    daily = data.get("daily", {})

    rainfall_next_24h = _sum_next_24h(hourly.get("precipitation", []))
    et0_today = float(daily.get("et0_fao_evapotranspiration", [None])[0] or 0)

    if rainfall_next_24h >= 10:
        forecast_summary = f"Heavy rain expected (~{rainfall_next_24h:.0f}mm in next 24h)"
    elif rainfall_next_24h >= 2:
        forecast_summary = f"Light rain expected (~{rainfall_next_24h:.0f}mm in next 24h)"
    else:
        forecast_summary = "No significant rainfall in next 24h"

    # Open-Meteo reports soil moisture in m³/m³ (e.g. 0.28 = 28% volumetric).
    # Multiply by 100 to match the app's 0-100 percentage convention.
    soil_moisture_raw = current.get("soil_moisture_3_to_9cm")
    soil_moisture_pct = round(float(soil_moisture_raw) * 100, 1) if soil_moisture_raw is not None else None

    return {
        "current": {
            "temperature": float(current.get("temperature_2m") or 0),
            "humidity": float(current.get("relative_humidity_2m") or 0),
            "rainfall_mm": float(current.get("precipitation") or 0),
            "wind_speed": float(current.get("wind_speed_10m") or 0),
            "solar_radiation": float(current.get("shortwave_radiation") or 0),
            "soil_moisture": soil_moisture_pct,
            "soil_moisture_source": "satellite_estimate" if soil_moisture_pct is not None else None,
        },
        "forecast": {
            "rainfall_next_24h_mm": round(rainfall_next_24h, 1),
            "et0_today_mm": round(et0_today, 2),
            "summary": forecast_summary,
        },
        "source": "Open-Meteo",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _sum_next_24h(hourly_precip: list) -> float:
    if not hourly_precip:
        return 0.0
    # Take the first 24 valid hours from the hourly forecast
    values = [float(v) for v in hourly_precip[:24] if v is not None]
    return sum(values)
