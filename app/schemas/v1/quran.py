from typing import Optional
from pydantic import BaseModel, ConfigDict

class ReciterBase(BaseModel):
    name: str
    bio: Optional[str] = None
    photo: Optional[str] = None

class ReciterCreate(ReciterBase):
    pass

class ReciterUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    photo: Optional[str] = None

class ReciterResponse(ReciterBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class SurahAudioBase(BaseModel):
    surah_number: int
    reciter_id: int
    audio_url: str
    duration_seconds: Optional[int] = None

class SurahAudioCreate(SurahAudioBase):
    pass

class SurahAudioUpdate(BaseModel):
    surah_number: Optional[int] = None
    reciter_id: Optional[int] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[int] = None

class SurahAudioResponse(SurahAudioBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

