from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from datetime import datetime


# ── Auth Schemas ──

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


# ── Crop Schemas ──

class CropCreate(BaseModel):
    name: str = Field(..., max_length=100, example="Wheat")
    species: Optional[str] = Field(None, max_length=150, example="Triticum aestivum")
    min_soil_moisture: float = Field(..., ge=0, le=100, example=30.0)
    max_soil_moisture: float = Field(..., ge=0, le=100, example=70.0)
    optimal_temperature_min: Optional[float] = Field(None, example=15.0)
    optimal_temperature_max: Optional[float] = Field(None, example=30.0)
    water_requirement_mm: Optional[float] = Field(None, ge=0, example=5.0)
    parameters_source: Optional[Literal["predefined", "ai_estimated", "user_provided"]] = "user_provided"
    parameters_notes: Optional[str] = Field(None, max_length=1000)
    latitude: Optional[float] = Field(None, ge=-90, le=90, example=52.52)
    longitude: Optional[float] = Field(None, ge=-180, le=180, example=13.41)
    planted_on: Optional[datetime] = None


class CropResponse(BaseModel):
    id: int
    name: str
    species: Optional[str]
    min_soil_moisture: float
    max_soil_moisture: float
    optimal_temperature_min: Optional[float]
    optimal_temperature_max: Optional[float]
    water_requirement_mm: Optional[float]
    parameters_source: Optional[str]
    parameters_notes: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    planted_on: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



class CropProfileResponse(BaseModel):
    id: int
    name: str
    species: Optional[str]
    min_soil_moisture: float
    max_soil_moisture: float

    optimal_temperature_min: Optional[float]
    optimal_temperature_max: Optional[float]

    water_requirement_mm: Optional[float]

    class Config:
        from_attributes = True



class EstimateCropRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, example="Lavender")
    species: Optional[str] = Field(None, max_length=150)


class EstimatedCropResponse(BaseModel):
    name: str
    species: str
    min_soil_moisture: float = Field(..., ge=0, le=100)
    max_soil_moisture: float = Field(..., ge=0, le=100)
    optimal_temperature_min: float
    optimal_temperature_max: float
    water_requirement_mm: float = Field(..., ge=0)
    confidence: Literal["high", "medium", "low"]
    notes: str
    source: Literal["ai_estimated"] = "ai_estimated"


# ── Sensor Data Schemas ──

class SensorDataCreate(BaseModel):
    crop_id: int
    soil_moisture: float = Field(..., ge=0, le=100, example=25.5)
    temperature: float = Field(..., example=28.0)
    humidity: Optional[float] = Field(None, ge=0, le=100, example=60.0)
    rainfall_mm: Optional[float] = Field(None, ge=0, example=0.0)
    wind_speed: Optional[float] = Field(None, ge=0, example=12.5)
    solar_radiation: Optional[float] = Field(None, ge=0, example=450.0)


class SensorDataResponse(BaseModel):
    id: int
    crop_id: int
    soil_moisture: float
    temperature: float
    humidity: Optional[float]
    rainfall_mm: Optional[float]
    wind_speed: Optional[float]
    solar_radiation: Optional[float]
    recorded_at: datetime

    class Config:
        from_attributes = True


# ── Irrigation Decision Schemas ──

class IrrigationDecisionResponse(BaseModel):
    id: int
    crop_id: int
    sensor_data_id: Optional[int]
    water_stress_index: float
    stress_level: str
    should_irrigate: bool
    recommended_water_mm: Optional[float]
    reason: Optional[str]
    growth_stage: Optional[str] = None
    status: str
    decided_at: datetime

    class Config:
        from_attributes = True


class IrrigationDecisionUpdate(BaseModel):
    status: str = Field(..., pattern="^(approved|completed|skipped)$")
