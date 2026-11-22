from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, require_permission
from app.models.duas import Dua, DuaCategory
from app.schemas.v1.duas import DuaResponse, DuaCreate, DuaUpdate, DuaCategoryResponse, DuaCategoryCreate

router = APIRouter()

@router.get("/", response_model=List[DuaResponse])
async def list_duas(category_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Dua).where(Dua.published.is_(True))
    if category_id:
        stmt = stmt.where(Dua.category_id == category_id)
    return list((await db.execute(stmt.order_by(Dua.display_order))).scalars().all())

@router.post("/", response_model=DuaResponse, status_code=status.HTTP_201_CREATED)
async def create_dua(data: DuaCreate, current_user=Depends(require_permission("duas.manage")), db: AsyncSession = Depends(get_db)):
    d = Dua(**data.model_dump())
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d

@router.get("/categories", response_model=List[DuaCategoryResponse])
async def list_dua_categories(db: AsyncSession = Depends(get_db)):
    return list((await db.execute(select(DuaCategory).order_by(DuaCategory.display_order))).scalars().all())

@router.get("/{id}", response_model=DuaResponse)
async def get_dua(id: int, db: AsyncSession = Depends(get_db)):
    d = await db.get(Dua, id)
    if not d:
        raise HTTPException(status_code=404, detail="Dua not found")
    return d

