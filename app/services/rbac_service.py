import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.rbac_repo import RBACRepository
from app.repositories.user_repo import UserRepository
from app.core.permissions import DEFAULT_ROLES, sanitize_permissions
from app.models.users import Role

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

