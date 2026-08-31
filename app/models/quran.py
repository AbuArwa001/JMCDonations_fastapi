from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Reciter(Base):
    __tablename__ = "reciters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    surah_audios: Mapped[List["SurahAudio"]] = relationship("SurahAudio", back_populates="reciter", cascade="all, delete-orphan")


class SurahAudio(Base):
    __tablename__ = "surah_audios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    surah_number: Mapped[int] = mapped_column(Integer)
    reciter_id: Mapped[int] = mapped_column(ForeignKey("reciters.id", ondelete="CASCADE"))
    reciter: Mapped["Reciter"] = relationship("Reciter", back_populates="surah_audios")
    
    audio_url: Mapped[str] = mapped_column(String(1000))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
