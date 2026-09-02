import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class CommunityContent(Base):
    __tablename__ = "community_content"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_type: Mapped[str] = mapped_column(String(20)) # DARSA, DUA, INSPIRATION, KHUTBA
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    author_or_sheikh: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
