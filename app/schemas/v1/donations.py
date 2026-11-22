import uuid
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, computed_field, field_serializer

class DonationBase(BaseModel):
    title: str
    description: str
    target_amount: float
    start_date: datetime
    end_date: datetime
    paybill_number: str
    account_name: str
    account_number: Optional[str] = None
    category_id: uuid.UUID
    image_urls: List[str] = []
    is_featured: bool = False
    consumer_key: Optional[str] = None
    consumer_secret: Optional[str] = None
    passkey: Optional[str] = None
    initiator_name: Optional[str] = None
    security_credential: Optional[str] = None

class DonationCreate(DonationBase):
    pass

class DonationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    paybill_number: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    image_urls: Optional[List[str]] = None
    status: Optional[str] = None
    is_featured: Optional[bool] = None

class DonationResponse(DonationBase):
    id: uuid.UUID
    slug: Optional[str] = None
    status: str
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    collected_amount: float = 0.0
    donor_count: int = 0
    average_rating: float = 0.0
    remaining_days: int = 0
    is_expired: bool = False
    category_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by_id: uuid.UUID

    @computed_field
    @property
    def category(self) -> uuid.UUID:
        return self.category_id

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at", "start_date", "end_date", "deleted_at", when_used="json")
    def serialize_datetime(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return v.replace(tzinfo=timezone.utc).isoformat() if v.tzinfo is None else v.isoformat()

class SavedDonationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    donation_id: uuid.UUID
    donation: Optional[DonationResponse] = None
    saved_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("saved_at", when_used="json")
    def serialize_saved_at(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return v.replace(tzinfo=timezone.utc).isoformat() if v.tzinfo is None else v.isoformat()

