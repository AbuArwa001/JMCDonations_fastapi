from fastapi import APIRouter
from app.api.v1 import auth, users, donations, transactions

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(donations.router, prefix="/donations", tags=["donations"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
