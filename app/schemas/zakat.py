import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class NisabRateBase(BaseModel):
    gold_price_per_gram: float
    silver_price_per_gram: float
    currency: str = "KES"

class NisabRateCreate(NisabRateBase):
    pass

class NisabRateUpdate(BaseModel):
    gold_price_per_gram: Optional[float] = None
    silver_price_per_gram: Optional[float] = None
    currency: Optional[str] = None

class NisabRateResponse(NisabRateBase):
    id: uuid.UUID
    updated_at: datetime
    updated_by_id: Optional[uuid.UUID] = None
    
    model_config = ConfigDict(from_attributes=True)
