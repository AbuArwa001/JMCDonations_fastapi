import uuid
from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Date, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class FridayBulletin(Base):
    __tablename__ = "friday_bulletins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    issue_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    published_date: Mapped[date] = mapped_column(Date)
    pdf_path: Mapped[str] = mapped_column(String(500))
    cover_image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
