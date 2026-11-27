import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

class PermissionResponse(BaseModel):
    key: str
    label: str
    description: str
    group: str

class RoleBase(BaseModel):
    role_name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    permissions: List[str] = []
    color: Optional[str] = "#10b981"

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    role_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    color: Optional[str] = None

class RoleResponse(RoleBase):
    id: uuid.UUID
    is_system: bool = False
    users_count: int = 0
    user_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class RoleSummary(BaseModel):
    id: uuid.UUID
    role_name: str
    description: Optional[str] = None
    color: Optional[str] = None
    is_system: Optional[bool] = False
    model_config = ConfigDict(from_attributes=True)

class StaffUser(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    phone_number: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool
    is_admin: bool
    is_super_admin: bool
    role: Optional[RoleSummary] = None
    ss_login: Optional[datetime] = None
    firebase_uid: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class StaffUserInput(BaseModel):
    email: str
    full_name: str
    password: Optional[str] = None
    phone_number: Optional[str] = None
    role_id: Optional[uuid.UUID] = None

class StaffUserUpdateInput(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role_id: Optional[uuid.UUID] = None
    clear_role: Optional[bool] = False
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class StaffInviteResponse(BaseModel):
    user: StaffUser
    created: bool
    firebase_synced: bool
    password_reset_link: Optional[str] = None

class AssignRoleRequest(BaseModel):
    role_id: Optional[uuid.UUID] = None

