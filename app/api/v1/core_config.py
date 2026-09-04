from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.core_config import AppFeature
from app.models.users import User
from app.schemas.core_config import AppFeatureCreate, AppFeatureUpdate, AppFeatureResponse
from app.api.dependencies.auth import get_current_admin_user

router = APIRouter()

@router.get("/", response_model=List[AppFeatureResponse])
async def list_features(active_only: bool = False, db: AsyncSession = Depends(get_db)):
    """
    List application feature flags.
    """
    query = select(AppFeature)
    if active_only:
        query = query.filter(AppFeature.is_active == True)
    query = query.order_by(AppFeature.name)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=AppFeatureResponse, status_code=status.HTTP_201_CREATED)
async def create_feature(
    feature_in: AppFeatureCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new feature flag (Admin only).
    """
    existing = await db.execute(select(AppFeature).filter(AppFeature.name == feature_in.name))
    if existing.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Feature flag already exists")

    db_feature = AppFeature(**feature_in.model_dump())
    db.add(db_feature)
    await db.commit()
    await db.refresh(db_feature)
    return db_feature

@router.get("/{feature_id}", response_model=AppFeatureResponse)
async def get_feature(feature_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppFeature).filter(AppFeature.id == feature_id))
    feature = result.scalars().first()
    if not feature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    return feature

@router.patch("/{feature_id}", response_model=AppFeatureResponse)
@router.put("/{feature_id}", response_model=AppFeatureResponse)
async def update_feature(
    feature_id: int,
    feature_in: AppFeatureUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(AppFeature).filter(AppFeature.id == feature_id))
    feature = result.scalars().first()
    if not feature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")

    update_data = feature_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feature, field, value)

    feature.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(feature)
    return feature

@router.delete("/{feature_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature(
    feature_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(AppFeature).filter(AppFeature.id == feature_id))
    feature = result.scalars().first()
    if not feature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")

    await db.delete(feature)
    await db.commit()
