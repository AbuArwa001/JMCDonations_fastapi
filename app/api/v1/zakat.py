from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.db.session import get_db
from app.models.zakat import NisabRate
from app.schemas.zakat import NisabRateCreate, NisabRateUpdate, NisabRateResponse

router = APIRouter()

@router.get("/nisab", response_model=NisabRateResponse)
async def get_nisab_rate(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NisabRate).order_by(NisabRate.updated_at.desc()))
    db_rate = result.scalars().first()
    if not db_rate:
        raise HTTPException(status_code=404, detail="Nisab rate not set")
    return db_rate

@router.post("/nisab", response_model=NisabRateResponse, status_code=status.HTTP_201_CREATED)
async def create_nisab_rate(rate_in: NisabRateCreate, db: AsyncSession = Depends(get_db)):
    db_rate = NisabRate(**rate_in.model_dump())
    db.add(db_rate)
    await db.commit()
    await db.refresh(db_rate)
    return db_rate
