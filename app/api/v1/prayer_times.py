from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.session import get_db
from app.models.prayer_times import City
from app.schemas.content import CityResponse

router = APIRouter()

@router.get("/cities", response_model=List[CityResponse])
async def list_cities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(City))
    return result.scalars().all()
