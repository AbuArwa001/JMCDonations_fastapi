import uuid
from datetime import datetime, timezone
from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict, field_serializer
from app.schemas.v1.accounts import (
    BankAccountBase, BankAccountCreate, BankAccountUpdate, BankAccountResponse,
    TransferCreate, TransferResponse
)

class BulkDeleteTransactionsRequest(BaseModel):
    transaction_ids: List[uuid.UUID]

class BulkDeleteTransactionsResponse(BaseModel):
    deleted_count: int
    message: str

class TransactionBase(BaseModel):
    donation_id: uuid.UUID
    amount: float
    payment_method: str = "M-Pesa"
    account_name: Optional[str] = None
    account_number: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    transaction_reference: Optional[str] = None
    mpesa_receipt: Optional[str] = None
    donation_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    donated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class TransactionResponse(TransactionBase):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    recorded_by_admin_id: Optional[uuid.UUID] = None
    transaction_reference: Optional[str] = None
    payment_status: str
    mpesa_receipt: Optional[str] = None
    donated_at: datetime
    completed_at: Optional[datetime] = None
    user_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("donated_at", "completed_at", when_used="json")
    def serialize_datetime(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return v.replace(tzinfo=timezone.utc).isoformat() if v.tzinfo is None else v.isoformat()

class STKPushRequest(BaseModel):
    phone_number: str
    amount: float
    account_name: Optional[str] = "Donation"
    donation: Optional[str] = None
    donation_id: Optional[Union[uuid.UUID, str]] = None
    user_id: Optional[Union[uuid.UUID, str]] = None

STKPushInput = STKPushRequest

class PayPalInitInput(BaseModel):
    amount: float
    donation: Optional[str] = None
    donation_id: Optional[str] = None
    account_name: Optional[str] = "Donation"
    currency: Optional[str] = "USD"

class CardPaymentInput(BaseModel):
    amount: float
    donation_id: Optional[str] = None
    donation: Optional[str] = None

class FlutterwaveVerifyInput(BaseModel):
    tx_ref: str
    flw_ref: Optional[str] = ""
    amount: Optional[float] = 0.0
    donation_id: Optional[str] = None
    status: Optional[str] = "successful"

