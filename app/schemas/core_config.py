from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class AppFeatureBase(BaseModel):
    name: str
    is_active: bool = False
    description: Optional[str] = None

class AppFeatureCreate(AppFeatureBase):
    pass

class AppFeatureUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class AppFeatureResponse(AppFeatureBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
