from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health", summary="Health Check")
async def health_check():
    return {"status": "ok", "version": "v1", "project": settings.PROJECT_NAME}

@router.get("/ping", summary="Ping")
async def ping():
    return {"ping": "pong"}

