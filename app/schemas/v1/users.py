import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, ConfigDict, model_validator
from app.schemas.v1.notifications import (
    NotificationStateResponse, NotificationStateUpdate, NotificationSyncRequest
)

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    phone_number: Optional[str] = None
    fcm_token: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    fcm_token: Optional[str] = None
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    address: Optional[str] = None
    default_donation_account: Optional[str] = None

class UserPaymentAccountBase(BaseModel):
    account_type: str
    provider: Optional[str] = None
    account_number: str
    extra_data: Optional[dict] = {}
    is_default: bool = False

class UserPaymentAccountCreate(UserPaymentAccountBase):
    pass

class UserPaymentAccountUpdate(BaseModel):
    account_type: Optional[str] = None
    provider: Optional[str] = None
    account_number: Optional[str] = None
    extra_data: Optional[dict] = None
    is_default: Optional[bool] = None

class UserPaymentAccountResponse(UserPaymentAccountBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    is_admin: bool
    firebase_uid: Optional[str] = None
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    address: Optional[str] = None
    default_donation_account: Optional[str] = None
    payment_accounts: List[UserPaymentAccountResponse] = []
    total_donations: int = 0
    total_impact: float = 0.0
    ss_login: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def handle_orm_attributes(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            photo = getattr(data, "profile_image_url", None)
            if photo and "api.dicebear.com" in photo and "/svg" in photo:
                photo = photo.replace("/svg", "/png")
            accs = data.__dict__.get("payment_accounts", []) if hasattr(data, "__dict__") else []
            return {
                "id": getattr(data, "id", None), "email": getattr(data, "email", None),
                "username": getattr(data, "username", None), "full_name": getattr(data, "full_name", None),
                "phone_number": getattr(data, "phone_number", None), "fcm_token": getattr(data, "fcm_token", None),
                "is_active": getattr(data, "is_active", True), "is_admin": getattr(data, "is_admin", False),
                "firebase_uid": getattr(data, "firebase_uid", None), "profile_image_url": photo,
                "bio": getattr(data, "bio", None), "address": getattr(data, "address", None),
                "default_donation_account": getattr(data, "default_donation_account", None),
                "payment_accounts": accs, "total_donations": getattr(data, "total_donations", 0),
                "total_impact": getattr(data, "total_impact", 0.0), "ss_login": getattr(data, "ss_login", None),
            }
        return data

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    user: UserResponse
