from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database.connection import Base


class IrrigationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class StressLevel(str, enum.Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    species = Column(String(150), nullable=True)
    min_soil_moisture = Column(Float, nullable=False, comment="Minimum soil moisture percentage")
    max_soil_moisture = Column(Float, nullable=False, comment="Maximum soil moisture percentage")
    optimal_temperature_min = Column(Float, nullable=True, comment="Optimal min temperature (°C)")
    optimal_temperature_max = Column(Float, nullable=True, comment="Optimal max temperature (°C)")
    water_requirement_mm = Column(Float, nullable=True, comment="Daily water requirement in mm")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sensor_data = relationship("SensorData", back_populates="crop")
    irrigation_decisions = relationship("IrrigationDecision", back_populates="crop")

    def __repr__(self):
        return f"<Crop(id={self.id}, name='{self.name}')>"


class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    soil_moisture = Column(Float, nullable=False, comment="Soil moisture percentage (0-100)")
    temperature = Column(Float, nullable=False, comment="Air temperature in °C")
    humidity = Column(Float, nullable=True, comment="Air humidity percentage (0-100)")
    rainfall_mm = Column(Float, nullable=True, comment="Rainfall in mm")
    wind_speed = Column(Float, nullable=True, comment="Wind speed in km/h")
    solar_radiation = Column(Float, nullable=True, comment="Solar radiation in W/m²")
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    crop = relationship("Crop", back_populates="sensor_data")

    def __repr__(self):
        return f"<SensorData(id={self.id}, crop_id={self.crop_id}, moisture={self.soil_moisture})>"


class IrrigationDecision(Base):
    __tablename__ = "irrigation_decisions"

    id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    sensor_data_id = Column(Integer, ForeignKey("sensor_data.id"), nullable=True)
    water_stress_index = Column(Float, nullable=False, comment="Calculated water stress index (0-1)")
    stress_level = Column(String(20), nullable=False, comment="low/moderate/high/critical")
    should_irrigate = Column(Boolean, nullable=False)
    recommended_water_mm = Column(Float, nullable=True, comment="Recommended irrigation amount in mm")
    reason = Column(Text, nullable=True, comment="Explanation of the decision")
    status = Column(String(20), default="pending", comment="pending/approved/completed/skipped")
    decided_at = Column(DateTime(timezone=True), server_default=func.now())

    crop = relationship("Crop", back_populates="irrigation_decisions")
    sensor_data = relationship("SensorData")

    def __repr__(self):
        return f"<IrrigationDecision(id={self.id}, irrigate={self.should_irrigate})>"
