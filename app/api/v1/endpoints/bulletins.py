import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.repositories.community_repo import CommunityRepository
from app.models.bulletins import FridayBulletin
from app.schemas.v1.bulletins import FridayBulletinResponse, FridayBulletinCreate, FridayBulletinUpdate

router = APIRouter()

@router.get("/", response_model=List[FridayBulletinResponse])
async def list_bulletins(db: AsyncSession = Depends(get_db)):
    return await CommunityRepository(db).list_bulletins()

@router.post("/", response_model=FridayBulletinResponse, status_code=status.HTTP_201_CREATED)
async def create_bulletin(data: FridayBulletinCreate, current_user=Depends(require_permission("bulletins.manage")), db: AsyncSession = Depends(get_db)):
    bulletin = FridayBulletin(**data.model_dump())
    db.add(bulletin)
    await db.commit()
    await db.refresh(bulletin)
    return bulletin

@router.get("/{id}", response_model=FridayBulletinResponse)
async def get_bulletin(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    return b

@router.put("/{id}", response_model=FridayBulletinResponse)
async def update_bulletin(id: uuid.UUID, data: FridayBulletinUpdate, current_user=Depends(require_permission("bulletins.manage")), db: AsyncSession = Depends(get_db)):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(b, f, v)
    await db.commit()
    return b

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bulletin(id: uuid.UUID, current_user=Depends(require_permission("bulletins.manage")), db: AsyncSession = Depends(get_db)):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    await db.delete(b)
    await db.commit()

