from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, auth, users, user_profile, rbac, donations, categories,
    transactions, mpesa, paypal, accounts, transfers,
    community, bulletins, events, khutba, duas, quran,
    prayer_times, zakat, ratings, features, analytics
)

router = APIRouter()

router.include_router(health.router)
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(user_profile.router, prefix="/users", tags=["users"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(rbac.router, prefix="/rbac", tags=["rbac"])
router.include_router(donations.router, prefix="/donations", tags=["donations"])
router.include_router(categories.router, prefix="/categories", tags=["categories"])
router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
router.include_router(mpesa.router, prefix="/mpesa", tags=["transactions"])
router.include_router(mpesa.router, prefix="/transactions/mpesa", tags=["transactions"])
router.include_router(paypal.router, prefix="/paypal", tags=["transactions"])
router.include_router(paypal.router, prefix="/transactions/paypal", tags=["transactions"])
router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
router.include_router(accounts.router, prefix="/bank-accounts", tags=["accounts"])
router.include_router(accounts.router, prefix="/transactions/accounts", tags=["accounts"])
router.include_router(transfers.router, prefix="/transfers", tags=["transfers"])
router.include_router(transfers.router, prefix="/transactions/transfers", tags=["transfers"])
router.include_router(community.router, prefix="/community", tags=["community"])
router.include_router(bulletins.router, prefix="/bulletins", tags=["bulletins"])
router.include_router(events.router, prefix="/events", tags=["events"])
router.include_router(khutba.router, prefix="/khutba", tags=["khutba"])
router.include_router(duas.router, prefix="/duas", tags=["duas"])
router.include_router(quran.router, prefix="/quran", tags=["quran"])
router.include_router(prayer_times.router, prefix="/prayer-times", tags=["prayer_times"])
router.include_router(zakat.router, prefix="/zakat", tags=["zakat"])
router.include_router(ratings.router, prefix="/ratings", tags=["ratings"])
router.include_router(features.router, prefix="/features", tags=["core_config"])
router.include_router(features.router, prefix="/core_config/features", tags=["core_config"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

