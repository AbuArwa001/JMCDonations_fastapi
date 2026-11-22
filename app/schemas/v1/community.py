import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class CommunityContentBase(BaseModel):
    content_type: str
    title: str
    content: Optional[str] = None
    media_url: Optional[str] = None
    extra_data: Optional[dict] = {}
    is_active: bool = True

class CommunityContentCreate(CommunityContentBase):
    pass

class CommunityContentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    media_url: Optional[str] = None
    extra_data: Optional[dict] = None
    is_active: Optional[bool] = None

class CommunityContentResponse(CommunityContentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

