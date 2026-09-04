import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class RatingBase(BaseModel):
    donation_id: uuid.UUID
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating between 1.0 and 5.0")
    comment: str

class RatingCreate(RatingBase):
    pass

class RatingUpdate(BaseModel):
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    comment: Optional[str] = None

class RatingResponse(RatingBase):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
