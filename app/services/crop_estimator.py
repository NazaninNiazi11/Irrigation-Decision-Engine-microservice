import json
import logging
import os
from typing import Optional

from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.schemas import EstimatedCropResponse

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-haiku-4.5"
REQUEST_TIMEOUT_SECONDS = 15.0

_client = None
_cache: dict[str, EstimatedCropResponse] = {}


def _get_client():
    """Lazy module-level OpenAI client (cached across requests)."""
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AI estimation is not configured. Set OPENROUTER_API_KEY in .env.",
        )

    from openai import OpenAI

    _client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return _client


def estimate_crop_parameters(name: str, species: Optional[str] = None) -> EstimatedCropResponse:
    """Use an LLM to estimate irrigation parameters for an unknown crop.

    Returns an EstimatedCropResponse the caller can present to the user for review.
    Raises HTTPException(422) if the model returns unusable output.
    Raises HTTPException(503) if the AI service is unavailable.
    """
    cache_key = f"{name.strip().lower()}|{(species or '').strip().lower()}"
    if cache_key in _cache:
        return _cache[cache_key]

    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    client = _get_client()

    user_prompt = _build_prompt(name, species)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=400,
        )
        raw = response.choices[0].message.content or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("OpenRouter crop estimation failed for '%s': %s", name, e)
        raise HTTPException(
            status_code=503,
            detail="Could not reach the AI service. Please enter values manually.",
        )

    estimate = _parse_and_validate(raw, name)

    _cache[cache_key] = estimate
    return estimate


_SYSTEM_PROMPT = (
    "You are an agricultural irrigation expert. Given a crop name, return its typical "
    "irrigation parameters as a JSON object. Use FAO-56 reference values where you know "
    "them. If the crop is obscure or you are uncertain, set confidence to \"low\" and "
    "explain in the notes. Always return valid JSON matching the requested schema exactly."
)


def _build_prompt(name: str, species: Optional[str]) -> str:
    species_line = f"\nSpecies (if helpful): {species}" if species else ""
    return (
        f"Crop name: {name}{species_line}\n\n"
        "Return ONLY a JSON object with this exact schema:\n"
        "{\n"
        '  "name": string,\n'
        '  "species": string (Latin binomial),\n'
        '  "min_soil_moisture": number (0-100, percent),\n'
        '  "max_soil_moisture": number (0-100, percent),\n'
        '  "optimal_temperature_min": number (degrees Celsius),\n'
        '  "optimal_temperature_max": number (degrees Celsius),\n'
        '  "water_requirement_mm": number (mm per day),\n'
        '  "confidence": "high" | "medium" | "low",\n'
        '  "notes": string (1-2 sentences explaining your reasoning and any caveats)\n'
        "}"
    )


def _extract_json(raw: str) -> str:
    """Extract a JSON object from the model's response.

    Handles models that wrap JSON in ```json fences or add prose around it,
    even when JSON mode was requested.
    """
    text = raw.strip()
    if text.startswith("```"):
        # Strip a fenced block: ```json\n...\n``` or ```\n...\n```
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text.lstrip("`")
        if text.lower().startswith("json\n"):
            text = text[5:]
        elif text.lower().startswith("json"):
            text = text[4:].lstrip()
        text = text.rstrip("`").strip()

    # Fallback: slice from first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object found in response")
    return text[start : end + 1]


def _parse_and_validate(raw: str, requested_name: str) -> EstimatedCropResponse:
    try:
        data = json.loads(_extract_json(raw))
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("AI returned non-JSON for '%s': %s | raw=%r", requested_name, e, raw[:300])
        raise HTTPException(
            status_code=422,
            detail="The AI returned an invalid response. Please enter values manually.",
        )

    # Bounds clamping (defensive — model occasionally outputs out-of-range values)
    if "min_soil_moisture" in data:
        data["min_soil_moisture"] = max(0.0, min(100.0, float(data["min_soil_moisture"])))
    if "max_soil_moisture" in data:
        data["max_soil_moisture"] = max(0.0, min(100.0, float(data["max_soil_moisture"])))
    if "water_requirement_mm" in data:
        data["water_requirement_mm"] = max(0.0, float(data["water_requirement_mm"]))

    data.pop("source", None)  # ignore any "source" field from the LLM; we set it ourselves
    try:
        return EstimatedCropResponse(**data, source="ai_estimated")
    except ValidationError as e:
        logger.warning("AI estimate failed validation for '%s': %s", requested_name, e)
        raise HTTPException(
            status_code=422,
            detail="The AI response was incomplete. Please enter values manually.",
        )
