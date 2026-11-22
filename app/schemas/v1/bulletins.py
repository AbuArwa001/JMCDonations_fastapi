import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class FridayBulletinBase(BaseModel):
    title: str
    bulletin_date: date
    issue_number: Optional[str] = None
    description: Optional[str] = None
    pdf_file_url: str
    cover_image_url: Optional[str] = None
    published: bool = True

class FridayBulletinCreate(FridayBulletinBase):
    pass

class FridayBulletinUpdate(BaseModel):
    title: Optional[str] = None
    bulletin_date: Optional[date] = None
    issue_number: Optional[str] = None
    description: Optional[str] = None
    pdf_file_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    published: Optional[bool] = None

class FridayBulletinResponse(FridayBulletinBase):
    id: uuid.UUID
    downloads_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

