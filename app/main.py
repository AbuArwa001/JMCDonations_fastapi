import asyncio, logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.exceptions import register_exception_handlers
from app.services.rbac_service import ensure_default_roles
from app.api.v1.router import router as api_v1_router
from app.api.v2.router import router as api_v2_router
from app.api.v1.endpoints.mpesa import mpesa_callback
from app.workers.pending_cleanup import pending_cleanup_loop
from app.workers.auto_close import expired_donations_loop
import app.models  # noqa

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.warning(f"Database schema auto-creation skipped or connection error: {e}")

    try:
        async with AsyncSessionLocal() as session:
            await ensure_default_roles(session)
    except Exception as e:
        logger.warning(f"RBAC role seeding skipped: {e}")

    cleanup_task = asyncio.create_task(pending_cleanup_loop())
    auto_close_task = asyncio.create_task(expired_donations_loop())
    yield
    cleanup_task.cancel()
    auto_close_task.cancel()
    try:
        await asyncio.gather(cleanup_task, auto_close_task, return_exceptions=True)
    except Exception:
        pass

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json", description="FastAPI Architecture with V1 & V2 versioning", lifespan=lifespan)
register_exception_handlers(app)
app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.CORS_ALLOWED_ORIGIN:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.CORS_ALLOWED_ORIGIN.split(",") if origin.strip()],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$|^https://.*\.vercel\.app$",
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

app.include_router(api_v1_router, prefix=settings.API_V1_STR)
app.include_router(api_v2_router, prefix=settings.API_V2_STR)

for p in ["static/avatars", "static/donations", "FRIDAY_BULETIN"]:
    Path(p).mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/static/bulletins", StaticFiles(directory="FRIDAY_BULETIN"), name="static_bulletins")

@app.get("/", tags=["root"])
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API", "versions": {"v1": settings.API_V1_STR, "v2": settings.API_V2_STR}}

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}

app.add_api_route("/mpesa/callback", mpesa_callback, methods=["POST"], tags=["mpesa"])
app.add_api_route("/mpesa/callback/", mpesa_callback, methods=["POST"], tags=["mpesa"])
