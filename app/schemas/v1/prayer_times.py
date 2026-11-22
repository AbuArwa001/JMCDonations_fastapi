from datetime import datetime, date, time
from typing import Optional
from pydantic import BaseModel, ConfigDict

class CityBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    timezone: str = "Africa/Nairobi"
    is_active: bool = True

class CityCreate(CityBase):
    pass

class CityUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None

class CityResponse(CityBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class PrayerCalculationSettingsResponse(BaseModel):
    id: int
    calculation_method: str
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PrayerCalculationSettingsUpdate(BaseModel):
    calculation_method: str

class PrayerTimeOverrideBase(BaseModel):
    city_id: int
    date: date
    prayer_name: str
    overridden_time: time
    reason: Optional[str] = None

class PrayerTimeOverrideCreate(PrayerTimeOverrideBase):
    pass

class PrayerTimeOverrideResponse(PrayerTimeOverrideBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DailyPrayerTimesResponse(BaseModel):
    city: str
    date: date
    fajr: str
    sunrise: str = "06:25"
    dhuhr: str
    asr: str
    maghrib: str
    isha: str
    hijri_date: Optional[str] = None

