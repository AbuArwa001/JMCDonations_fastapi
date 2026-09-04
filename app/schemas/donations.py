import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, computed_field

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
    
    created_at: datetime
    updated_at: datetime
    created_by_id: uuid.UUID

    @computed_field
    @property
    def category(self) -> uuid.UUID:
        return self.category_id
    
    model_config = ConfigDict(from_attributes=True)

class SavedDonationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    donation_id: uuid.UUID
    donation: Optional[DonationResponse] = None
    saved_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
