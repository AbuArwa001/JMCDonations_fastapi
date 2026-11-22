from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, require_permission
from app.models.quran import Reciter, SurahAudio
from app.schemas.v1.quran import ReciterResponse, ReciterCreate, SurahAudioResponse, SurahAudioCreate

router = APIRouter()

@router.get("/reciters", response_model=List[ReciterResponse])
async def list_reciters(db: AsyncSession = Depends(get_db)):
    return list((await db.execute(select(Reciter).order_by(Reciter.name))).scalars().all())

@router.post("/reciters", response_model=ReciterResponse, status_code=status.HTTP_201_CREATED)
async def create_reciter(data: ReciterCreate, current_user=Depends(require_permission("quran.manage")), db: AsyncSession = Depends(get_db)):
    r = Reciter(**data.model_dump())
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r

@router.get("/surahs", response_model=List[SurahAudioResponse])
async def list_surah_audio(reciter_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(SurahAudio).where(SurahAudio.reciter_id == reciter_id).order_by(SurahAudio.surah_number)
    return list((await db.execute(stmt)).scalars().all())

