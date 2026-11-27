import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, require_permission, get_current_super_admin
from app.repositories.user_repo import UserRepository
from app.services.rbac_service import user_to_staff_user
from app.core.security import get_password_hash
from app.models.users import User, Role
from app.schemas.v1.rbac import StaffUser, StaffUserInput, StaffInviteResponse

router = APIRouter()

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
