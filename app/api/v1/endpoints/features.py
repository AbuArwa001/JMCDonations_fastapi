from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.repositories.content_repo import FeatureRepository
from app.models.core_config import AppFeature
from app.schemas.v1.core_config import AppFeatureResponse, AppFeatureCreate, AppFeatureUpdate

router = APIRouter()

@router.get("/", response_model=List[AppFeatureResponse])
async def list_features(db: AsyncSession = Depends(get_db)):
    return await FeatureRepository(db).list_all()

@router.post("/", response_model=AppFeatureResponse, status_code=status.HTTP_201_CREATED)
async def create_feature(data: AppFeatureCreate, current_user=Depends(require_permission("features.manage")), db: AsyncSession = Depends(get_db)):
    repo = FeatureRepository(db)
    if await repo.get_by_name(data.name):
        raise HTTPException(status_code=400, detail="Feature already exists")
    f = AppFeature(**data.model_dump())
    created = await repo.create(f)
    await db.commit()
    return created

@router.put("/{id}", response_model=AppFeatureResponse)
@router.put("/{id}/", response_model=AppFeatureResponse)
@router.patch("/{id}", response_model=AppFeatureResponse)
@router.patch("/{id}/", response_model=AppFeatureResponse)
async def update_feature(id: int, data: AppFeatureUpdate, current_user=Depends(require_permission("features.manage")), db: AsyncSession = Depends(get_db)):
    f = await FeatureRepository(db).get_by_id(id)
    if not f:
        raise HTTPException(status_code=404, detail="Feature not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(f, k, v)
    await db.commit()
    return f

