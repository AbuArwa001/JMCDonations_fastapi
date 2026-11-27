from fastapi import APIRouter
from app.api.v1.endpoints.khutba_device import router as device_router
from app.api.v1.endpoints.khutba_notify import router as notify_router
from app.api.v1.endpoints.khutba_crud import router as crud_router

router = APIRouter()
router.include_router(device_router)
router.include_router(notify_router)
router.include_router(crud_router)
