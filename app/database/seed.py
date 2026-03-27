from app.database.connection import SessionLocal
from app.models.models import Crop

db = SessionLocal()

def seed_db():
    crops = [
        {
            "name": "Tomato",
            "species": "Solanum lycopersicum",
            "min_soil_moisture": 0.4,
            "max_soil_moisture": 0.7,
            "optimal_temperature_min": 18,
            "optimal_temperature_max": 30,
            "water_requirement_mm": 5,
        },
        {
            "name": "Wheat",
            "species": "Triticum",
            "min_soil_moisture": 0.3,
            "max_soil_moisture": 0.6,
            "optimal_temperature_min": 12,
            "optimal_temperature_max": 25,
            "water_requirement_mm": 4,
        },
        {
            "name": "Corn",
            "species": "Zea mays",
            "min_soil_moisture": 0.35,
            "max_soil_moisture": 0.65,
            "optimal_temperature_min": 20,
            "optimal_temperature_max": 32,
            "water_requirement_mm": 6,
        },
    ]

    for c in crops:
        exists = db.query(Crop).filter(Crop.name == c["name"]).first()
        if not exists:
            db.add(Crop(**c))

    db.commit()
    db.close()