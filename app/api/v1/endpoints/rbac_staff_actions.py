import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_super_admin
from app.services.rbac_service import RBACService, user_to_staff_user
from app.services.user_service import get_user_response
from app.models.users import User, Role
from app.schemas.v1.rbac import StaffUser, StaffUserUpdateInput, AssignRoleRequest
from app.schemas.v1.users import UserResponse

router = APIRouter()

@router.patch("/users/{user_id}", response_model=StaffUser)
@router.patch("/users/{user_id}/", response_model=StaffUser)
async def update_staff_user(
    user_id: uuid.UUID, data: StaffUserUpdateInput,
    current_user: User = Depends(get_current_super_admin), db: AsyncSession = Depends(get_db)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone_number is not None:
        user.phone_number = data.phone_number
    if data.clear_role:
        user.role_id = None
        user.role = None
    elif data.role_id is not None:
        user.role_id = data.role_id
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    await db.commit()
    await db.refresh(user)
    if user.role_id:
        user.role = await db.get(Role, user.role_id)
    return user_to_staff_user(user)

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/users/{user_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_staff_access(
    user_id: uuid.UUID, current_user: User = Depends(get_current_super_admin), db: AsyncSession = Depends(get_db)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot revoke your own staff privileges")
    user.is_admin = False
    user.role_id = None
    user.role = None
    await db.commit()
    return None

@router.post("/users/{user_id}/password-reset")
@router.post("/users/{user_id}/password-reset/")
async def generate_password_reset_link(
    user_id: uuid.UUID, current_user: User = Depends(get_current_super_admin), db: AsyncSession = Depends(get_db)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    link = f"https://donations.jamiamosque.co.ke/reset-password?email={user.email}"
    return {"email": user.email, "password_reset_link": link}

@router.post("/users/{user_id}/role", response_model=UserResponse)
@router.post("/users/{user_id}/role/", response_model=UserResponse)
async def assign_role_to_user(
    user_id: uuid.UUID, req: AssignRoleRequest, current_user=Depends(get_current_super_admin), db: AsyncSession = Depends(get_db)
):
    user = await RBACService(db).assign_user_role(user_id, req.role_id)
    return await get_user_response(db, user)
