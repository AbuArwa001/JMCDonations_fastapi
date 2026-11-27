import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, require_permission, get_current_super_admin, get_current_user, get_user_permissions
from app.repositories.rbac_repo import RBACRepository
from app.repositories.user_repo import UserRepository
from app.services.rbac_service import RBACService
from app.core.permissions import PERMISSIONS, sanitize_permissions, WILDCARD
from app.core.security import get_password_hash
from app.models.users import User, Role
from app.schemas.v1.rbac import (
    RoleResponse, RoleCreate, RoleUpdate, PermissionResponse, AssignRoleRequest,
    RoleSummary, StaffUser, StaffUserInput, StaffUserUpdateInput, StaffInviteResponse
)
from app.schemas.v1.users import UserResponse
from app.services.user_service import get_user_response

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

@router.get("/me")
async def get_my_rbac_access(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    granted = await get_user_permissions(db, current_user)
    role = await db.get(Role, current_user.role_id) if current_user.role_id else None
    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name or current_user.username,
            "phone_number": current_user.phone_number,
            "is_admin": current_user.is_admin,
            "is_staff": current_user.is_admin,
            "is_active": current_user.is_active,
            "role": {
                "id": str(role.id),
                "role_name": role.role_name,
                "color": role.color or "#10b981",
                "is_system": bool(role.is_system),
            } if role else None,
        },
        "permissions": list(granted),
        "is_super_admin": (WILDCARD in granted) or current_user.is_admin,
    }

@router.get("/stats")
async def get_rbac_stats(current_user=Depends(require_permission("roles.manage")), db: AsyncSession = Depends(get_db)):
    total_staff = (await db.execute(select(func.count(User.id)).where(User.is_admin.is_(True)))).scalar_one() or 0
    active_staff = (await db.execute(select(func.count(User.id)).where(User.is_admin.is_(True), User.is_active.is_(True)))).scalar_one() or 0
    super_admins = (await db.execute(select(func.count(User.id)).where(User.is_admin.is_(True), User.role_id.is_(None)))).scalar_one() or 0
    roles = (await db.execute(select(func.count(Role.id)))).scalar_one() or 0
    unassigned = (await db.execute(select(func.count(User.id)).where(User.is_admin.is_(True), User.role_id.is_(None)))).scalar_one() or 0
    return {
        "total_staff": total_staff,
        "active_staff": active_staff,
        "super_admins": super_admins,
        "roles": roles,
        "unassigned": unassigned,
    }

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(current_user=Depends(require_permission("roles.manage"))):
    return [PermissionResponse(**p) for p in PERMISSIONS]

@router.get("/roles", response_model=List[RoleResponse])
@router.get("/roles/", response_model=List[RoleResponse])
async def list_roles(current_user=Depends(require_permission("roles.manage")), db: AsyncSession = Depends(get_db)):
    repo = RBACRepository(db)
    rows = await repo.list_roles_with_counts()
    return [
        RoleResponse(
            id=r.id,
            role_name=r.role_name,
            description=r.description,
            permissions=r.permissions if isinstance(r.permissions, list) else [],
            color=r.color or "#10b981",
            is_system=bool(r.is_system),
            users_count=c,
            user_count=c,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r, c in rows
    ]

@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
@router.post("/roles/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(role_in: RoleCreate, current_user=Depends(get_current_super_admin), db: AsyncSession = Depends(get_db)):
    repo = RBACRepository(db)
    if await repo.get_by_name(role_in.role_name):
        raise HTTPException(status_code=400, detail="Role name already exists")
    role = Role(
        id=uuid.uuid4(),
        role_name=role_in.role_name,
        description=role_in.description,
        permissions=sanitize_permissions(role_in.permissions),
        color=role_in.color or "#10b981",
        is_system=False,
    )
    created = await repo.create(role)
    await db.commit()
    return RoleResponse(
        id=created.id,
        role_name=created.role_name,
        description=created.description,
        permissions=created.permissions if isinstance(created.permissions, list) else [],
        color=created.color or "#10b981",
        is_system=bool(created.is_system),
        users_count=0,
        user_count=0,
        created_at=created.created_at,
        updated_at=created.updated_at,
    )

@router.put("/roles/{id}", response_model=RoleResponse)
@router.put("/roles/{id}/", response_model=RoleResponse)
@router.patch("/roles/{id}", response_model=RoleResponse)
@router.patch("/roles/{id}/", response_model=RoleResponse)
async def update_role(id: uuid.UUID, role_in: RoleUpdate, current_user=Depends(get_current_super_admin), db: AsyncSession = Depends(get_db)):
    repo = RBACRepository(db)
    role = await repo.get_by_id(id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system role")
    if role_in.role_name is not None:
        role.role_name = role_in.role_name
    if role_in.description is not None:
        role.description = role_in.description
    if role_in.permissions is not None:
        role.permissions = sanitize_permissions(role_in.permissions)
    if role_in.color is not None:
        role.color = role_in.color
    await db.commit()
    cnt = await repo.count_users_with_role(role.id)
    return RoleResponse(
        id=role.id,
        role_name=role.role_name,
        description=role.description,
        permissions=role.permissions if isinstance(role.permissions, list) else [],
        color=role.color or "#10b981",
        is_system=bool(role.is_system),
        users_count=cnt,
        user_count=cnt,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )

@router.delete("/roles/{id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/roles/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(id: uuid.UUID, current_user=Depends(get_current_super_admin), db: AsyncSession = Depends(get_db)):
    repo = RBACRepository(db)
    role = await repo.get_by_id(id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system role")
    cnt = await repo.count_users_with_role(role.id)
    if cnt > 0:
        raise HTTPException(status_code=400, detail="Cannot delete role with assigned users")
    await repo.delete(role)
    await db.commit()
    return None

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
            func.lower(User.email).like(s) |
            func.lower(User.username).like(s) |
            func.lower(User.full_name).like(s) |
            func.lower(User.phone_number).like(s)
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
            email=data.email,
            username=username,
            full_name=data.full_name,
            phone_number=data.phone_number,
            hashed_password=get_password_hash(pwd),
            is_active=True,
            is_admin=True,
            role_id=data.role_id
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

    return StaffInviteResponse(
        user=user_to_staff_user(user),
        created=created,
        firebase_synced=bool(user.firebase_uid),
        password_reset_link=None
    )

@router.patch("/users/{user_id}", response_model=StaffUser)
@router.patch("/users/{user_id}/", response_model=StaffUser)
async def update_staff_user(
    user_id: uuid.UUID,
    data: StaffUserUpdateInput,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
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
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
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
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    link = f"https://donations.jamiamosque.co.ke/reset-password?email={user.email}"
    return {"email": user.email, "password_reset_link": link}

@router.post("/users/{user_id}/role", response_model=UserResponse)
async def assign_role_to_user(user_id: uuid.UUID, req: AssignRoleRequest, current_user=Depends(get_current_super_admin), db: AsyncSession = Depends(get_db)):
    user = await RBACService(db).assign_user_role(user_id, req.role_id)
    return await get_user_response(db, user)
