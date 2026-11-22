import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class CategoryBase(BaseModel):
    category_name: str
    color: str = "#9D7C3F"

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    color: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

