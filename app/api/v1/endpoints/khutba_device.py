from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db
from app.models.khutba import DeviceToken, NotificationLog
from app.schemas.v1.khutba import DeviceTokenCreate, DeviceTokenResponse, NotificationLogResponse

router = APIRouter()

@router.get("/logs", response_model=List[NotificationLogResponse])
@router.get("/logs/", response_model=List[NotificationLogResponse])
async def list_notification_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = select(NotificationLog).order_by(NotificationLog.sent_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())

@router.post("/register_device", response_model=DeviceTokenResponse)
@router.post("/register_device/", response_model=DeviceTokenResponse)
@router.post("/register-device", response_model=DeviceTokenResponse)
@router.post("/register-device/", response_model=DeviceTokenResponse)
@router.post("/devices/register", response_model=DeviceTokenResponse)
@router.post("/devices/register/", response_model=DeviceTokenResponse)
async def register_device(data: DeviceTokenCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(DeviceToken).where(DeviceToken.fcm_token == data.fcm_token)
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        return existing
    dev = DeviceToken(fcm_token=data.fcm_token, platform=data.platform)
    db.add(dev)
    await db.commit()
    await db.refresh(dev)
    return dev
