import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission, get_current_super_admin
from app.repositories.rbac_repo import RBACRepository
from app.core.permissions import sanitize_permissions
from app.models.users import Role
from app.schemas.v1.rbac import RoleResponse, RoleCreate, RoleUpdate

router = APIRouter()

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
