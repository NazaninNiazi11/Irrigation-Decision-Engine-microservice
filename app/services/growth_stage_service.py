"""Growing Degree Days (GDD) based crop growth-stage estimation.

Uses Open-Meteo daily mean temperatures since the crop's planting date to compute
cumulative GDD with a base temperature of 10°C, then maps that to a generic stage
with stage-specific water/moisture multipliers.

This is a SIMPLIFIED, generic model — real agronomy uses crop-specific GDD curves.
For a demo/MVP, the generic thresholds below are reasonable for warm-season crops.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.models.models import Crop

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 5.0
BASE_TEMPERATURE_C = 10.0
MAX_PAST_DAYS = 92  # Open-Meteo forecast endpoint limit

# Generic GDD-to-stage mapping (cumulative GDD since planting, base 10°C)
# Each stage has water and moisture-threshold multipliers that scale the crop's
# default values. Flowering is the most water-sensitive stage.
_STAGE_MAP = [
    # (max_gdd, name, water_multiplier, moisture_min_multiplier, description)
    (200,  "Germination / Establishment", 0.7, 0.9,  "Seedlings establishing — light, frequent watering."),
    (500,  "Vegetative Growth",           1.0, 1.0,  "Canopy expanding — standard watering schedule."),
    (900,  "Flowering / Reproductive",    1.3, 1.1,  "Peak water demand — water stress now hurts yield most."),
    (1400, "Fruiting / Grain Fill",       1.2, 1.05, "Filling fruit/grain — maintain steady moisture."),
    (10_000, "Maturation",                0.6, 0.85, "Approaching harvest — reduce irrigation to ripen crop."),
]

_cache: dict[tuple, dict] = {}


def compute_growth_stage(crop: Crop) -> Optional[dict]:
    """Estimate the crop's current growth stage from cumulative GDD.

    Returns None if the crop is missing planting date or coordinates, or if the
    historical-weather call fails — callers should treat absence as "unknown stage."
    """
    if crop.planted_on is None or crop.latitude is None or crop.longitude is None:
        return None

    today = datetime.now(timezone.utc).date()
    planted_date = crop.planted_on.date() if hasattr(crop.planted_on, "date") else crop.planted_on
    days_since_planted = (today - planted_date).days
    if days_since_planted < 0:
        return None  # Planted in the future

    cache_key = (crop.id, today.isoformat())
    if cache_key in _cache:
        return _cache[cache_key]

    past_days = min(days_since_planted, MAX_PAST_DAYS)
    if past_days == 0:
        # Planted today — no history to fetch, just report germination
        result = _build_result("Germination / Establishment", 0.0, 0, 0.7, 0.9,
                               "Just planted — light, frequent watering until establishment.")
        _cache[cache_key] = result
        return result

    daily_means = _fetch_daily_mean_temps(crop.latitude, crop.longitude, past_days)
    if daily_means is None:
        return None

    gdd = sum(max(0.0, t - BASE_TEMPERATURE_C) for t in daily_means if t is not None)
    capped = days_since_planted > MAX_PAST_DAYS

    name, water_mult, moisture_mult, desc = _stage_for_gdd(gdd)
    result = _build_result(name, gdd, days_since_planted, water_mult, moisture_mult, desc, capped=capped)
    _cache[cache_key] = result
    return result


def _stage_for_gdd(gdd: float) -> tuple[str, float, float, str]:
    for max_gdd, name, water_mult, moisture_mult, desc in _STAGE_MAP:
        if gdd <= max_gdd:
            return name, water_mult, moisture_mult, desc
    # Fallthrough (shouldn't happen given 10_000 ceiling)
    last = _STAGE_MAP[-1]
    return last[1], last[2], last[3], last[4]


def _build_result(name: str, gdd: float, days: int, water_mult: float, moisture_mult: float,
                  description: str, capped: bool = False) -> dict:
    summary = f"{name} — Day {days}, {round(gdd)} GDD"
    if capped:
        summary += f" (history capped at {MAX_PAST_DAYS} days)"
    return {
        "stage": name,
        "gdd_cumulative": round(gdd, 1),
        "days_since_planted": days,
        "water_multiplier": water_mult,
        "moisture_min_multiplier": moisture_mult,
        "description": description,
        "summary": summary,
        "history_capped": capped,
    }


def _fetch_daily_mean_temps(lat: float, lon: float, past_days: int) -> Optional[list]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_mean",
        "past_days": past_days,
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        response = httpx.get(OPEN_METEO_FORECAST_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.warning("Open-Meteo historical fetch failed for (%.2f, %.2f): %s", lat, lon, e)
        return None

    try:
        return data["daily"]["temperature_2m_mean"]
    except (KeyError, TypeError):
        logger.warning("Open-Meteo historical response missing daily temps")
        return None
