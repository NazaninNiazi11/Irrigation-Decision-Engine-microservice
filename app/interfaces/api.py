import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.models.models import Crop, SensorData, IrrigationDecision, User
from app.schemas.schemas import (
    CropCreate, CropResponse, CropProfileResponse,
    EstimateCropRequest, EstimatedCropResponse,
    SensorDataCreate, SensorDataResponse,
    IrrigationDecisionResponse, IrrigationDecisionUpdate,
)
from app.services.irrigation_service import IrrigationService
from app.services import crop_estimator, weather_service
from app.auth import get_current_user
from app.rate_limit import limiter

router = APIRouter()

# ── Load crop profiles once at module level ──
_profiles_path = Path(__file__).resolve().parent.parent / "data" / "crop_profiles.json"
_crop_profiles: List[dict] = json.loads(_profiles_path.read_text())


# ── Health ──

@router.get("/health")
def health_check():
    return {"status": "ok"}


# ── Crop Profiles (no auth) ──

@router.get("/crop-profiles", response_model=List[CropProfileResponse], tags=["Crops"])
def list_crop_profiles(db: Session = Depends(get_db)):
    """Return crop profiles. """
    return db.query(Crop).all()


# ── Crops ──

@router.post("/crops/estimate", response_model=EstimatedCropResponse, tags=["Crops"])
@limiter.limit("10/minute")
def estimate_crop(request: Request, body: EstimateCropRequest, current_user: User = Depends(get_current_user)):
    """Use AI to estimate irrigation parameters for a crop not in the predefined list.

    Returns suggested values the user can review and edit before saving via POST /crops.
    """
    return crop_estimator.estimate_crop_parameters(body.name, body.species)


@router.post("/crops", response_model=CropResponse, status_code=201, tags=["Crops"])
def create_crop(crop: CropCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Register a new crop with its moisture and temperature thresholds."""
    db_crop = Crop(**crop.model_dump())
    db.add(db_crop)
    db.commit()
    db.refresh(db_crop)
    return db_crop


@router.get("/crops", response_model=List[CropResponse], tags=["Crops"])
def list_crops(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all registered crops."""
    return db.query(Crop).all()


@router.get("/crops/{crop_id}", response_model=CropResponse, tags=["Crops"])
def get_crop(crop_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    return crop


# ── Weather (used for sensor autofill and decision context) ──

@router.get("/weather/current", tags=["Weather"])
@limiter.limit("60/minute")
def current_weather(
    request: Request,
    crop_id: int = Query(..., description="Crop ID — uses its registered location"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch current weather + 24h forecast for a crop's location (Open-Meteo)."""
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    if crop.latitude is None or crop.longitude is None:
        raise HTTPException(
            status_code=400,
            detail="This crop has no location set. Edit the crop and add latitude/longitude to enable live weather.",
        )
    weather = weather_service.get_current_weather(crop.latitude, crop.longitude)
    if weather is None:
        raise HTTPException(
            status_code=503,
            detail="Weather service unavailable. Please enter sensor values manually.",
        )
    return weather


# ── Sensor Data ──

@router.post("/sensor-data", response_model=SensorDataResponse, status_code=201, tags=["Sensor Data"])
def submit_sensor_data(data: SensorDataCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Submit new sensor readings for a crop."""
    crop = db.query(Crop).filter(Crop.id == data.crop_id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")

    sensor = SensorData(**data.model_dump())
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor


@router.get("/sensor-data", response_model=List[SensorDataResponse], tags=["Sensor Data"])
def list_sensor_data(
    crop_id: int = Query(None, description="Filter by crop ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sensor readings, optionally filtered by crop."""
    query = db.query(SensorData)
    if crop_id:
        query = query.filter(SensorData.crop_id == crop_id)
    return query.order_by(SensorData.recorded_at.desc()).limit(limit).all()


@router.get("/sensor-data/{sensor_id}", response_model=SensorDataResponse, tags=["Sensor Data"])
def get_sensor_data(sensor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sensor = db.query(SensorData).filter(SensorData.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor data not found")
    return sensor


# ── Irrigation Decisions ──

@router.post("/decisions/evaluate/{sensor_data_id}", response_model=IrrigationDecisionResponse, status_code=201, tags=["Decisions"])
@limiter.limit("30/minute")
def evaluate_irrigation(request: Request, sensor_data_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Analyze sensor data and generate an irrigation decision."""
    try:
        decision = IrrigationService.evaluate_and_store(db, sensor_data_id)
        return decision
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/decisions", response_model=List[IrrigationDecisionResponse], tags=["Decisions"])
def list_decisions(
    crop_id: int = Query(None, description="Filter by crop ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List irrigation decisions."""
    query = db.query(IrrigationDecision)
    if crop_id:
        query = query.filter(IrrigationDecision.crop_id == crop_id)
    return query.order_by(IrrigationDecision.decided_at.desc()).limit(limit).all()


@router.patch("/decisions/{decision_id}", response_model=IrrigationDecisionResponse, tags=["Decisions"])
def update_decision_status(decision_id: int, update: IrrigationDecisionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update the status of an irrigation decision (approve, complete, or skip)."""
    decision = db.query(IrrigationDecision).filter(IrrigationDecision.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision.status = update.status
    db.commit()
    db.refresh(decision)
    return decision
