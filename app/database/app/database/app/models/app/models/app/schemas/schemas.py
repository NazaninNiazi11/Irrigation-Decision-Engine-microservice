from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Crop Schemas ──

class CropCreate(BaseModel):
    name: str = Field(..., max_length=100, example="Wheat")
    species: Optional[str] = Field(None, max_length=150, example="Triticum aestivum")
    min_soil_moisture: float = Field(..., ge=0, le=100, example=30.0)
    max_soil_moisture: float = Field(..., ge=0, le=100, example=70.0)
    optimal_temperature_min: Optional[float] = Field(None, example=15.0)
    optimal_temperature_max: Optional[float] = Field(None, example=30.0)
    water_requirement_mm: Optional[float] = Field(None, ge=0, example=5.0)


class CropResponse(BaseModel):
    id: int
    name: str
    species: Optional[str]
    min_soil_moisture: float
    max_soil_moisture: float
    optimal_temperature_min: Optional[float]
    optimal_temperature_max: Optional[float]
    water_requirement_mm: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    status: str
    decided_at: datetime

    class Config:
        from_attributes = True


class IrrigationDecisionUpdate(BaseModel):
    status: str = Field(..., pattern="^(approved|completed|skipped)$")
