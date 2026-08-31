import uuid
from datetime import date, time, datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, Date, Time, ForeignKey, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class EventCategory(Base):
    __tablename__ = "event_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    
    events: Mapped[List["Event"]] = relationship("Event", back_populates="category", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("event_categories.id", ondelete="SET NULL"), nullable=True)
    category: Mapped[Optional["EventCategory"]] = relationship("EventCategory", back_populates="events")
    
    story: Mapped[str] = mapped_column(Text)
    cover_image: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    event_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    
    venue_name: Mapped[str] = mapped_column(String(255))
    venue_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    venue_map_link: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    guest_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    guest_photo: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[Optional["User"]] = relationship("User")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    gallery_images: Mapped[List["EventImage"]] = relationship("EventImage", back_populates="event", cascade="all, delete-orphan")
    notifications: Mapped[List["NotificationLog"]] = relationship("NotificationLog", back_populates="related_event")


class EventImage(Base):
    __tablename__ = "event_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    event: Mapped["Event"] = relationship("Event", back_populates="gallery_images")
    
    image: Mapped[str] = mapped_column(String(1000))
    caption: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
