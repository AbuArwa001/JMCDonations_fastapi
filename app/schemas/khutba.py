import uuid
from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class JumaKhutbaBase(BaseModel):
    khutba_date: date
    khutba_time: time
    imam_name: str
    imam_photo: Optional[str] = None
    title: str
    topic_summary: Optional[str] = None
    published: bool = True

class JumaKhutbaCreate(JumaKhutbaBase):
    pass

class JumaKhutbaUpdate(BaseModel):
    khutba_date: Optional[date] = None
    khutba_time: Optional[time] = None
    imam_name: Optional[str] = None
    imam_photo: Optional[str] = None
    title: Optional[str] = None
    topic_summary: Optional[str] = None
    published: Optional[bool] = None

class JumaKhutbaResponse(JumaKhutbaBase):
    id: int
    created_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DeviceTokenCreate(BaseModel):
    fcm_token: str
    platform: Optional[str] = "Android"

class DeviceTokenResponse(BaseModel):
    id: int
    fcm_token: str
    platform: Optional[str] = None
    registered_at: datetime
    last_seen_at: datetime
    model_config = ConfigDict(from_attributes=True)

class NotificationLogResponse(BaseModel):
    id: int
    title: str
    body: str
    image_url: Optional[str] = None
    related_khutba_id: Optional[int] = None
    related_event_id: Optional[int] = None
    sent_at: datetime
    recipient_count: int
    model_config = ConfigDict(from_attributes=True)
