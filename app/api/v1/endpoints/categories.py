import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.repositories.category_repo import CategoryRepository
from app.services.category_service import CategoryService
from app.schemas.v1.categories import CategoryResponse, CategoryCreate, CategoryUpdate

router = APIRouter()

@router.get("", response_model=List[CategoryResponse])
@router.get("/", response_model=List[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await CategoryRepository(db).list_all()

@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryCreate, current_user=Depends(require_permission("categories.manage")), db: AsyncSession = Depends(get_db)):
    return await CategoryService(db).create_category(data)

@router.get("/{id}", response_model=CategoryResponse)
async def get_category(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cat = await CategoryRepository(db).get_by_id(id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat

@router.put("/{id}", response_model=CategoryResponse)
async def update_category(id: uuid.UUID, data: CategoryUpdate, current_user=Depends(require_permission("categories.manage")), db: AsyncSession = Depends(get_db)):
    return await CategoryService(db).update_category(id, data)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(id: uuid.UUID, current_user=Depends(require_permission("categories.manage")), db: AsyncSession = Depends(get_db)):
    repo = CategoryRepository(db)
    cat = await repo.get_by_id(id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await repo.delete(cat)
    await db.commit()
