from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.api.deps import get_db
from app.core.config import settings
from app.schemas.v2.common import APIResponse

router = APIRouter()

@router.get("/health", response_model=APIResponse[dict], summary="V2 Detailed Health Check")
async def health_check_v2(db: AsyncSession = Depends(get_db)):
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {e}"

    data = {
        "status": "ok" if db_status == "healthy" else "degraded",
        "service": settings.PROJECT_NAME,
        "environment": "production",
        "components": {
            "database": db_status,
            "api": "healthy"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return APIResponse(data=data, message="System operational")

