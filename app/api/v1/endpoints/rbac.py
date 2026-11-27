from fastapi import APIRouter
from app.api.v1.endpoints.rbac_overview import router as overview_router
from app.api.v1.endpoints.rbac_roles import router as roles_router
from app.api.v1.endpoints.rbac_staff import router as staff_router
from app.api.v1.endpoints.rbac_staff_actions import router as staff_actions_router

router = APIRouter()

router.include_router(overview_router)
router.include_router(roles_router)
router.include_router(staff_router)
router.include_router(staff_actions_router)
