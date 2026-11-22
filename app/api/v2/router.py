from fastapi import APIRouter
from app.api.v2.endpoints import health, donations, users, transactions, analytics

router = APIRouter()

router.include_router(health.router, tags=["v2-health"])
router.include_router(donations.router, prefix="/donations", tags=["v2-donations"])
router.include_router(users.router, prefix="/users", tags=["v2-users"])
router.include_router(transactions.router, prefix="/transactions", tags=["v2-transactions"])
router.include_router(analytics.router, prefix="/analytics", tags=["v2-analytics"])

