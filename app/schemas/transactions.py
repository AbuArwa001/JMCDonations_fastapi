import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class TransactionBase(BaseModel):
    donation_id: uuid.UUID
    amount: float
    payment_method: str
    account_number: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: uuid.UUID
    transaction_reference: Optional[str] = None
    payment_status: str
    donated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
