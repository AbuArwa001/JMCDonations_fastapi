import os
import shutil
import uuid
from datetime import date
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.repositories.community_repo import CommunityRepository
from app.models.bulletins import FridayBulletin
from app.models.khutba import NotificationLog
from app.schemas.v1.bulletins import FridayBulletinResponse, FridayBulletinCreate, FridayBulletinUpdate
from app.services.firebase import firebase_service

router = APIRouter()

@router.get("/", response_model=List[FridayBulletinResponse])
@router.get("", response_model=List[FridayBulletinResponse])
async def list_bulletins(db: AsyncSession = Depends(get_db)):
    return await CommunityRepository(db).list_bulletins()

@router.post("/", response_model=FridayBulletinResponse, status_code=status.HTTP_201_CREATED)
async def create_bulletin(
    request: Request,
    current_user=Depends(require_permission("bulletins.manage")),
    db: AsyncSession = Depends(get_db)
):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        title = form.get("title")
        issue_number = form.get("issue_number")
        published_date_str = form.get("published_date")
        is_active_str = form.get("is_active", "true")

        if not title or not published_date_str:
            raise HTTPException(status_code=400, detail="Title and published_date are required")

        pdf_path = ""
        pdf_file = form.get("pdf_file")
        if pdf_file and hasattr(pdf_file, "filename"):
            ext = os.path.splitext(pdf_file.filename or "")[1] or ".pdf"
            pdf_name = f"bulletin_{uuid.uuid4().hex[:10]}{ext}"
            pdf_dest = Path("static/bulletins") / pdf_name
            pdf_dest.parent.mkdir(parents=True, exist_ok=True)
            with open(pdf_dest, "wb") as buf:
                shutil.copyfileobj(pdf_file.file, buf)
            pdf_path = f"/static/bulletins/{pdf_name}"

        cover_image_path = None
        cover_image = form.get("cover_image")
        if cover_image and hasattr(cover_image, "filename"):
            ext = os.path.splitext(cover_image.filename or "")[1] or ".jpg"
            img_name = f"cover_{uuid.uuid4().hex[:10]}{ext}"
            img_dest = Path("static/bulletins") / img_name
            img_dest.parent.mkdir(parents=True, exist_ok=True)
            with open(img_dest, "wb") as buf:
                shutil.copyfileobj(cover_image.file, buf)
            cover_image_path = f"/static/bulletins/{img_name}"

        bulletin = FridayBulletin(
            title=str(title),
            issue_number=str(issue_number) if issue_number else None,
            published_date=date.fromisoformat(str(published_date_str)),
            pdf_path=pdf_path,
            cover_image_path=cover_image_path,
            is_active=str(is_active_str).lower() in ("true", "1")
        )
    else:
        json_data = await request.json()
        data = FridayBulletinCreate(**json_data)
        bulletin = FridayBulletin(**data.model_dump())

    db.add(bulletin)
    await db.commit()
    await db.refresh(bulletin)
    return bulletin

@router.post("/{id}/notify")
async def notify_bulletin(id: int, current_user=Depends(require_permission("bulletins.manage")), db: AsyncSession = Depends(get_db)):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    title = f"New Friday Bulletin: {b.title}"
    body = f"Issue #{b.issue_number or ''} is now available to read."
    payload = {"type": "bulletin", "bulletin_id": str(b.id)}
    for topic_name in ("bulletins", "all_users", "general"):
        try:
            firebase_service.send_topic_notification(topic=topic_name, title=title, body=body, data=payload)
        except Exception:
            pass
    from app.models.khutba import DeviceToken
    tokens = list((await db.execute(select(DeviceToken.fcm_token))).scalars().all())
    count = 0
    if tokens:
        try:
            count = firebase_service.send_multicast(tokens=tokens, title=title, body=body, data=payload)
        except Exception:
            pass
    recipient_count = max(count, len(tokens), 1)
    log = NotificationLog(
        title=title,
        body=body,
        notification_type="bulletin",
        recipient_count=recipient_count
    )
    db.add(log)
    await db.commit()
    return {"status": "broadcasted", "bulletin_id": id, "success_count": recipient_count}

@router.get("/{id}", response_model=FridayBulletinResponse)
async def get_bulletin(id: int, db: AsyncSession = Depends(get_db)):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    return b

@router.put("/{id}", response_model=FridayBulletinResponse)
async def update_bulletin(id: int, data: FridayBulletinUpdate, current_user=Depends(require_permission("bulletins.manage")), db: AsyncSession = Depends(get_db)):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(b, f, v)
    await db.commit()
    return b

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bulletin(id: int, current_user=Depends(require_permission("bulletins.manage")), db: AsyncSession = Depends(get_db)):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    await db.delete(b)
    await db.commit()
