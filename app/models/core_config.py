from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AppFeature(Base):
    __tablename__ = "app_features"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
