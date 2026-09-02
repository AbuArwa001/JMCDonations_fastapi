from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.session import get_db
from app.models.quran import Reciter
from app.schemas.content import ReciterResponse

router = APIRouter()

@router.get("/reciters", response_model=List[ReciterResponse])
async def list_reciters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Reciter))
    return result.scalars().all()
