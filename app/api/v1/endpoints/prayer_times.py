from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, require_permission
from app.models.prayer_times import City, PrayerCalculationSettings, PrayerTimeOverride
from app.schemas.v1.prayer_times import (
    CityResponse, CityCreate, PrayerCalculationSettingsResponse, PrayerCalculationSettingsUpdate,
    PrayerTimeOverrideResponse, PrayerTimeOverrideCreate
)

router = APIRouter()

@router.get("/cities", response_model=List[CityResponse])
async def list_cities(db: AsyncSession = Depends(get_db)):
    return list((await db.execute(select(City).where(City.is_active.is_(True)))).scalars().all())

@router.post("/cities", response_model=CityResponse, status_code=status.HTTP_201_CREATED)
async def create_city(data: CityCreate, current_user=Depends(require_permission("prayer_times.manage")), db: AsyncSession = Depends(get_db)):
    c = City(**data.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c

@router.get("/settings", response_model=PrayerCalculationSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(PrayerCalculationSettings))).scalars().first()
    if not s:
        s = PrayerCalculationSettings(calculation_method="MuslimWorldLeague")
        db.add(s)
        await db.commit()
        await db.refresh(s)
    return s

@router.put("/settings", response_model=PrayerCalculationSettingsResponse)
async def update_settings(data: PrayerCalculationSettingsUpdate, current_user=Depends(require_permission("prayer_times.manage")), db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(PrayerCalculationSettings))).scalars().first()
    if not s:
        s = PrayerCalculationSettings(calculation_method=data.calculation_method)
        db.add(s)
    else:
        s.calculation_method = data.calculation_method
    await db.commit()
    await db.refresh(s)
    return s

