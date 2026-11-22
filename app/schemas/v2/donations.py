import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.schemas.v1.donations import DonationResponse

class DonationV2Category(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None

class DonationV2Response(BaseModel):
    id: uuid.UUID
    slug: Optional[str] = None
    title: str
    description: str
    target_amount: float
    collected_amount: float
    progress_percentage: float
    donor_count: int
    status: str
    is_featured: bool
    is_expired: bool
    remaining_days: int
    category: Optional[DonationV2Category] = None
    image_urls: List[str] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

