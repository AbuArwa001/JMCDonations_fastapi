from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class FridayBulletinBase(BaseModel):
    title: str
    published_date: date
    issue_number: Optional[str] = None
    pdf_path: str
    cover_image_path: Optional[str] = None
    is_active: bool = True

class FridayBulletinCreate(BaseModel):
    title: str
    published_date: date
    issue_number: Optional[str] = None
    pdf_path: Optional[str] = None
    cover_image_path: Optional[str] = None
    is_active: bool = True

class FridayBulletinUpdate(BaseModel):
    title: Optional[str] = None
    published_date: Optional[date] = None
    issue_number: Optional[str] = None
    pdf_path: Optional[str] = None
    cover_image_path: Optional[str] = None
    is_active: Optional[bool] = None

class FridayBulletinResponse(BaseModel):
    id: int
    title: str
    issue_number: Optional[str] = None
    published_date: date
    pdf_path: str
    cover_image_path: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
