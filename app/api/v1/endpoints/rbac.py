import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission, get_current_super_admin
from app.repositories.rbac_repo import RBACRepository
from app.services.rbac_service import RBACService
from app.core.permissions import PERMISSIONS, sanitize_permissions
from app.models.users import Role
from app.schemas.v1.rbac import RoleResponse, RoleCreate, RoleUpdate, PermissionResponse, AssignRoleRequest
from app.schemas.v1.users import UserResponse
from app.services.user_service import get_user_response

router = APIRouter()

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

