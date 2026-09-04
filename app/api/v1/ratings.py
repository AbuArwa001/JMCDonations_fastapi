import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.ratings import Rating
from app.models.donations import Donation
from app.models.users import User
from app.schemas.ratings import RatingCreate, RatingUpdate, RatingResponse
from app.api.dependencies.auth import get_current_active_user

router = APIRouter()

@router.get("/", response_model=List[RatingResponse])
async def list_ratings(
    donation_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    List ratings, optionally filtered by donation_id.
    """
    query = select(Rating)
    if donation_id:
        query = query.filter(Rating.donation_id == donation_id)
    query = query.order_by(Rating.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_rating(
    rating_in: RatingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit or update a rating for a donation drive.
    """
    # Check if donation exists
    d_res = await db.execute(select(Donation).filter(Donation.id == rating_in.donation_id, Donation.is_deleted == False))
    if not d_res.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    # Check if user already rated this donation
    existing_res = await db.execute(
        select(Rating).filter(
            Rating.user_id == current_user.id,
            Rating.donation_id == rating_in.donation_id
        )
    )
    existing_rating = existing_res.scalars().first()

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if existing_rating:
        existing_rating.rating = rating_in.rating
        existing_rating.comment = rating_in.comment
        existing_rating.updated_at = now_utc
        await db.commit()
        await db.refresh(existing_rating)
        return existing_rating

    new_rating = Rating(
        user_id=current_user.id,
        donation_id=rating_in.donation_id,
        rating=rating_in.rating,
        comment=rating_in.comment,
        created_at=now_utc,
        updated_at=now_utc
    )
    db.add(new_rating)
    await db.commit()
    await db.refresh(new_rating)
    return new_rating

@router.get("/{rating_id}", response_model=RatingResponse)
async def get_rating(rating_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rating).filter(Rating.id == rating_id))
    rating = result.scalars().first()
    if not rating:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found")
    return rating

@router.delete("/{rating_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rating(
    rating_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Rating).filter(Rating.id == rating_id))
    rating = result.scalars().first()
    if not rating:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found")

    # Only author or admin can delete
    if not current_user.is_admin and rating.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this rating")

    await db.delete(rating)
    await db.commit()
