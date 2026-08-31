import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict

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
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
