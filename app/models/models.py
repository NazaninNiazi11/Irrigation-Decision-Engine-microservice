from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    species = Column(String)

    min_soil_moisture = Column(Float)
    max_soil_moisture = Column(Float)

    optimal_temperature_min = Column(Float, nullable=True)
    optimal_temperature_max = Column(Float, nullable=True)

    water_requirement_mm = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)

    crop_id = Column(Integer, ForeignKey("crops.id"))

    soil_moisture = Column(Float)
    temperature = Column(Float)
    humidity = Column(Float, nullable=True)
    rainfall_mm = Column(Float, nullable=True)

    wind_speed = Column(Float, nullable=True)
    solar_radiation = Column(Float, nullable=True)

    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    crop = relationship("Crop")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IrrigationDecision(Base):
    __tablename__ = "irrigation_decisions"

    id = Column(Integer, primary_key=True, index=True)

    crop_id = Column(Integer)
    sensor_data_id = Column(Integer, ForeignKey("sensor_data.id"))

    water_stress_index = Column(Float)
    stress_level = Column(String)
    should_irrigate = Column(Boolean)

    recommended_water_mm = Column(Float, nullable=True)
    reason = Column(String)

    status = Column(String)

    decided_at = Column(DateTime(timezone=True), server_default=func.now())