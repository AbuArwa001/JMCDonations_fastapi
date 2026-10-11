import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, Field


class PermissionItem(BaseModel):
    key: str
    label: str
    description: str
    group: str


class PermissionGroup(BaseModel):
    group: str
    permissions: List[PermissionItem]


class RoleBase(BaseModel):
    role_name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    permissions: List[str] = []
    color: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    role_name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    color: Optional[str] = None


class RoleResponse(RoleBase):
    id: uuid.UUID
    is_system: bool = False
    user_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class RoleSummary(BaseModel):
    id: uuid.UUID
    role_name: str
    color: Optional[str] = None
    is_system: bool = False
    model_config = ConfigDict(from_attributes=True)


class StaffUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    phone_number: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool
    is_admin: bool
    is_super_admin: bool = False
    role: Optional[RoleSummary] = None
    ss_login: Optional[datetime] = None
    firebase_uid: Optional[str] = None


class StaffUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2)
    password: Optional[str] = Field(None, min_length=6)
    phone_number: Optional[str] = None
    role_id: Optional[uuid.UUID] = None


class StaffUserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role_id: Optional[uuid.UUID] = None
    clear_role: bool = False
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class MyAccessResponse(BaseModel):
    user: StaffUserResponse
    permissions: List[str]
    is_super_admin: bool


class RbacStats(BaseModel):
    total_staff: int
    active_staff: int
    super_admins: int
    roles: int
    unassigned: int
