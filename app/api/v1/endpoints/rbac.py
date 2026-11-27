import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.deps import get_db, require_permission, get_current_super_admin, get_current_user, get_user_permissions
from app.repositories.rbac_repo import RBACRepository
from app.services.rbac_service import RBACService
from app.core.permissions import PERMISSIONS, sanitize_permissions, WILDCARD
from app.models.users import User, Role
from app.schemas.v1.rbac import RoleResponse, RoleCreate, RoleUpdate, PermissionResponse, AssignRoleRequest
from app.schemas.v1.users import UserResponse
from app.services.user_service import get_user_response

router = APIRouter()

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
                "color": role.color,
                "is_system": role.is_system,
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
async def list_roles(current_user=Depends(require_permission("roles.manage")), db: AsyncSession = Depends(get_db)):
    repo = RBACRepository(db)
    rows = await repo.list_roles_with_counts()
    return [RoleResponse(id=r.id, role_name=r.role_name, description=r.description, permissions=r.permissions or [], color=r.color, is_system=r.is_system, users_count=c, created_at=r.created_at, updated_at=r.updated_at) for r, c in rows]

@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(role_in: RoleCreate, current_user=Depends(get_current_super_admin), db: AsyncSession = Depends(get_db)):
    repo = RBACRepository(db)
    if await repo.get_by_name(role_in.role_name):
        raise HTTPException(status_code=400, detail="Role name already exists")
    role = Role(id=uuid.uuid4(), role_name=role_in.role_name, description=role_in.description, permissions=sanitize_permissions(role_in.permissions), color=role_in.color, is_system=False)
    created = await repo.create(role)
    await db.commit()
    return RoleResponse(id=created.id, role_name=created.role_name, description=created.description, permissions=created.permissions, color=created.color, is_system=created.is_system, users_count=0, created_at=created.created_at, updated_at=created.updated_at)

@router.put("/roles/{id}", response_model=RoleResponse)
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
    return RoleResponse(id=role.id, role_name=role.role_name, description=role.description, permissions=role.permissions, color=role.color, is_system=role.is_system, users_count=cnt, created_at=role.created_at, updated_at=role.updated_at)

@router.post("/users/{user_id}/role", response_model=UserResponse)
async def assign_role_to_user(user_id: uuid.UUID, req: AssignRoleRequest, current_user=Depends(get_current_super_admin), db: AsyncSession = Depends(get_db)):
    user = await RBACService(db).assign_user_role(user_id, req.role_id)
    return await get_user_response(db, user)

