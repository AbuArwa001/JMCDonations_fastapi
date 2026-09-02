from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.db.session import get_db
from app.models.community import CommunityContent
from app.schemas.community import CommunityContentCreate, CommunityContentUpdate, CommunityContentResponse

router = APIRouter()

@router.get("/", response_model=List[CommunityContentResponse])
async def list_community_content(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommunityContent).order_by(CommunityContent.created_at.desc()))
    return result.scalars().all()

@router.post("/", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
async def create_community_content(content_in: CommunityContentCreate, db: AsyncSession = Depends(get_db)):
    db_content = CommunityContent(**content_in.model_dump())
    db.add(db_content)
    await db.commit()
    await db.refresh(db_content)
    return db_content

@router.get("/{content_id}", response_model=CommunityContentResponse)
async def get_community_content(content_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommunityContent).filter(CommunityContent.id == content_id))
    db_content = result.scalars().first()
    if not db_content:
        raise HTTPException(status_code=404, detail="Content not found")
    return db_content

@router.put("/{content_id}", response_model=CommunityContentResponse)
async def update_community_content(content_id: uuid.UUID, content_in: CommunityContentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommunityContent).filter(CommunityContent.id == content_id))
    db_content = result.scalars().first()
    if not db_content:
        raise HTTPException(status_code=404, detail="Content not found")
        
    update_data = content_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_content, key, value)
        
    await db.commit()
    await db.refresh(db_content)
    return db_content

@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_community_content(content_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommunityContent).filter(CommunityContent.id == content_id))
    db_content = result.scalars().first()
    if not db_content:
        raise HTTPException(status_code=404, detail="Content not found")
        
    await db.delete(db_content)
    await db.commit()
