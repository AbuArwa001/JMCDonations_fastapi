from datetime import date, time, datetime
from typing import List, Optional
from sqlalchemy import String, Float, Boolean, Date, Time, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(String(50), default="Africa/Nairobi")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    overrides: Mapped[List["PrayerTimeOverride"]] = relationship("PrayerTimeOverride", back_populates="city", cascade="all, delete-orphan")


class PrayerCalculationSettings(Base):
    __tablename__ = "prayer_calculation_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    calculation_method: Mapped[str] = mapped_column(String(100), default="MUSLIM_WORLD_LEAGUE")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PrayerTimeOverride(Base):
    __tablename__ = "prayer_time_overrides"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"))
    city: Mapped["City"] = relationship("City", back_populates="overrides")
    
    date: Mapped[date] = mapped_column(Date)
    prayer_name: Mapped[str] = mapped_column(String(50))
    overridden_time: Mapped[time] = mapped_column(Time)
    reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
