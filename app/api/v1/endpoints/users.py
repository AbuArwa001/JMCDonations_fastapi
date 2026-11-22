import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_admin_user, require_permission
from app.repositories.user_repo import UserRepository
from app.services.user_service import get_user_response
from app.models.users import User
from app.schemas.v1.users import UserResponse, UserCreate, UserUpdate
from app.core.security import get_password_hash

router = APIRouter()

@router.get("", response_model=List[UserResponse])
@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None, is_active: Optional[bool] = None,
    current_user: User = Depends(require_permission("users.manage", "dashboard.view")),
    db: AsyncSession = Depends(get_db)
):
    repo = UserRepository(db)
    users, _ = await repo.search(skip=skip, limit=limit, q=search, is_active=is_active)
    return [await get_user_response(db, u) for u in users]

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_staff_user(
    user_in: UserCreate, is_admin: bool = False,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db)
):
    repo = UserRepository(db)
    if await repo.get_by_email(user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=user_in.email, username=user_in.username, full_name=user_in.full_name,
        phone_number=user_in.phone_number, hashed_password=get_password_hash(user_in.password),
        is_active=True, is_admin=is_admin
    )
    created = await repo.create(user)
    await db.commit()
    return await get_user_response(db, created)

@router.get("/{id}", response_model=UserResponse)
async def get_user_by_id(id: uuid.UUID, current_user: User = Depends(get_current_admin_user), db: AsyncSession = Depends(get_db)):
    user = await UserRepository(db).get_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await get_user_response(db, user)

@router.patch("/{id}/status", response_model=UserResponse)
async def toggle_user_status(id: uuid.UUID, is_active: bool, current_user: User = Depends(require_permission("users.manage")), db: AsyncSession = Depends(get_db)):
    user = await UserRepository(db).get_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = is_active
    await db.commit()
    return await get_user_response(db, user)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(id: uuid.UUID, current_user: User = Depends(require_permission("users.manage")), db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await repo.delete(user)
    await db.commit()
