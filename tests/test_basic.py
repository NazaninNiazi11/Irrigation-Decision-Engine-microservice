import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.irrigation_service import IrrigationService

def test_water_stress():
    class Sensor:
        soil_moisture = 10
        temperature = 35
        humidity = 20
        rainfall_mm = 0

    class Crop:
        min_soil_moisture = 20
        max_soil_moisture = 60
        optimal_temperature_min = 15
        optimal_temperature_max = 30
        water_requirement_mm = 10

    result = IrrigationService.calculate_water_stress(Sensor(), Crop())
    assert result["should_irrigate"] == True