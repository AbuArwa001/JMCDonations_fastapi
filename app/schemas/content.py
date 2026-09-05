import uuid
from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# ==================== Categories ====================
class CategoryBase(BaseModel):
    category_name: str
    color: str = "#9D7C3F"

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    color: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==================== Duas ====================
class DuaCategoryBase(BaseModel):
    name: str
    slug: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0

class DuaCategoryCreate(DuaCategoryBase):
    name: str

class DuaCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None

class DuaCategoryResponse(DuaCategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DuaBase(BaseModel):
    title: str
    arabic_text: str
    transliteration: Optional[str] = None
    translation_en: str
    translation_sw: Optional[str] = None
    source_reference: Optional[str] = None
    audio_url: Optional[str] = None
    category_id: int
    display_order: int = 0
    published: bool = True

class DuaCreate(DuaBase):
    pass

class DuaUpdate(BaseModel):
    title: Optional[str] = None
    arabic_text: Optional[str] = None
    transliteration: Optional[str] = None
    translation_en: Optional[str] = None
    translation_sw: Optional[str] = None
    source_reference: Optional[str] = None
    audio_url: Optional[str] = None
    category_id: Optional[int] = None
    display_order: Optional[int] = None
    published: Optional[bool] = None

class DuaResponse(DuaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ==================== Events ====================
class EventCategoryBase(BaseModel):
    name: str
    slug: Optional[str] = None

class EventCategoryCreate(EventCategoryBase):
    name: str

class EventCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None

class EventCategoryResponse(EventCategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class EventImageBase(BaseModel):
    image: str
    caption: Optional[str] = None
    order: int = 0

class EventImageCreate(EventImageBase):
    event_id: int

class EventImageResponse(EventImageBase):
    id: int
    event_id: int
    model_config = ConfigDict(from_attributes=True)

class EventBase(BaseModel):
    title: str
    category_id: Optional[int] = None
    story: str
    cover_image: Optional[str] = None
    event_date: date
    start_time: time
    end_time: Optional[time] = None
    venue_name: str
    venue_address: Optional[str] = None
    venue_map_link: Optional[str] = None
    guest_name: Optional[str] = None
    guest_photo: Optional[str] = None
    published: bool = True

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    category_id: Optional[int] = None
    story: Optional[str] = None
    cover_image: Optional[str] = None
    event_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    venue_map_link: Optional[str] = None
    guest_name: Optional[str] = None
    guest_photo: Optional[str] = None
    published: Optional[bool] = None

class EventResponse(EventBase):
    id: int
    created_at: datetime
    created_by_id: Optional[uuid.UUID] = None
    gallery_images: List[EventImageResponse] = []
    model_config = ConfigDict(from_attributes=True)

# ==================== Quran ====================
class ReciterBase(BaseModel):
    name: str
    bio: Optional[str] = None
    photo: Optional[str] = None

class ReciterCreate(ReciterBase):
    pass

class ReciterUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    photo: Optional[str] = None

class ReciterResponse(ReciterBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class SurahAudioBase(BaseModel):
    surah_number: int
    reciter_id: int
    audio_url: str
    duration_seconds: Optional[int] = None

class SurahAudioCreate(SurahAudioBase):
    pass

class SurahAudioUpdate(BaseModel):
    surah_number: Optional[int] = None
    reciter_id: Optional[int] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[int] = None

class SurahAudioResponse(SurahAudioBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ==================== Prayer Times ====================
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
