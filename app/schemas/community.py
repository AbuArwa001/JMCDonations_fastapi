import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class CommunityContentBase(BaseModel):
    content_type: str
    title: str
    body: str
    author_or_sheikh: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    is_published: bool = True

class CommunityContentCreate(CommunityContentBase):
    pass

class CommunityContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    author_or_sheikh: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    is_published: Optional[bool] = None

class CommunityContentResponse(CommunityContentBase):
    id: uuid.UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
