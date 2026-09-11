from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime

class BulletinBase(BaseModel):
    title: str
    issue_number: Optional[str] = None
    published_date: date
    is_active: bool = True

class BulletinCreate(BulletinBase):
    pass

class BulletinUpdate(BaseModel):
    title: Optional[str] = None
    issue_number: Optional[str] = None
    published_date: Optional[date] = None
    is_active: Optional[bool] = None

class BulletinResponse(BulletinBase):
    id: int
    pdf_path: str
    cover_image_path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
