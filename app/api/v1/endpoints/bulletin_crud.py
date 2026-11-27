import os
import shutil
import uuid
from datetime import date
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.repositories.community_repo import CommunityRepository
from app.models.bulletins import FridayBulletin
from app.schemas.v1.bulletins import FridayBulletinResponse, FridayBulletinCreate, FridayBulletinUpdate
from app.api.v1.endpoints.bulletin_notify import auto_notify_bulletin

router = APIRouter()

@router.get("/", response_model=List[FridayBulletinResponse])
async def list_bulletins(db: AsyncSession = Depends(get_db)):
    return await CommunityRepository(db).list_bulletins()

def _save_file(upload, prefix: str, ext_fallback: str) -> str:
    ext = os.path.splitext(getattr(upload, "filename", "") or "")[1] or ext_fallback
    fname = f"{prefix}_{uuid.uuid4().hex[:10]}{ext}"
    dest = Path("static/bulletins") / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as buf:
        shutil.copyfileobj(upload.file, buf)
    return f"/static/bulletins/{fname}"

@router.post("/", response_model=FridayBulletinResponse, status_code=status.HTTP_201_CREATED)
async def create_bulletin(
    request: Request,
    current_user=Depends(require_permission("bulletins.manage")),
    db: AsyncSession = Depends(get_db)
):
    if "multipart/form-data" in request.headers.get("content-type", ""):
        form = await request.form()
        title, pub_date = form.get("title"), form.get("published_date")
        if not title or not pub_date:
            raise HTTPException(status_code=400, detail="Title and published_date are required")
        pdf_f, img_f = form.get("pdf_file"), form.get("cover_image")
        pdf_path = _save_file(pdf_f, "bulletin", ".pdf") if pdf_f and hasattr(pdf_f, "filename") else ""
        cover_path = _save_file(img_f, "cover", ".jpg") if img_f and hasattr(img_f, "filename") else None
        bulletin = FridayBulletin(
            title=str(title), issue_number=str(form.get("issue_number")) if form.get("issue_number") else None,
            published_date=date.fromisoformat(str(pub_date)), pdf_path=pdf_path, cover_image_path=cover_path,
            is_active=str(form.get("is_active", "true")).lower() in ("true", "1")
        )
    else:
        bulletin = FridayBulletin(**FridayBulletinCreate(**(await request.json())).model_dump())
    db.add(bulletin)
    await db.commit()
    await db.refresh(bulletin)
    if bulletin.is_active:
        await auto_notify_bulletin(db, bulletin)
    return bulletin

@router.get("/{id}", response_model=FridayBulletinResponse)
@router.get("/{id}/", response_model=FridayBulletinResponse)
async def get_bulletin(id: int, db: AsyncSession = Depends(get_db)):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    return b

@router.put("/{id}", response_model=FridayBulletinResponse)
@router.put("/{id}/", response_model=FridayBulletinResponse)
async def update_bulletin(id: int, data: FridayBulletinUpdate, current_user=Depends(require_permission("bulletins.manage")), db: AsyncSession = Depends(get_db)):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(b, f, v)
    await db.commit()
    return b

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bulletin(id: int, current_user=Depends(require_permission("bulletins.manage")), db: AsyncSession = Depends(get_db)):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    await db.delete(b)
    await db.commit()
