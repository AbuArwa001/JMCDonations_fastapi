from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.quran import Reciter, SurahAudio
from app.models.users import User
from app.schemas.content import (
    ReciterCreate, ReciterUpdate, ReciterResponse,
    SurahAudioCreate, SurahAudioUpdate, SurahAudioResponse
)
from app.api.dependencies.auth import get_current_admin_user

router = APIRouter()

# ==================== Reciters ====================

@router.get("/reciters", response_model=List[ReciterResponse])
async def list_reciters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Reciter).order_by(Reciter.name))
    return result.scalars().all()

@router.post("/reciters", response_model=ReciterResponse, status_code=status.HTTP_201_CREATED)
async def create_reciter(
    reciter_in: ReciterCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_reciter = Reciter(**reciter_in.model_dump())
    db.add(db_reciter)
    await db.commit()
    await db.refresh(db_reciter)
    return db_reciter

@router.get("/reciters/{reciter_id}", response_model=ReciterResponse)
async def get_reciter(reciter_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Reciter).filter(Reciter.id == reciter_id))
    reciter = result.scalars().first()
    if not reciter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reciter not found")
    return reciter

@router.patch("/reciters/{reciter_id}", response_model=ReciterResponse)
@router.put("/reciters/{reciter_id}", response_model=ReciterResponse)
async def update_reciter(
    reciter_id: int,
    reciter_in: ReciterUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Reciter).filter(Reciter.id == reciter_id))
    reciter = result.scalars().first()
    if not reciter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reciter not found")

    update_data = reciter_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(reciter, field, value)

    await db.commit()
    await db.refresh(reciter)
    return reciter

@router.delete("/reciters/{reciter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reciter(
    reciter_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Reciter).filter(Reciter.id == reciter_id))
    reciter = result.scalars().first()
    if not reciter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reciter not found")

    await db.delete(reciter)
    await db.commit()

# ==================== Surah Audio ====================

@router.get("/audio", response_model=List[SurahAudioResponse])
async def list_surah_audio(
    reciter_id: Optional[int] = None,
    surah_number: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(SurahAudio)
    if reciter_id:
        query = query.filter(SurahAudio.reciter_id == reciter_id)
    if surah_number:
        query = query.filter(SurahAudio.surah_number == surah_number)
    query = query.order_by(SurahAudio.surah_number)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/audio", response_model=SurahAudioResponse, status_code=status.HTTP_201_CREATED)
async def create_surah_audio(
    audio_in: SurahAudioCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_audio = SurahAudio(**audio_in.model_dump())
    db.add(db_audio)
    await db.commit()
    await db.refresh(db_audio)
    return db_audio

@router.delete("/audio/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_surah_audio(
    audio_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SurahAudio).filter(SurahAudio.id == audio_id))
    audio = result.scalars().first()
    if not audio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Surah audio not found")

    await db.delete(audio)
    await db.commit()
