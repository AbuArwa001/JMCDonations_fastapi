from fastapi import APIRouter
from app.api.v1.endpoints.rbac_overview import router as overview_router
from app.api.v1.endpoints.rbac_roles import router as roles_router
from app.api.v1.endpoints.rbac_users import router as users_router

router = APIRouter()

router.include_router(overview_router)
router.include_router(roles_router)
router.include_router(users_router)
