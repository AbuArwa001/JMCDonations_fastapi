from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timezone
import uuid

from app.db.session import get_db
from app.models.users import User, UserPaymentAccount
from app.schemas.users import (
    UserResponse, UserUpdate,
    UserPaymentAccountCreate, UserPaymentAccountUpdate, UserPaymentAccountResponse
)
from app.api.dependencies.auth import get_current_active_user, get_current_admin_user

router = APIRouter()

# ==================== User Profile ====================

@router.get("/me", response_model=UserResponse)
async def read_user_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current logged in user details.
    """
    return current_user

@router.patch("/me", response_model=UserResponse)
@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update profile details of current user.
    """
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
        
    await db.commit()
    await db.refresh(current_user)
    return current_user

# ==================== User Payment Accounts ====================

@router.get("/payment-accounts", response_model=List[UserPaymentAccountResponse])
async def list_my_payment_accounts(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all payment accounts belonging to the authenticated user.
    """
    result = await db.execute(
        select(UserPaymentAccount)
        .filter(UserPaymentAccount.user_id == current_user.id)
        .order_by(UserPaymentAccount.created_at.desc())
    )
    return result.scalars().all()

@router.post("/payment-accounts", response_model=UserPaymentAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_account(
    acc_in: UserPaymentAccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new payment account (M-Pesa, Card, Bank) for current user.
    """
    db_acc = UserPaymentAccount(
        **acc_in.model_dump(),
        user_id=current_user.id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(db_acc)
    await db.commit()
    await db.refresh(db_acc)
    return db_acc

@router.get("/payment-accounts/{account_id}", response_model=UserPaymentAccountResponse)
async def get_payment_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserPaymentAccount).filter(
            UserPaymentAccount.id == account_id,
            UserPaymentAccount.user_id == current_user.id
        )
    )
    acc = result.scalars().first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment account not found")
    return acc

@router.patch("/payment-accounts/{account_id}", response_model=UserPaymentAccountResponse)
@router.put("/payment-accounts/{account_id}", response_model=UserPaymentAccountResponse)
async def update_payment_account(
    account_id: uuid.UUID,
    acc_in: UserPaymentAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserPaymentAccount).filter(
            UserPaymentAccount.id == account_id,
            UserPaymentAccount.user_id == current_user.id
        )
    )
    acc = result.scalars().first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment account not found")

    update_data = acc_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(acc, field, value)

    acc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(acc)
    return acc

@router.delete("/payment-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserPaymentAccount).filter(
            UserPaymentAccount.id == account_id,
            UserPaymentAccount.user_id == current_user.id
        )
    )
    acc = result.scalars().first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment account not found")

    await db.delete(acc)
    await db.commit()

# ==================== User Management (Admin / Detail) ====================

@router.get("/", response_model=List[UserResponse])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    List all users (Admin only).
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve user by UUID.
    """
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this user"
        )
        
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete a user account (Admin only).
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()
