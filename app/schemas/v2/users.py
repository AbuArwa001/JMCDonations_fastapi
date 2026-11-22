import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict

class UserRoleV2(BaseModel):
    id: Optional[uuid.UUID] = None
    role_name: str
    permissions: List[str] = []

class UserV2Response(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    full_name: str
    phone_number: Optional[str] = None
    is_active: bool
    is_admin: bool
    profile_image_url: Optional[str] = None
    role: Optional[UserRoleV2] = None
    total_donations: int = 0
    total_impact: float = 0.0
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

