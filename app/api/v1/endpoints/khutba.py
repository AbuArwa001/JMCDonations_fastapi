from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, require_permission
from app.models.khutba import JumaKhutba, DeviceToken, NotificationLog
from app.schemas.v1.khutba import (
    JumaKhutbaResponse, JumaKhutbaCreate, JumaKhutbaUpdate,
    DeviceTokenCreate, DeviceTokenResponse, NotificationLogResponse
)
from app.services.firebase import firebase_service

router = APIRouter()

@router.get("/logs", response_model=List[NotificationLogResponse])
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
    existing = (await db.execute(select(DeviceToken).where(DeviceToken.fcm_token == data.fcm_token))).scalars().first()
    if existing:
        return existing
    dev = DeviceToken(fcm_token=data.fcm_token, platform=data.platform)
    db.add(dev)
    await db.commit()
    await db.refresh(dev)
    return dev

@router.get("/", response_model=List[JumaKhutbaResponse])
async def list_khutbas(db: AsyncSession = Depends(get_db)):
    stmt = select(JumaKhutba).order_by(JumaKhutba.khutba_date.desc()).limit(20)
    return list((await db.execute(stmt)).scalars().all())

@router.post("/", response_model=JumaKhutbaResponse, status_code=status.HTTP_201_CREATED)
async def create_khutba(data: JumaKhutbaCreate, current_user=Depends(require_permission("khutba.manage")), db: AsyncSession = Depends(get_db)):
    k = JumaKhutba(**data.model_dump(), created_by_id=current_user.id)
    db.add(k)
    await db.commit()
    await db.refresh(k)
    return k

@router.get("/{id}", response_model=JumaKhutbaResponse)
async def get_khutba(id: int, db: AsyncSession = Depends(get_db)):
    k = await db.get(JumaKhutba, id)
    if not k:
        raise HTTPException(status_code=404, detail="Khutba not found")
    return k

@router.put("/{id}", response_model=JumaKhutbaResponse)
async def update_khutba(id: int, data: JumaKhutbaUpdate, current_user=Depends(require_permission("khutba.manage")), db: AsyncSession = Depends(get_db)):
    k = await db.get(JumaKhutba, id)
    if not k:
        raise HTTPException(status_code=404, detail="Khutba not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(k, f, v)
    await db.commit()
    return k

