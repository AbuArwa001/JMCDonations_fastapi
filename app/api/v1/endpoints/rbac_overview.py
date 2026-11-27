from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.deps import get_db, require_permission, get_current_user, get_user_permissions
from app.core.permissions import PERMISSIONS, WILDCARD
from app.models.users import User, Role
from app.schemas.v1.rbac import PermissionResponse

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
