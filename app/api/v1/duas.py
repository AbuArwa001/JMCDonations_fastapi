import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.duas import Dua, DuaCategory
from app.models.users import User
from app.schemas.content import (
    DuaCreate, DuaUpdate, DuaResponse,
    DuaCategoryCreate, DuaCategoryUpdate, DuaCategoryResponse
)
from app.api.dependencies.auth import get_current_admin_user

router = APIRouter()

def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    return re.sub(r'[\s_-]+', '-', s)

# ==================== Dua Categories ====================

@router.get("/categories", response_model=List[DuaCategoryResponse])
async def list_dua_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DuaCategory).order_by(DuaCategory.display_order))
    return result.scalars().all()

@router.post("/categories", response_model=DuaCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_dua_category(
    cat_in: DuaCategoryCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    base_slug = cat_in.slug or slugify(cat_in.name)
    slug = base_slug
    counter = 1
    while True:
        existing = await db.execute(select(DuaCategory).filter(DuaCategory.slug == slug))
        if not existing.scalars().first():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    db_cat = DuaCategory(
        name=cat_in.name,
        slug=slug,
        icon=cat_in.icon,
        display_order=cat_in.display_order
    )
    db.add(db_cat)
    await db.commit()
    await db.refresh(db_cat)
    return db_cat

@router.get("/categories/{category_id}", response_model=DuaCategoryResponse)
async def get_dua_category(category_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DuaCategory).filter(DuaCategory.id == category_id))
    cat = result.scalars().first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dua category not found")
    return cat

@router.patch("/categories/{category_id}", response_model=DuaCategoryResponse)
@router.put("/categories/{category_id}", response_model=DuaCategoryResponse)
async def update_dua_category(
    category_id: int,
    cat_in: DuaCategoryUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DuaCategory).filter(DuaCategory.id == category_id))
    cat = result.scalars().first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dua category not found")

    update_data = cat_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cat, field, value)

    await db.commit()
    await db.refresh(cat)
    return cat

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dua_category(
    category_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DuaCategory).filter(DuaCategory.id == category_id))
    cat = result.scalars().first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dua category not found")

    await db.delete(cat)
    await db.commit()

# ==================== Duas ====================

@router.get("/", response_model=List[DuaResponse])
async def list_duas(
    category_id: Optional[int] = None,
    published_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    query = select(Dua)
    if category_id is not None:
        query = query.filter(Dua.category_id == category_id)
    if published_only:
        query = query.filter(Dua.published == True)
    query = query.order_by(Dua.display_order)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=DuaResponse, status_code=status.HTTP_201_CREATED)
async def create_dua(
    dua_in: DuaCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_dua = Dua(**dua_in.model_dump())
    db.add(db_dua)
    await db.commit()
    await db.refresh(db_dua)
    return db_dua

@router.get("/{dua_id}", response_model=DuaResponse)
async def get_dua(dua_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dua).filter(Dua.id == dua_id))
    dua = result.scalars().first()
    if not dua:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dua not found")
    return dua

@router.patch("/{dua_id}", response_model=DuaResponse)
@router.put("/{dua_id}", response_model=DuaResponse)
async def update_dua(
    dua_id: int,
    dua_in: DuaUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Dua).filter(Dua.id == dua_id))
    dua = result.scalars().first()
    if not dua:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dua not found")

    update_data = dua_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dua, field, value)

    await db.commit()
    await db.refresh(dua)
    return dua

@router.delete("/{dua_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dua(
    dua_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Dua).filter(Dua.id == dua_id))
    dua = result.scalars().first()
    if not dua:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dua not found")

    await db.delete(dua)
    await db.commit()
