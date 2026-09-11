import os
import uuid
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.bulletins import FridayBulletin
from app.schemas.bulletins import BulletinResponse
from app.api.dependencies.auth import get_current_admin_user
from app.services.aws import upload_file_to_s3, delete_file_from_s3
from app.core.config import settings

router = APIRouter()

@router.get("/", response_model=List[BulletinResponse])
async def list_bulletins(
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    query = select(FridayBulletin)
    if active_only:
        query = query.filter(FridayBulletin.is_active == True)
    
    query = query.order_by(FridayBulletin.published_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{bulletin_id}", response_model=BulletinResponse)
async def get_bulletin(
    bulletin_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(FridayBulletin).filter(FridayBulletin.id == bulletin_id))
    bulletin = result.scalars().first()
    if not bulletin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bulletin not found")
    return bulletin

from app.services.firebase import firebase_service
from app.models.khutba import NotificationLog

@router.post("/", response_model=BulletinResponse, status_code=status.HTTP_201_CREATED)
async def create_bulletin(
    title: str = Form(...),
    issue_number: Optional[str] = Form(None),
    published_date: date = Form(...),
    pdf_file: UploadFile = File(...),
    cover_image: Optional[UploadFile] = File(None),
    is_active: bool = Form(True),
    send_notification: bool = Form(True),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    if not pdf_file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed for bulletins.")

    # Save PDF to S3
    pdf_object_name = f"bulletins/{uuid.uuid4().hex}_{pdf_file.filename}"
    try:
        pdf_url = upload_file_to_s3(pdf_file.file, pdf_object_name, content_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload PDF: {str(e)}")

    # Save Cover Image to S3
    cover_image_url = None
    if cover_image:
        cover_object_name = f"bulletins/cover_{uuid.uuid4().hex}_{cover_image.filename}"
        try:
            cover_image_url = upload_file_to_s3(cover_image.file, cover_object_name, content_type=cover_image.content_type)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload cover image: {str(e)}")

    bulletin = FridayBulletin(
        title=title,
        issue_number=issue_number,
        published_date=published_date,
        pdf_path=pdf_url,
        cover_image_path=cover_image_url,
        is_active=is_active
    )
    db.add(bulletin)
    await db.commit()
    await db.refresh(bulletin)
    
    # Broadcast Push Notification to all users
    if send_notification and is_active:
        issue_str = f" #{issue_number}" if issue_number else ""
        notif_title = f"New Friday Bulletin Issue{issue_str} Out Now!"
        notif_body = f"{title} - Read today's Friday sermon & community updates."
        
        payload = {
            "type": "bulletin",
            "bulletin_id": str(bulletin.id),
            "title": str(bulletin.title),
            "issue_number": str(bulletin.issue_number or "")
        }

        # Send to all_users and bulletins topics
        firebase_service.send_topic_notification(
            topic="all_users",
            title=notif_title,
            body=notif_body,
            data=payload,
            image_url=cover_image_url
        )
        firebase_service.send_topic_notification(
            topic="bulletins",
            title=notif_title,
            body=notif_body,
            data=payload,
            image_url=cover_image_url
        )

        # Log notification in DB
        log = NotificationLog(
            title=notif_title,
            body=notif_body,
            image_url=cover_image_url,
            recipient_count=1
        )
        db.add(log)
        await db.commit()

    return bulletin

@router.post("/{bulletin_id}/notify")
async def notify_bulletin(
    bulletin_id: int,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually broadcast a push notification for a specific Friday Bulletin to all users.
    """
    result = await db.execute(select(FridayBulletin).filter(FridayBulletin.id == bulletin_id))
    bulletin = result.scalars().first()
    if not bulletin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bulletin not found")

    issue_str = f" #{bulletin.issue_number}" if bulletin.issue_number else ""
    notif_title = f"The Friday Bulletin Issue{issue_str}"
    notif_body = f"{bulletin.title} - Tap to read online."
    
    payload = {
        "type": "bulletin",
        "bulletin_id": str(bulletin.id),
        "title": str(bulletin.title),
        "issue_number": str(bulletin.issue_number or "")
    }

    firebase_service.send_topic_notification(
        topic="all_users",
        title=notif_title,
        body=notif_body,
        data=payload,
        image_url=bulletin.cover_image_path
    )
    firebase_service.send_topic_notification(
        topic="bulletins",
        title=notif_title,
        body=notif_body,
        data=payload,
        image_url=bulletin.cover_image_path
    )

    log = NotificationLog(
        title=notif_title,
        body=notif_body,
        image_url=bulletin.cover_image_path,
        recipient_count=1
    )
    db.add(log)
    await db.commit()

    return {"status": "success", "message": "Notification broadcast initiated", "bulletin_id": bulletin_id}

def _extract_s3_key(url: str) -> Optional[str]:
    if not url:
        return None
    bucket_prefix = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"
    if url.startswith(bucket_prefix):
        return url[len(bucket_prefix):]
    return None

@router.delete("/{bulletin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bulletin(
    bulletin_id: int,
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(FridayBulletin).filter(FridayBulletin.id == bulletin_id))
    bulletin = result.scalars().first()
    if not bulletin:
        raise HTTPException(status_code=404, detail="Bulletin not found")

    # Delete physical files from S3
    if bulletin.pdf_path:
        pdf_key = _extract_s3_key(bulletin.pdf_path)
        if pdf_key:
            delete_file_from_s3(pdf_key)
            
    if bulletin.cover_image_path:
        cover_key = _extract_s3_key(bulletin.cover_image_path)
        if cover_key:
            delete_file_from_s3(cover_key)

    await db.delete(bulletin)
    await db.commit()
