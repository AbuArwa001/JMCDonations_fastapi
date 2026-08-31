from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.users import User
from app.schemas.users import UserCreate, UserResponse, Token
import uuid

router = APIRouter()

# Note: Password hashing should use passlib, this is a placeholder
def get_password_hash(password: str) -> str:
    return password + "notreallyhashed"

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    db_user = User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Standard OAuth2PasswordRequestForm is usually used, using JSON for simplicity
    result = await db.execute(select(User).filter(User.email == user_in.email))
    user = result.scalars().first()
    if not user or user.hashed_password != get_password_hash(user_in.password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    return {"access_token": str(user.id), "token_type": "bearer"}
