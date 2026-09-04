from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.khutba import JumaKhutba, DeviceToken, NotificationLog
from app.models.users import User
from app.schemas.khutba import (
    JumaKhutbaCreate, JumaKhutbaUpdate, JumaKhutbaResponse,
    DeviceTokenCreate, DeviceTokenResponse,
    NotificationLogResponse
)
from app.api.dependencies.auth import get_current_admin_user

router = APIRouter()

# ==================== Juma Khutba ====================

@router.get("/", response_model=List[JumaKhutbaResponse])
async def list_khutbas(
    published_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    query = select(JumaKhutba)
    if published_only:
        query = query.filter(JumaKhutba.published == True)
    query = query.order_by(JumaKhutba.khutba_date.desc(), JumaKhutba.khutba_time.desc())
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=JumaKhutbaResponse, status_code=status.HTTP_201_CREATED)
async def create_khutba(
    khutba_in: JumaKhutbaCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_khutba = JumaKhutba(**khutba_in.model_dump(), created_by_id=current_user.id)
    db.add(db_khutba)
    await db.commit()
    await db.refresh(db_khutba)
    return db_khutba

@router.get("/{khutba_id}", response_model=JumaKhutbaResponse)
async def get_khutba(khutba_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JumaKhutba).filter(JumaKhutba.id == khutba_id))
    khutba = result.scalars().first()
    if not khutba:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khutba not found")
    return khutba

@router.patch("/{khutba_id}", response_model=JumaKhutbaResponse)
@router.put("/{khutba_id}", response_model=JumaKhutbaResponse)
async def update_khutba(
    khutba_id: int,
    khutba_in: JumaKhutbaUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(JumaKhutba).filter(JumaKhutba.id == khutba_id))
    khutba = result.scalars().first()
    if not khutba:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khutba not found")

    update_data = khutba_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(khutba, field, value)

    await db.commit()
    await db.refresh(khutba)
    return khutba

@router.delete("/{khutba_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_khutba(
    khutba_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(JumaKhutba).filter(JumaKhutba.id == khutba_id))
    khutba = result.scalars().first()
    if not khutba:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khutba not found")

    await db.delete(khutba)
    await db.commit()

@router.post("/{khutba_id}/notify")
async def notify_khutba(
    khutba_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(JumaKhutba).filter(JumaKhutba.id == khutba_id))
    khutba = result.scalars().first()
    if not khutba:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khutba not found")

    log = NotificationLog(
        title=f"Juma Khutba: {khutba.title}",
        body=f"By Sheikh {khutba.imam_name} on {khutba.khutba_date}",
        image_url=khutba.imam_photo,
        related_khutba_id=khutba.id,
        recipient_count=1
    )
    db.add(log)
    await db.commit()
    return {"status": "success", "message": "Notification broadcast initiated", "khutba_id": khutba_id}

# ==================== Device Tokens ====================

@router.post("/register-device", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_device_token(token_in: DeviceTokenCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeviceToken).filter(DeviceToken.fcm_token == token_in.fcm_token))
    existing = result.scalars().first()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if existing:
        existing.last_seen_at = now_utc
        existing.platform = token_in.platform
        await db.commit()
        await db.refresh(existing)
        return existing

    device = DeviceToken(
        fcm_token=token_in.fcm_token,
        platform=token_in.platform,
        registered_at=now_utc,
        last_seen_at=now_utc
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device

# ==================== Notification Logs ====================

@router.get("/logs", response_model=List[NotificationLogResponse])
async def list_notification_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(NotificationLog).order_by(NotificationLog.sent_at.desc()).limit(limit))
    return result.scalars().all()
