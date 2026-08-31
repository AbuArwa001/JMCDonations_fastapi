import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    image_urls: Mapped[list] = mapped_column(JSON, default=list)
    slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    paybill_number: Mapped[str] = mapped_column(String(50))
    account_name: Mapped[str] = mapped_column(String(100))
    account_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    consumer_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    consumer_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    passkey: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    initiator_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    security_credential: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    category: Mapped["Category"] = relationship("Category", back_populates="donations")
    
    target_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="Active")
    
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_by: Mapped["User"] = relationship("User")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="donation")
    saved_by: Mapped[List["SavedDonation"]] = relationship("SavedDonation", back_populates="donation")


class SavedDonation(Base):
    __tablename__ = "saved_donations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship("User")
    
    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id", ondelete="CASCADE"))
    donation: Mapped["Donation"] = relationship("Donation", back_populates="saved_by")
    
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
