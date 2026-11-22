import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class TransactionV2Response(BaseModel):
    id: uuid.UUID
    donation_id: uuid.UUID
    donation_title: Optional[str] = None
    amount: float
    currency: str = "KES"
    payment_method: str
    payment_status: str
    transaction_reference: Optional[str] = None
    mpesa_receipt: Optional[str] = None
    donor_name: Optional[str] = None
    donated_at: datetime
    completed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class V2PaymentInitiateRequest(BaseModel):
    donation_id: uuid.UUID
    amount: float
    phone_number: str
    idempotency_key: Optional[str] = None

