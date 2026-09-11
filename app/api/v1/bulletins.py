import os
import shutil
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

router = APIRouter()

UPLOAD_DIR = "FRIDAY_BULETIN"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

@router.post("/", response_model=BulletinResponse, status_code=status.HTTP_201_CREATED)
async def create_bulletin(
    title: str = Form(...),
    issue_number: Optional[str] = Form(None),
    published_date: date = Form(...),
    pdf_file: UploadFile = File(...),
    cover_image: Optional[UploadFile] = File(None),
    is_active: bool = Form(True),
    current_user = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    if not pdf_file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed for bulletins.")

    # Save PDF
    pdf_filename = f"{uuid.uuid4().hex}_{pdf_file.filename}"
    pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(pdf_file.file, buffer)

    # Save Cover Image
    cover_image_path = None
    if cover_image:
        cover_filename = f"cover_{uuid.uuid4().hex}_{cover_image.filename}"
        cover_path = os.path.join(UPLOAD_DIR, cover_filename)
        with open(cover_path, "wb") as buffer:
            shutil.copyfileobj(cover_image.file, buffer)
        cover_image_path = f"/static/bulletins/{cover_filename}"

    # Relative static path for response
    static_pdf_path = f"/static/bulletins/{pdf_filename}"

    bulletin = FridayBulletin(
        title=title,
        issue_number=issue_number,
        published_date=published_date,
        pdf_path=static_pdf_path,
        cover_image_path=cover_image_path,
        is_active=is_active
    )
    db.add(bulletin)
    await db.commit()
    await db.refresh(bulletin)
    
    return bulletin

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

    # Optionally delete physical files
    if bulletin.pdf_path:
        filename = bulletin.pdf_path.split("/")[-1]
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            
    if bulletin.cover_image_path:
        filename = bulletin.cover_image_path.split("/")[-1]
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    await db.delete(bulletin)
    await db.commit()
