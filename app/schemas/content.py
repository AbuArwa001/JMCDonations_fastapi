import uuid
from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# Categories
class CategoryBase(BaseModel):
    category_name: str
    color: str = "#9D7C3F"

class CategoryResponse(CategoryBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Duas
class DuaBase(BaseModel):
    title: str
    arabic_text: str
    transliteration: Optional[str] = None
    translation_en: str
    translation_sw: Optional[str] = None
    source_reference: Optional[str] = None
    audio_url: Optional[str] = None
    category_id: int

class DuaResponse(DuaBase):
    id: int
    display_order: int
    model_config = ConfigDict(from_attributes=True)

# Quran
class ReciterBase(BaseModel):
    name: str
    bio: Optional[str] = None

class ReciterResponse(ReciterBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Prayer Times
class CityBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    timezone: str = "Africa/Nairobi"

class CityResponse(CityBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

# Events
class EventBase(BaseModel):
    title: str
    story: str
    event_date: date
    start_time: time
    end_time: Optional[time] = None
    venue_name: str

class EventResponse(EventBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
