import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id", ondelete="CASCADE"))
    donation: Mapped["Donation"] = relationship("Donation", back_populates="transactions")
    
    account_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    
    recorded_by_admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recorded_by_admin: Mapped[Optional["User"]] = relationship("User", foreign_keys=[recorded_by_admin_id])
    
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    payment_method: Mapped[str] = mapped_column(String(50))
    payment_status: Mapped[str] = mapped_column(String(20), default="Pending")
    mpesa_receipt: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    donated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bank_name: Mapped[str] = mapped_column(String(100))
    paybill_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    account_number: Mapped[str] = mapped_column(String(50))
    account_name: Mapped[str] = mapped_column(String(100))
    
    consumer_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    consumer_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    passkey: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    initiator_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    security_credential: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_paybill: Mapped[str] = mapped_column(String(50), default="150770")
    
    destination_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True)
    destination_account: Mapped[Optional["BankAccount"]] = relationship("BankAccount")
    
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    
    initiated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    initiated_by: Mapped[Optional["User"]] = relationship("User")
    
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
