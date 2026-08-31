import uuid
from datetime import datetime
from typing import List
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category_name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), default="#9D7C3F")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    donations: Mapped[List["Donation"]] = relationship("Donation", back_populates="category")
