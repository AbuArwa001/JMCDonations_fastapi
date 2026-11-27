from fastapi import APIRouter
from app.api.v1.endpoints.bulletin_notify import router as notify_router
from app.api.v1.endpoints.bulletin_crud import router as crud_router

router = APIRouter()
router.include_router(notify_router)
router.include_router(crud_router)
