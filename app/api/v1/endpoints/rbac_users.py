import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, require_permission, get_current_super_admin
from app.repositories.user_repo import UserRepository
from app.services.rbac_service import RBACService
from app.services.user_service import get_user_response
from app.core.security import get_password_hash
from app.models.users import User, Role
from app.schemas.v1.rbac import (
    RoleSummary, StaffUser, StaffUserInput, StaffUserUpdateInput,
    StaffInviteResponse, AssignRoleRequest
)
from app.schemas.v1.users import UserResponse

router = APIRouter()

def user_to_staff_user(user: User) -> StaffUser:
    is_super = bool(user.is_admin and (not user.role_id or (user.role and "*" in (user.role.permissions or []))))
    role_summary = None
    if user.role:
        role_summary = RoleSummary(
            id=user.role.id,
            role_name=user.role.role_name,
            description=user.role.description,
            color=user.role.color or "#10b981",
            is_system=bool(user.role.is_system),
        )
    return StaffUser(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name or user.username,
        phone_number=user.phone_number,
        profile_image_url=user.profile_image_url,
        is_active=user.is_active,
        is_admin=user.is_admin,
        is_super_admin=is_super,
        role=role_summary,
        ss_login=user.ss_login,
        firebase_uid=user.firebase_uid,
    )

@router.get("/users", response_model=List[StaffUser])
@router.get("/users/", response_model=List[StaffUser])
async def list_staff_users(
    scope: str = Query("staff"),
    search: Optional[str] = Query(None),
    role_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(require_permission("users.manage", "roles.manage")),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).options(selectinload(User.role))
    if scope == "staff":
        stmt = stmt.where(User.is_admin.is_(True))
    if role_id:
        stmt = stmt.where(User.role_id == role_id)
    if search:
        s = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(User.email).like(s) | func.lower(User.username).like(s) |
            func.lower(User.full_name).like(s) | func.lower(User.phone_number).like(s)
        )
    users = list((await db.execute(stmt.order_by(User.full_name.asc()))).scalars().all())
    return [user_to_staff_user(u) for u in users]

@router.post("/users", response_model=StaffInviteResponse, status_code=status.HTTP_201_CREATED)
@router.post("/users/", response_model=StaffInviteResponse, status_code=status.HTTP_201_CREATED)
async def create_or_invite_staff_user(
    data: StaffUserInput,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    repo = UserRepository(db)
    user = await repo.get_by_email(data.email)
    created = False
    if not user:
        created = True
        username = data.email.split("@")[0]
        existing_u = (await db.execute(select(User).where(User.username == username))).scalars().first()
        if existing_u:
            username = f"{username}_{uuid.uuid4().hex[:4]}"
        pwd = data.password or uuid.uuid4().hex[:12]
        user = User(
            email=data.email, username=username, full_name=data.full_name,
            phone_number=data.phone_number, hashed_password=get_password_hash(pwd),
            is_active=True, is_admin=True, role_id=data.role_id
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.is_admin = True
        if data.role_id:
            user.role_id = data.role_id
        if data.full_name:
            user.full_name = data.full_name
        if data.phone_number:
            user.phone_number = data.phone_number
        await db.commit()
        await db.refresh(user)

    if user.role_id:
        user.role = await db.get(Role, user.role_id)

    return StaffInviteResponse(user=user_to_staff_user(user), created=created, firebase_synced=bool(user.firebase_uid), password_reset_link=None)

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
