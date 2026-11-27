import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.repositories.community_repo import CommunityRepository
from app.models.community import CommunityContent
from app.schemas.v1.community import CommunityContentResponse, CommunityContentCreate, CommunityContentUpdate

router = APIRouter()

@router.get("/content", response_model=List[CommunityContentResponse])
@router.get("/content/", response_model=List[CommunityContentResponse])
async def list_content(content_type: str = "darsa", published_only: bool = False, db: AsyncSession = Depends(get_db)):
    return await CommunityRepository(db).list_content_by_type(content_type, published_only=published_only)

@router.post("/content", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/content/", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
async def create_content(data: CommunityContentCreate, current_user=Depends(require_permission("darsas.manage", "inspiration.manage")), db: AsyncSession = Depends(get_db)):
    c = CommunityContent(**data.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c

@router.get("/content/{id}", response_model=CommunityContentResponse)
@router.get("/content/{id}/", response_model=CommunityContentResponse)
async def get_content(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    c = await db.get(CommunityContent, id)
    if not c:
        raise HTTPException(status_code=404, detail="Content not found")
    return c

@router.put("/content/{id}", response_model=CommunityContentResponse)
@router.put("/content/{id}/", response_model=CommunityContentResponse)
@router.patch("/content/{id}", response_model=CommunityContentResponse)
@router.patch("/content/{id}/", response_model=CommunityContentResponse)
async def update_content(id: uuid.UUID, data: CommunityContentUpdate, current_user=Depends(require_permission("darsas.manage", "inspiration.manage")), db: AsyncSession = Depends(get_db)):
    c = await db.get(CommunityContent, id)
    if not c:
        raise HTTPException(status_code=404, detail="Content not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(c, f, v)
    await db.commit()
    await db.refresh(c)
    return c

@router.delete("/content/{id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/content/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(id: uuid.UUID, current_user=Depends(require_permission("darsas.manage", "inspiration.manage")), db: AsyncSession = Depends(get_db)):
    c = await db.get(CommunityContent, id)
    if not c:
        raise HTTPException(status_code=404, detail="Content not found")
    await db.delete(c)
    await db.commit()
    return None

@router.get("/darsas", response_model=List[CommunityContentResponse])
@router.get("/darsas/", response_model=List[CommunityContentResponse])
async def list_darsas(db: AsyncSession = Depends(get_db)):
    return await CommunityRepository(db).list_content_by_type("darsa")

@router.post("/darsas", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/darsas/", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
async def create_darsa(data: CommunityContentCreate, current_user=Depends(require_permission("darsas.manage")), db: AsyncSession = Depends(get_db)):
    c = CommunityContent(**data.model_dump())
    c.content_type = "darsa"
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c

@router.get("/inspiration", response_model=List[CommunityContentResponse])
@router.get("/inspiration/", response_model=List[CommunityContentResponse])
async def list_inspiration(db: AsyncSession = Depends(get_db)):
    return await CommunityRepository(db).list_content_by_type("inspiration")

@router.post("/inspiration", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/inspiration/", response_model=CommunityContentResponse, status_code=status.HTTP_201_CREATED)
async def create_inspiration(data: CommunityContentCreate, current_user=Depends(require_permission("inspiration.manage")), db: AsyncSession = Depends(get_db)):
    c = CommunityContent(**data.model_dump())
    c.content_type = "inspiration"
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c
