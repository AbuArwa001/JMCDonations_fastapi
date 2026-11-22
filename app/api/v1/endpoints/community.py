import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.repositories.community_repo import CommunityRepository
from app.models.community import CommunityContent
from app.schemas.v1.community import CommunityContentResponse, CommunityContentCreate, CommunityContentUpdate

router = APIRouter()

@router.get("/darsas", response_model=List[CommunityContentResponse])
async def list_darsas(db: AsyncSession = Depends(get_db)):
    return await CommunityRepository(db).list_content_by_type("darsa")

@router.post("/darsas", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
async def create_darsa(data: CommunityContentCreate, current_user=Depends(require_permission("darsas.manage")), db: AsyncSession = Depends(get_db)):
    c = CommunityContent(**data.model_dump())
    c.content_type = "darsa"
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c

@router.get("/inspiration", response_model=List[CommunityContentResponse])
async def list_inspiration(db: AsyncSession = Depends(get_db)):
    return await CommunityRepository(db).list_content_by_type("inspiration")

@router.post("/inspiration", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
async def create_inspiration(data: CommunityContentCreate, current_user=Depends(require_permission("inspiration.manage")), db: AsyncSession = Depends(get_db)):
    c = CommunityContent(**data.model_dump())
    c.content_type = "inspiration"
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c

