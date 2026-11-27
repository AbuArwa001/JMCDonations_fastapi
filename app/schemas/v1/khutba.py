import uuid
from datetime import date, time, datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_serializer

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

    @field_serializer("created_at", when_used="json")
    def serialize_datetime(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return v.replace(tzinfo=timezone.utc).isoformat() if v.tzinfo is None else v.isoformat()

    @field_serializer("khutba_time", when_used="json")
    def serialize_time(self, v: Optional[time]) -> Optional[str]:
        if v is None:
            return None
        return v.strftime("%H:%M:%S")

    @field_serializer("khutba_date", when_used="json")
    def serialize_date(self, v: Optional[date]) -> Optional[str]:
        if v is None:
            return None
        return v.isoformat()

    @field_serializer("imam_photo", when_used="json")
    def serialize_imam_photo(self, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        if v.startswith("http://") or v.startswith("https://"):
            return v
        base = "https://donations-api.jamiamosque.co.ke"
        return f"{base}{v}" if v.startswith("/") else f"{base}/{v}"

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
    notification_type: Optional[str] = "general"
    related_khutba_id: Optional[int] = None
    related_event_id: Optional[int] = None
    related_donation_id: Optional[str] = None
    sent_at: datetime
    recipient_count: int
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("sent_at", when_used="json")
    def serialize_datetime(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return v.replace(tzinfo=timezone.utc).isoformat() if v.tzinfo is None else v.isoformat()

