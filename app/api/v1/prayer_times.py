from datetime import date, datetime, time, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.prayer_times import City, PrayerCalculationSettings, PrayerTimeOverride
from app.models.users import User
from app.schemas.content import (
    CityCreate, CityUpdate, CityResponse,
    PrayerTimeOverrideCreate, PrayerTimeOverrideResponse,
    PrayerCalculationSettingsResponse, PrayerCalculationSettingsUpdate,
    DailyPrayerTimesResponse
)
from app.api.dependencies.auth import get_current_admin_user

router = APIRouter()

# ==================== Cities ====================

@router.get("/cities", response_model=List[CityResponse])
async def list_cities(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    query = select(City)
    if active_only:
        query = query.filter(City.is_active == True)
    query = query.order_by(City.name)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/cities", response_model=CityResponse, status_code=status.HTTP_201_CREATED)
async def create_city(
    city_in: CityCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_city = City(**city_in.model_dump())
    db.add(db_city)
    await db.commit()
    await db.refresh(db_city)
    return db_city

@router.get("/cities/{city_id}", response_model=CityResponse)
async def get_city(city_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(City).filter(City.id == city_id))
    city = result.scalars().first()
    if not city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")
    return city

@router.patch("/cities/{city_id}", response_model=CityResponse)
@router.put("/cities/{city_id}", response_model=CityResponse)
async def update_city(
    city_id: int,
    city_in: CityUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(City).filter(City.id == city_id))
    city = result.scalars().first()
    if not city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")

    update_data = city_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(city, field, value)

    await db.commit()
    await db.refresh(city)
    return city

@router.delete("/cities/{city_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_city(
    city_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(City).filter(City.id == city_id))
    city = result.scalars().first()
    if not city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")

    await db.delete(city)
    await db.commit()

# ==================== Overrides ====================

@router.get("/overrides", response_model=List[PrayerTimeOverrideResponse])
async def list_overrides(city_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    query = select(PrayerTimeOverride)
    if city_id:
        query = query.filter(PrayerTimeOverride.city_id == city_id)
    query = query.order_by(PrayerTimeOverride.date.desc())
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/overrides", response_model=PrayerTimeOverrideResponse, status_code=status.HTTP_201_CREATED)
async def create_override(
    override_in: PrayerTimeOverrideCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_override = PrayerTimeOverride(**override_in.model_dump())
    db.add(db_override)
    await db.commit()
    await db.refresh(db_override)
    return db_override

@router.delete("/overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_override(
    override_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(PrayerTimeOverride).filter(PrayerTimeOverride.id == override_id))
    override = result.scalars().first()
    if not override:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")

    await db.delete(override)
    await db.commit()

# ==================== Calculation Settings ====================

@router.get("/settings", response_model=PrayerCalculationSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PrayerCalculationSettings).order_by(PrayerCalculationSettings.id.desc()))
    settings = result.scalars().first()
    if not settings:
        settings = PrayerCalculationSettings(calculation_method="MUSLIM_WORLD_LEAGUE")
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings

@router.put("/settings", response_model=PrayerCalculationSettingsResponse)
async def update_settings(
    settings_in: PrayerCalculationSettingsUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(PrayerCalculationSettings).order_by(PrayerCalculationSettings.id.desc()))
    settings = result.scalars().first()
    if not settings:
        settings = PrayerCalculationSettings(calculation_method=settings_in.calculation_method)
        db.add(settings)
    else:
        settings.calculation_method = settings_in.calculation_method
        settings.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(settings)
    return settings

# ==================== Today & Calc Times ====================

@router.get("/today", response_model=DailyPrayerTimesResponse)
@router.get("/", response_model=DailyPrayerTimesResponse)
async def get_today_prayer_times(
    city_name: str = "Nairobi",
    target_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    query_date = target_date or datetime.now(timezone.utc).date()
    # Baseline defaults for Nairobi / East Africa (standard Jamia Mosque times)
    times = {
        "city": city_name,
        "date": query_date,
        "fajr": "05:15",
        "dhuhr": "12:35",
        "asr": "15:55",
        "maghrib": "18:40",
        "isha": "19:50"
    }

    # Check for city overrides
    city_res = await db.execute(select(City).filter(City.name.ilike(city_name)))
    city = city_res.scalars().first()
    if city:
        overrides_res = await db.execute(
            select(PrayerTimeOverride).filter(
                PrayerTimeOverride.city_id == city.id,
                PrayerTimeOverride.date == query_date
            )
        )
        for ovr in overrides_res.scalars().all():
            prayer_key = ovr.prayer_name.lower()
            if prayer_key in times:
                times[prayer_key] = ovr.overridden_time.strftime("%H:%M")

    return DailyPrayerTimesResponse(**times)
