import uuid
from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

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

