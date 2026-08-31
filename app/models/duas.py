import uuid
from typing import List, Optional
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class DuaCategory(Base):
    __tablename__ = "dua_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    
    duas: Mapped[List["Dua"]] = relationship("Dua", back_populates="category", cascade="all, delete-orphan")


class Dua(Base):
    __tablename__ = "duas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("dua_categories.id", ondelete="CASCADE"))
    category: Mapped["DuaCategory"] = relationship("DuaCategory", back_populates="duas")
    
    title: Mapped[str] = mapped_column(String(200))
    arabic_text: Mapped[str] = mapped_column(Text)
    transliteration: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    translation_en: Mapped[str] = mapped_column(Text)
    translation_sw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_reference: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    published: Mapped[bool] = mapped_column(Boolean, default=True)
