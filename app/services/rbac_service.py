import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.rbac_repo import RBACRepository
from app.repositories.user_repo import UserRepository
from app.core.permissions import DEFAULT_ROLES
from app.models.users import Role, User
from app.schemas.v1.rbac import StaffUser, RoleSummary

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

class RBACService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RBACRepository(db)
        self.user_repo = UserRepository(db)

    async def ensure_default_roles(self) -> None:
        for r_data in DEFAULT_ROLES:
            existing = await self.repo.get_by_name(r_data["role_name"])
            if not existing:
                new_role = Role(
                    id=uuid.uuid4(),
                    role_name=r_data["role_name"],
                    description=r_data["description"],
                    permissions=r_data["permissions"],
                    color=r_data["color"],
                    is_system=r_data.get("is_system", False),
                )
                await self.repo.create(new_role)
            else:
                if not existing.color and r_data.get("color"):
                    existing.color = r_data["color"]
                if not existing.description and r_data.get("description"):
                    existing.description = r_data["description"]
                if (not existing.permissions or existing.permissions == []) and r_data.get("permissions"):
                    existing.permissions = r_data["permissions"]
                if r_data.get("is_system") is not None:
                    existing.is_system = r_data["is_system"]
        await self.db.commit()

    async def assign_user_role(self, user_id: uuid.UUID, role_id: Optional[uuid.UUID]):
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if role_id is not None:
            role = await self.repo.get_by_id(role_id)
            if not role:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        user.role_id = role_id
        await self.db.commit()
        return user

async def ensure_default_roles(db: AsyncSession) -> None:
    service = RBACService(db)
    await service.ensure_default_roles()
