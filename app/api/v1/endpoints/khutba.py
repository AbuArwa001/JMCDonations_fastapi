import os
import shutil
import uuid
from datetime import date, time, datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
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
    existing = (await db.execute(select(DeviceToken).where(DeviceToken.fcm_token == data.fcm_token))).scalars().first()
    if existing:
        return existing
    dev = DeviceToken(fcm_token=data.fcm_token, platform=data.platform)
    db.add(dev)
    await db.commit()
    await db.refresh(dev)
    return dev

@router.get("/", response_model=List[JumaKhutbaResponse])
@router.get("", response_model=List[JumaKhutbaResponse])
async def list_khutbas(published_only: bool = False, db: AsyncSession = Depends(get_db)):
    stmt = select(JumaKhutba)
    if published_only:
        stmt = stmt.where(JumaKhutba.published == True)
    stmt = stmt.order_by(JumaKhutba.khutba_date.desc()).limit(50)
    return list((await db.execute(stmt)).scalars().all())

@router.post("/", response_model=JumaKhutbaResponse, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=JumaKhutbaResponse, status_code=status.HTTP_201_CREATED)
async def create_khutba(
    request: Request,
    current_user=Depends(require_permission("khutba.manage")),
    db: AsyncSession = Depends(get_db)
):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        title = form.get("title")
        imam_name = form.get("imam_name")
        khutba_date_str = form.get("khutba_date")
        khutba_time_str = form.get("khutba_time")
        topic_summary = form.get("topic_summary")
        published_raw = form.get("published", "true")

        if not title or not imam_name:
            raise HTTPException(status_code=400, detail="Title and imam_name are required")

        try:
            k_date = date.fromisoformat(str(khutba_date_str)) if khutba_date_str else date.today()
        except Exception:
            k_date = date.today()

        try:
            if khutba_time_str:
                parts = [int(p) for p in str(khutba_time_str).split(":")[:2]]
                k_time = time(parts[0], parts[1])
            else:
                k_time = time(13, 0)
        except Exception:
            k_time = time(13, 0)

        imam_photo_val = None
        photo_field = form.get("imam_photo")
        if photo_field and hasattr(photo_field, "filename") and photo_field.filename:
            ext = os.path.splitext(photo_field.filename or "")[1] or ".jpg"
            img_name = f"imam_{uuid.uuid4().hex[:10]}{ext}"
            dest = Path("static/khutba") / img_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as buf:
                shutil.copyfileobj(photo_field.file, buf)
            imam_photo_val = f"/static/khutba/{img_name}"
        elif isinstance(photo_field, str) and photo_field:
            imam_photo_val = photo_field

        k = JumaKhutba(
            title=str(title),
            imam_name=str(imam_name),
            khutba_date=k_date,
            khutba_time=k_time,
            imam_photo=imam_photo_val,
            topic_summary=str(topic_summary) if topic_summary else None,
            published=str(published_raw).lower() in ("true", "1", "yes"),
            created_by_id=current_user.id if current_user else None
        )
    else:
        json_data = await request.json()
        data = JumaKhutbaCreate(**json_data)
        k = JumaKhutba(**data.model_dump(), created_by_id=current_user.id if current_user else None)

    db.add(k)
    await db.commit()
    await db.refresh(k)
    return k

@router.get("/{id}", response_model=JumaKhutbaResponse)
@router.get("/{id}/", response_model=JumaKhutbaResponse)
async def get_khutba(id: int, db: AsyncSession = Depends(get_db)):
    k = await db.get(JumaKhutba, id)
    if not k:
        raise HTTPException(status_code=404, detail="Khutba not found")
    return k

@router.put("/{id}", response_model=JumaKhutbaResponse)
@router.put("/{id}/", response_model=JumaKhutbaResponse)
@router.patch("/{id}", response_model=JumaKhutbaResponse)
@router.patch("/{id}/", response_model=JumaKhutbaResponse)
async def update_khutba(
    id: int,
    request: Request,
    current_user=Depends(require_permission("khutba.manage")),
    db: AsyncSession = Depends(get_db)
):
    k = await db.get(JumaKhutba, id)
    if not k:
        raise HTTPException(status_code=404, detail="Khutba not found")

    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        if "title" in form:
            k.title = str(form.get("title"))
        if "imam_name" in form:
            k.imam_name = str(form.get("imam_name"))
        if "khutba_date" in form:
            try:
                k.khutba_date = date.fromisoformat(str(form.get("khutba_date")))
            except Exception:
                pass
        if "khutba_time" in form:
            try:
                parts = [int(p) for p in str(form.get("khutba_time")).split(":")[:2]]
                k.khutba_time = time(parts[0], parts[1])
            except Exception:
                pass
        if "topic_summary" in form:
            k.topic_summary = str(form.get("topic_summary"))
        if "published" in form:
            k.published = str(form.get("published")).lower() in ("true", "1", "yes")

        photo_field = form.get("imam_photo")
        if photo_field and hasattr(photo_field, "filename") and photo_field.filename:
            ext = os.path.splitext(photo_field.filename or "")[1] or ".jpg"
            img_name = f"imam_{uuid.uuid4().hex[:10]}{ext}"
            dest = Path("static/khutba") / img_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as buf:
                shutil.copyfileobj(photo_field.file, buf)
            k.imam_photo = f"/static/khutba/{img_name}"
        elif isinstance(photo_field, str) and photo_field:
            k.imam_photo = photo_field
    else:
        json_data = await request.json()
        data = JumaKhutbaUpdate(**json_data)
        for f, v in data.model_dump(exclude_unset=True).items():
            setattr(k, f, v)

    await db.commit()
    await db.refresh(k)
    return k

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_khutba(id: int, current_user=Depends(require_permission("khutba.manage")), db: AsyncSession = Depends(get_db)):
    k = await db.get(JumaKhutba, id)
    if not k:
        raise HTTPException(status_code=404, detail="Khutba not found")
    await db.delete(k)
    await db.commit()
    return None

@router.post("/{id}/notify")
@router.post("/{id}/notify/")
async def notify_khutba(id: int, current_user=Depends(require_permission("khutba.manage")), db: AsyncSession = Depends(get_db)):
    k = await db.get(JumaKhutba, id)
    if not k:
        raise HTTPException(status_code=404, detail="Khutba not found")
    count = 0
    try:
        firebase_service.send_topic_notification(
            topic="general",
            title=f"Friday Khutba: {k.title}",
            body=f"By {k.imam_name} on {k.khutba_date.strftime('%d %b %Y')}",
        )
        count = 1
    except Exception:
        pass
    log = NotificationLog(
        title=f"Friday Khutba: {k.title}",
        body=f"By {k.imam_name} on {k.khutba_date.strftime('%d %b %Y')}",
        notification_type="khutba",
        related_khutba_id=k.id,
        recipient_count=count
    )
    db.add(log)
    await db.commit()
    return {"status": "success", "success_count": count}
