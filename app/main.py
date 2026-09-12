from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router

from contextlib import asynccontextmanager
import asyncio
from app.db.session import engine
from app.models.__init__ import *
from app.db.base import Base
from app.workers.pending_cleanup import pending_cleanup_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create missing database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Start background worker: expire pending transactions > 1 hr
    cleanup_task = asyncio.create_task(pending_cleanup_loop())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Reimplementation of JMCDonations API using FastAPI",
    lifespan=lifespan
)

# Set up CORS
if settings.CORS_ALLOWED_ORIGIN:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.CORS_ALLOWED_ORIGIN.split(",") if origin.strip()],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$|^https://.*\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

from pathlib import Path
from fastapi.staticfiles import StaticFiles

app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount static files directory (avatars, uploads, donation galleries)
static_dir = Path("static")
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "avatars").mkdir(parents=True, exist_ok=True)
(static_dir / "donations").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

friday_bulletin_dir = Path("FRIDAY_BULETIN")
friday_bulletin_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/bulletins", StaticFiles(directory="FRIDAY_BULETIN"), name="static_bulletins")

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Root fallback for M-Pesa callbacks without /api/v1 prefix
from app.api.v1.transactions import mpesa_callback
app.add_api_route("/mpesa/callback", mpesa_callback, methods=["POST"], tags=["mpesa"])
app.add_api_route("/mpesa/callback/", mpesa_callback, methods=["POST"], tags=["mpesa"])

