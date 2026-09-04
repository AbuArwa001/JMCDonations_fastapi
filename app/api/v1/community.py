import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.community import CommunityContent
from app.models.users import User
from app.schemas.community import CommunityContentCreate, CommunityContentUpdate, CommunityContentResponse
from app.api.dependencies.auth import get_current_admin_user

router = APIRouter()

@router.get("/", response_model=List[CommunityContentResponse])
@router.get("/content", response_model=List[CommunityContentResponse])
async def list_community_content(
    content_type: Optional[str] = None,
    is_published: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(CommunityContent)
    if content_type:
        query = query.filter(CommunityContent.content_type == content_type)
    if is_published is not None:
        query = query.filter(CommunityContent.is_published == is_published)
    query = query.order_by(CommunityContent.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/content", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
async def create_community_content(
    content_in: CommunityContentCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_content = CommunityContent(**content_in.model_dump())
    db.add(db_content)
    await db.commit()
    await db.refresh(db_content)
    return db_content

@router.get("/{content_id}", response_model=CommunityContentResponse)
@router.get("/content/{content_id}", response_model=CommunityContentResponse)
async def get_community_content(content_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommunityContent).filter(CommunityContent.id == content_id))
    db_content = result.scalars().first()
    if not db_content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    return db_content

@router.patch("/{content_id}", response_model=CommunityContentResponse)
@router.put("/{content_id}", response_model=CommunityContentResponse)
@router.patch("/content/{content_id}", response_model=CommunityContentResponse)
@router.put("/content/{content_id}", response_model=CommunityContentResponse)
async def update_community_content(
    content_id: uuid.UUID,
    content_in: CommunityContentUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CommunityContent).filter(CommunityContent.id == content_id))
    db_content = result.scalars().first()
    if not db_content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
        
    update_data = content_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_content, key, value)
        
    await db.commit()
    await db.refresh(db_content)
    return db_content

@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_community_content(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CommunityContent).filter(CommunityContent.id == content_id))
    db_content = result.scalars().first()
    if not db_content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
        
    await db.delete(db_content)
    await db.commit()
