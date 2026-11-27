from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, require_permission
from app.models.khutba import JumaKhutba
from app.schemas.v1.khutba import JumaKhutbaResponse, JumaKhutbaCreate, JumaKhutbaUpdate
from app.api.v1.endpoints.khutba_helpers import parse_date, parse_time, save_khutba_photo

router = APIRouter()

@router.get("/", response_model=List[JumaKhutbaResponse])
async def list_khutbas(published_only: bool = False, db: AsyncSession = Depends(get_db)):
    stmt = select(JumaKhutba)
    if published_only:
        stmt = stmt.where(JumaKhutba.published == True)
    stmt = stmt.order_by(JumaKhutba.khutba_date.desc()).limit(50)
    return list((await db.execute(stmt)).scalars().all())

@router.post("/", response_model=JumaKhutbaResponse, status_code=status.HTTP_201_CREATED)
async def create_khutba(
    request: Request,
    current_user=Depends(require_permission("khutba.manage")),
    db: AsyncSession = Depends(get_db)
):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        title, imam = form.get("title"), form.get("imam_name")
        if not title or not imam:
            raise HTTPException(status_code=400, detail="Title and imam_name are required")
        photo = save_khutba_photo(form.get("imam_photo"))
        k = JumaKhutba(
            title=str(title), imam_name=str(imam),
            khutba_date=parse_date(form.get("khutba_date")),
            khutba_time=parse_time(form.get("khutba_time")),
            imam_photo=photo, topic_summary=str(form.get("topic_summary")) if form.get("topic_summary") else None,
            published=str(form.get("published", "true")).lower() in ("true", "1", "yes"),
            created_by_id=current_user.id if current_user else None
        )
    else:
        k = JumaKhutba(**JumaKhutbaCreate(**(await request.json())).model_dump(), created_by_id=current_user.id if current_user else None)
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
@router.patch("/{id}", response_model=JumaKhutbaResponse)
@router.patch("/{id}/", response_model=JumaKhutbaResponse)
async def update_khutba(
    id: int, request: Request,
    current_user=Depends(require_permission("khutba.manage")),
    db: AsyncSession = Depends(get_db)
):
    k = await db.get(JumaKhutba, id)
    if not k:
        raise HTTPException(status_code=404, detail="Khutba not found")
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        if "title" in form: k.title = str(form.get("title"))
        if "imam_name" in form: k.imam_name = str(form.get("imam_name"))
        if "khutba_date" in form: k.khutba_date = parse_date(form.get("khutba_date"))
        if "khutba_time" in form: k.khutba_time = parse_time(form.get("khutba_time"))
        if "topic_summary" in form: k.topic_summary = str(form.get("topic_summary"))
        if "published" in form: k.published = str(form.get("published")).lower() in ("true", "1", "yes")
        photo = save_khutba_photo(form.get("imam_photo"))
        if photo: k.imam_photo = photo
    else:
        for f, v in JumaKhutbaUpdate(**(await request.json())).model_dump(exclude_unset=True).items():
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
