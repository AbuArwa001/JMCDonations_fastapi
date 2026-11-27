import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.repositories.content_repo import RatingRepository
from app.models.ratings import Rating
from app.models.users import User
from app.schemas.v1.ratings import RatingResponse, RatingCreate

router = APIRouter()

@router.get("/", response_model=List[RatingResponse])
@router.get("", response_model=List[RatingResponse])
async def list_all_ratings(db: AsyncSession = Depends(get_db)):
    repo = RatingRepository(db)
    return await repo.get_multi(skip=0, limit=100)

@router.get("/donation/{donation_id}", response_model=List[RatingResponse])
async def list_ratings_for_donation(donation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await RatingRepository(db).list_for_donation(donation_id)

@router.post("/", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def create_rating(data: RatingCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = RatingRepository(db)
    r = Rating(**data.model_dump(), user_id=current_user.id, user_name=current_user.full_name)
    created = await repo.create(r)
    await db.commit()
    return created

