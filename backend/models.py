from pydantic import BaseModel, field_validator
from typing import Optional

class SensorReading(BaseModel): 
    device_id: str
    recorded_at: int  #unix timestamp
    pm25: float
    pm10: float
    temperature: Optional[float]  #optional: dht22 can fail but the reading works
    humidity: Optional[float]

    @field_validator("pm25", "pm10")
    @classmethod
    def pm_reading_check(cls, v): 
        if v < 0: 
            raise ValueError("PM values cannot be negative.")
        if v > 1000: 
            raise ValueError("PM value exceeds physically plausible range.")
        return v
    
    @field_validator("temperature")
    @classmethod
    def temperature_check(cls, v): 
        if v is not None and not(-40<=v<=85): 
            raise ValueError("Temperature out of sensor range.")
        return v
    
    @field_validator("humidity")
    @classmethod
    def humidity_check(cls, v): 
        if v is not None and not(0<=v<=100): 
            raise ValueError("Humidity must be between 0 and 100.")
        return v
