from typing import List, Optional
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, require_permission
from app.models.duas import Dua, DuaCategory
from app.schemas.v1.duas import (
    DuaResponse, DuaCreate, DuaUpdate,
    DuaCategoryResponse, DuaCategoryCreate, DuaCategoryUpdate
)

router = APIRouter()

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '-', text)

@router.get("/categories", response_model=List[DuaCategoryResponse])
@router.get("/categories/", response_model=List[DuaCategoryResponse])
async def list_dua_categories(db: AsyncSession = Depends(get_db)):
    return list((await db.execute(select(DuaCategory).order_by(DuaCategory.display_order))).scalars().all())

@router.post("/categories", response_model=DuaCategoryResponse, status_code=status.HTTP_201_CREATED)
@router.post("/categories/", response_model=DuaCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_dua_category(data: DuaCategoryCreate, current_user=Depends(require_permission("duas.manage")), db: AsyncSession = Depends(get_db)):
    slug = data.slug or slugify(data.name)
    existing = (await db.execute(select(DuaCategory).where(DuaCategory.slug == slug))).scalars().first()
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"
    cat = DuaCategory(name=data.name, slug=slug, icon=data.icon, display_order=data.display_order)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat

@router.put("/categories/{id}", response_model=DuaCategoryResponse)
@router.put("/categories/{id}/", response_model=DuaCategoryResponse)
@router.patch("/categories/{id}", response_model=DuaCategoryResponse)
@router.patch("/categories/{id}/", response_model=DuaCategoryResponse)
async def update_dua_category(id: int, data: DuaCategoryUpdate, current_user=Depends(require_permission("duas.manage")), db: AsyncSession = Depends(get_db)):
    cat = await db.get(DuaCategory, id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(cat, f, v)
    await db.commit()
    await db.refresh(cat)
    return cat

@router.delete("/categories/{id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/categories/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dua_category(id: int, current_user=Depends(require_permission("duas.manage")), db: AsyncSession = Depends(get_db)):
    cat = await db.get(DuaCategory, id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    await db.commit()
    return None

@router.get("/", response_model=List[DuaResponse])
@router.get("", response_model=List[DuaResponse])
async def list_duas(category_id: Optional[int] = None, published_only: bool = False, db: AsyncSession = Depends(get_db)):
    stmt = select(Dua)
    if published_only:
        stmt = stmt.where(Dua.published.is_(True))
    if category_id:
        stmt = stmt.where(Dua.category_id == category_id)
    return list((await db.execute(stmt.order_by(Dua.display_order))).scalars().all())

@router.post("/", response_model=DuaResponse, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=DuaResponse, status_code=status.HTTP_201_CREATED)
async def create_dua(data: DuaCreate, current_user=Depends(require_permission("duas.manage")), db: AsyncSession = Depends(get_db)):
    d = Dua(**data.model_dump())
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d

@router.get("/{id}", response_model=DuaResponse)
@router.get("/{id}/", response_model=DuaResponse)
async def get_dua(id: int, db: AsyncSession = Depends(get_db)):
    d = await db.get(Dua, id)
    if not d:
        raise HTTPException(status_code=404, detail="Dua not found")
    return d

@router.put("/{id}", response_model=DuaResponse)
@router.put("/{id}/", response_model=DuaResponse)
@router.patch("/{id}", response_model=DuaResponse)
@router.patch("/{id}/", response_model=DuaResponse)
async def update_dua(id: int, data: DuaUpdate, current_user=Depends(require_permission("duas.manage")), db: AsyncSession = Depends(get_db)):
    d = await db.get(Dua, id)
    if not d:
        raise HTTPException(status_code=404, detail="Dua not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(d, f, v)
    await db.commit()
    await db.refresh(d)
    return d

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dua(id: int, current_user=Depends(require_permission("duas.manage")), db: AsyncSession = Depends(get_db)):
    d = await db.get(Dua, id)
    if not d:
        raise HTTPException(status_code=404, detail="Dua not found")
    await db.delete(d)
    await db.commit()
    return None
