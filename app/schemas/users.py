import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, ConfigDict, model_validator

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    phone_number: Optional[str] = None
    fcm_token: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    fcm_token: Optional[str] = None
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    address: Optional[str] = None
    default_donation_account: Optional[str] = None

class UserPaymentAccountBase(BaseModel):
    account_type: str  # M-Pesa, Card, PayPal, Bank
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
            # Check for DiceBear SVG to PNG
            photo_url = getattr(data, "profile_image_url", None)
            if photo_url and "api.dicebear.com" in photo_url and "/svg" in photo_url:
                photo_url = photo_url.replace("/svg", "/png")

            # Check if payment_accounts is loaded in session without triggering lazy load
            accounts = []
            if "payment_accounts" in getattr(data, "__dict__", {}):
                raw_accs = data.__dict__["payment_accounts"]
                if raw_accs:
                    accounts = raw_accs

            return {
                "id": getattr(data, "id", None),
                "email": getattr(data, "email", None),
                "username": getattr(data, "username", None),
                "full_name": getattr(data, "full_name", None),
                "phone_number": getattr(data, "phone_number", None),
                "fcm_token": getattr(data, "fcm_token", None),
                "is_active": getattr(data, "is_active", True),
                "is_admin": getattr(data, "is_admin", False),
                "firebase_uid": getattr(data, "firebase_uid", None),
                "profile_image_url": photo_url,
                "bio": getattr(data, "bio", None),
                "address": getattr(data, "address", None),
                "default_donation_account": getattr(data, "default_donation_account", None),
                "payment_accounts": accounts,
                "total_donations": getattr(data, "total_donations", 0),
                "total_impact": getattr(data, "total_impact", 0.0),
                "ss_login": getattr(data, "ss_login", None),
            }
        return data

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    user: UserResponse

class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    email_or_username: Optional[str] = None
    password: str

class FirebaseLoginRequest(BaseModel):
    id_token: Optional[str] = None
    idToken: Optional[str] = None
    token: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_token(cls, data: Any) -> Any:
        if isinstance(data, dict):
            resolved = data.get("id_token") or data.get("idToken") or data.get("token")
            if not resolved:
                raise ValueError("Firebase ID token is required (expected 'id_token', 'idToken', or 'token')")
            data["id_token"] = resolved
        return data

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class FCMTokenRequest(BaseModel):
    fcm_token: str


