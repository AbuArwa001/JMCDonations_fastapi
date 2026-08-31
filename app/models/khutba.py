import uuid
from datetime import date, time, datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, Date, Time, ForeignKey, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class JumaKhutba(Base):
    __tablename__ = "juma_khutbas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    khutba_date: Mapped[date] = mapped_column(Date)
    khutba_time: Mapped[time] = mapped_column(Time)
    imam_name: Mapped[str] = mapped_column(String(200))
    imam_photo: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    topic_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[Optional["User"]] = relationship("User")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    notifications: Mapped[List["NotificationLog"]] = relationship("NotificationLog", back_populates="related_khutba")


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fcm_token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    related_khutba_id: Mapped[Optional[int]] = mapped_column(ForeignKey("juma_khutbas.id", ondelete="SET NULL"), nullable=True)
    related_khutba: Mapped[Optional["JumaKhutba"]] = relationship("JumaKhutba", back_populates="notifications")
    
    related_event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    related_event: Mapped[Optional["Event"]] = relationship("Event", back_populates="notifications")
    
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
