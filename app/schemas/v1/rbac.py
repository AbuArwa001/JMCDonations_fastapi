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
    color: str = "#10b981"

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    role_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    color: Optional[str] = None

class RoleResponse(RoleBase):
    id: uuid.UUID
    is_system: bool
    users_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AssignRoleRequest(BaseModel):
    role_id: Optional[uuid.UUID] = None

