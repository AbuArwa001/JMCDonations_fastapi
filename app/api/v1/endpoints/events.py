from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, require_permission
from app.repositories.community_repo import CommunityRepository
from app.models.events import Event, EventCategory
from app.schemas.v1.events import (
    EventResponse, EventCreate, EventUpdate, EventCategoryResponse, EventCategoryCreate
)

router = APIRouter()

@router.get("/", response_model=List[EventResponse])
async def list_events(upcoming_only: bool = False, db: AsyncSession = Depends(get_db)):
    return await CommunityRepository(db).list_events(upcoming_only)

@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(data: EventCreate, current_user=Depends(require_permission("events.manage")), db: AsyncSession = Depends(get_db)):
    event = Event(**data.model_dump(), created_by_id=current_user.id)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.get("/{id}", response_model=EventResponse)
async def get_event(id: int, db: AsyncSession = Depends(get_db)):
    e = await db.get(Event, id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    return e

@router.put("/{id}", response_model=EventResponse)
async def update_event(id: int, data: EventUpdate, current_user=Depends(require_permission("events.manage")), db: AsyncSession = Depends(get_db)):
    e = await db.get(Event, id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(e, f, v)
    await db.commit()
    return e

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(id: int, current_user=Depends(require_permission("events.manage")), db: AsyncSession = Depends(get_db)):
    e = await db.get(Event, id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(e)
    await db.commit()

@router.get("/categories/all", response_model=List[EventCategoryResponse])
async def list_event_categories(db: AsyncSession = Depends(get_db)):
    return list((await db.execute(select(EventCategory))).scalars().all())

