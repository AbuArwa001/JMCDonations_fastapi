from fastapi import APIRouter
from app.api.v1 import (
    auth, users, donations, transactions, community, zakat,
    categories, duas, quran, prayer_times, events,
    khutba, ratings, core_config, analytics
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(donations.router, prefix="/donations", tags=["donations"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
api_router.include_router(zakat.router, prefix="/zakat", tags=["zakat"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(duas.router, prefix="/duas", tags=["duas"])
api_router.include_router(quran.router, prefix="/quran", tags=["quran"])
api_router.include_router(prayer_times.router, prefix="/prayer-times", tags=["prayer_times"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(khutba.router, prefix="/khutba", tags=["khutba"])
api_router.include_router(ratings.router, prefix="/ratings", tags=["ratings"])
api_router.include_router(core_config.router, prefix="/features", tags=["core_config"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
