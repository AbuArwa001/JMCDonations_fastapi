import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.category_repo import CategoryRepository
from app.models.categories import Category
from app.schemas.v1.categories import CategoryCreate, CategoryUpdate

class CategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CategoryRepository(db)

    async def create_category(self, data: CategoryCreate) -> Category:
        existing = await self.repo.get_by_name(data.category_name)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists")
        cat = Category(category_name=data.category_name, color=data.color)
        created = await self.repo.create(cat)
        await self.db.commit()
        return created

    async def update_category(self, cat_id: uuid.UUID, data: CategoryUpdate) -> Category:
        cat = await self.repo.get_by_id(cat_id)
        if not cat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        if data.category_name is not None:
            cat.category_name = data.category_name
        if data.color is not None:
            cat.color = data.color
        await self.db.commit()
        return cat

