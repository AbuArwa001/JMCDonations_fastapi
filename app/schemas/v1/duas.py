from typing import Optional
from pydantic import BaseModel, ConfigDict

class DuaCategoryBase(BaseModel):
    name: str
    slug: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0

class DuaCategoryCreate(DuaCategoryBase):
    name: str

class DuaCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None

class DuaCategoryResponse(DuaCategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DuaBase(BaseModel):
    title: str
    arabic_text: str
    transliteration: Optional[str] = None
    translation_en: str
    translation_sw: Optional[str] = None
    source_reference: Optional[str] = None
    audio_url: Optional[str] = None
    category_id: int
    display_order: int = 0
    published: bool = True

class DuaCreate(DuaBase):
    pass

class DuaUpdate(BaseModel):
    title: Optional[str] = None
    arabic_text: Optional[str] = None
    transliteration: Optional[str] = None
    translation_en: Optional[str] = None
    translation_sw: Optional[str] = None
    source_reference: Optional[str] = None
    audio_url: Optional[str] = None
    category_id: Optional[int] = None
    display_order: Optional[int] = None
    published: Optional[bool] = None

class DuaResponse(DuaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

