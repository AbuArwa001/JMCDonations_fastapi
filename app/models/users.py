import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    role_name: Mapped[str] = mapped_column(String(50), unique=True)
    
    users: Mapped[List["User"]] = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fcm_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[Optional["Role"]] = relationship("Role", back_populates="users")
    
    ss_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    firebase_uid: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_analytics_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_donation_account: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    payment_accounts: Mapped[List["UserPaymentAccount"]] = relationship("UserPaymentAccount", back_populates="user", cascade="all, delete-orphan")

class UserPaymentAccount(Base):
    __tablename__ = "user_payment_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship("User", back_populates="payment_accounts")
    
    account_type: Mapped[str] = mapped_column(String(20)) # M-Pesa, Card, PayPal
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    account_number: Mapped[str] = mapped_column(String(100))
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
