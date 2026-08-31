import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class DonationBase(BaseModel):
    title: str
    description: str
    target_amount: float
    start_date: datetime
    end_date: datetime
    paybill_number: str
    account_name: str
    category_id: uuid.UUID
    image_urls: List[str] = []

class DonationCreate(DonationBase):
    pass

class DonationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[float] = None
    end_date: Optional[datetime] = None

class DonationResponse(DonationBase):
    id: uuid.UUID
    slug: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    created_by_id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)
