import math, uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_pagination, get_current_active_user, require_permission, get_user_permissions
from app.repositories.user_repo import UserRepository
from app.repositories.rbac_repo import RBACRepository
from app.schemas.common import PaginationParams
from app.schemas.v2.common import PaginatedAPIResponse, PaginationMeta, APIResponse
from app.schemas.v2.users import UserV2Response, UserRoleV2
from app.models.users import User

router = APIRouter()

async def _build_v2_user(db: AsyncSession, u: User) -> UserV2Response:
    perms = list(await get_user_permissions(db, u))
    role_obj = await RBACRepository(db).get_by_id(u.role_id) if u.role_id else None
    role_info = UserRoleV2(id=role_obj.id if role_obj else None, role_name=role_obj.role_name if role_obj else ("Admin" if u.is_admin else "Donor"), permissions=perms)
    return UserV2Response(
        id=u.id, email=u.email, username=u.username, full_name=u.full_name,
        phone_number=u.phone_number, is_active=u.is_active, is_admin=u.is_admin,
        profile_image_url=u.profile_image_url, role=role_info, created_at=getattr(u, "created_at", None)
    )

@router.get("/me", response_model=APIResponse[UserV2Response])
async def get_my_profile_v2(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    data = await _build_v2_user(db, current_user)
    return APIResponse(data=data)

@router.get("", response_model=PaginatedAPIResponse[UserV2Response])
@router.get("/", response_model=PaginatedAPIResponse[UserV2Response])
async def list_users_v2(
    search: Optional[str] = None, is_active: Optional[bool] = None,
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db)
):
    repo = UserRepository(db)
    items, total = await repo.search(skip=pagination.skip, limit=pagination.limit, q=search, is_active=is_active)
    v2_items = [await _build_v2_user(db, u) for u in items]
    pages = math.ceil(total / pagination.page_size) if total > 0 else 1
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total_items=total, total_pages=pages, has_next=pagination.page < pages, has_prev=pagination.page > 1)
    return PaginatedAPIResponse(items=v2_items, pagination=meta)
