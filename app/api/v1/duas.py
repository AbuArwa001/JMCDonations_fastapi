from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.session import get_db
from app.models.duas import Dua, DuaCategory
from app.schemas.content import DuaResponse

router = APIRouter()

@router.get("/", response_model=List[DuaResponse])
async def list_duas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dua))
    return result.scalars().all()
