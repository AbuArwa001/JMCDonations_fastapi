import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class TransactionBase(BaseModel):
    donation_id: uuid.UUID
    amount: float
    payment_method: str = "M-Pesa"
    account_name: Optional[str] = None
    account_number: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    payment_status: Optional[str] = None
    mpesa_receipt: Optional[str] = None
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
    
    model_config = ConfigDict(from_attributes=True)

class BankAccountBase(BaseModel):
    bank_name: str
    account_name: str
    account_number: str
    paybill_number: Optional[str] = None
    is_active: bool = True
    consumer_key: Optional[str] = None
    consumer_secret: Optional[str] = None
    passkey: Optional[str] = None
    initiator_name: Optional[str] = None
    security_credential: Optional[str] = None

class BankAccountCreate(BankAccountBase):
    pass

class BankAccountUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    paybill_number: Optional[str] = None
    is_active: Optional[bool] = None

class BankAccountResponse(BankAccountBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TransferCreate(BaseModel):
    destination_account_id: uuid.UUID
    amount: float
    source_paybill: Optional[str] = "150770"
    description: Optional[str] = None

class TransferResponse(BaseModel):
    id: uuid.UUID
    source_paybill: str
    destination_account_id: Optional[uuid.UUID] = None
    amount: float
    status: str
    transaction_reference: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class STKPushRequest(BaseModel):
    donation_id: uuid.UUID
    phone_number: str
    amount: float
