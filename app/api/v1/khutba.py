from typing import List, Optional
from datetime import date, time
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
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
from app.services.firebase import firebase_service
from app.services.s3_service import upload_file_to_s3

router = APIRouter()


def _send_khutba_fcm(khutba: JumaKhutba) -> None:
    """Broadcast FCM notification for a Khutba to JamiaGive users."""
    title = f"Friday Khutba: {khutba.title}"
    body = f"By {khutba.imam_name} on {khutba.khutba_date}. Tap to read the topic summary."
    data = {
        "type": "khutba",
        "khutba_id": str(khutba.id),
        "title": str(khutba.title),
        "imam_name": str(khutba.imam_name),
    }
    image_url = khutba.imam_photo
    firebase_service.send_topic_notification("all_users", title, body, data=data, image_url=image_url)
    firebase_service.send_topic_notification("khutba", title, body, data=data, image_url=image_url)


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
    title: str = Form(...),
    imam_name: str = Form(...),
    khutba_date: date = Form(...),
    khutba_time: time = Form(...),
    topic_summary: Optional[str] = Form(None),
    published: bool = Form(True),
    imam_photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    imam_photo_url = None
    if imam_photo:
        object_name = f"khutba/imam_{uuid.uuid4().hex}_{imam_photo.filename}"
        try:
            imam_photo_url = await upload_file_to_s3(imam_photo, object_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")

    db_khutba = JumaKhutba(
        title=title,
        imam_name=imam_name,
        khutba_date=khutba_date,
        khutba_time=khutba_time,
        topic_summary=topic_summary,
        published=published,
        imam_photo=imam_photo_url,
        created_by_id=current_user.id
    )
    db.add(db_khutba)
    await db.commit()
    await db.refresh(db_khutba)

    # Auto-broadcast to JamiaGive users on creation
    if db_khutba.published:
        _send_khutba_fcm(db_khutba)
        log = NotificationLog(
            title=f"Friday Khutba: {db_khutba.title}",
            body=f"By {db_khutba.imam_name} on {db_khutba.khutba_date}",
            image_url=db_khutba.imam_photo,
            notification_type="khutba",
            related_khutba_id=db_khutba.id,
            recipient_count=1,
        )
        db.add(log)
        await db.commit()

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
    title: Optional[str] = Form(None),
    imam_name: Optional[str] = Form(None),
    khutba_date: Optional[date] = Form(None),
    khutba_time: Optional[time] = Form(None),
    topic_summary: Optional[str] = Form(None),
    published: Optional[bool] = Form(None),
    imam_photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(JumaKhutba).filter(JumaKhutba.id == khutba_id))
    khutba = result.scalars().first()
    if not khutba:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khutba not found")

    if title is not None: khutba.title = title
    if imam_name is not None: khutba.imam_name = imam_name
    if khutba_date is not None: khutba.khutba_date = khutba_date
    if khutba_time is not None: khutba.khutba_time = khutba_time
    if topic_summary is not None: khutba.topic_summary = topic_summary
    if published is not None: khutba.published = published

    if imam_photo:
        object_name = f"khutba/imam_{uuid.uuid4().hex}_{imam_photo.filename}"
        try:
            imam_photo_url = await upload_file_to_s3(imam_photo, object_name)
            khutba.imam_photo = imam_photo_url
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")

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
    """Manually broadcast a push notification for a Khutba to all JamiaGive users."""
    result = await db.execute(select(JumaKhutba).filter(JumaKhutba.id == khutba_id))
    khutba = result.scalars().first()
    if not khutba:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khutba not found")

    _send_khutba_fcm(khutba)

    log = NotificationLog(
        title=f"Friday Khutba: {khutba.title}",
        body=f"By {khutba.imam_name} on {khutba.khutba_date}",
        image_url=khutba.imam_photo,
        notification_type="khutba",
        related_khutba_id=khutba.id,
        recipient_count=1,
    )
    db.add(log)
    await db.commit()

    return {"status": "success", "message": "Notification broadcast initiated", "khutba_id": khutba_id}


# ==================== Device Tokens ====================

@router.post("/register-device", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register-device/", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED)
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
    result = await db.execute(
        select(NotificationLog).order_by(NotificationLog.sent_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/admin-notifications", response_model=List[NotificationLogResponse])
async def list_admin_notifications(
    limit: int = 30,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns admin-facing notification logs (donations completed, new drives, etc.)."""
    result = await db.execute(
        select(NotificationLog)
        .order_by(NotificationLog.sent_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
