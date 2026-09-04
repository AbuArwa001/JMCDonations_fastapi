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

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    is_admin: bool
    firebase_uid: Optional[str] = None
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    ss_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

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

