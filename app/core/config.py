from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # API info
    PROJECT_NAME: str = "JMCDonations FastAPI"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "django-insecure-default-key-for-local-dev-only-do-not-use-in-prod"
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./db.sqlite3"
    SYNC_DATABASE_URL: str = "sqlite:///./db.sqlite3"
    
    # M-Pesa
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_API_URL: str = "https://sandbox.safaricom.co.ke"
    MPESA_PASSKEY: str = ""
    MPESA_SHORTCODE: str = ""
    MPESA_CALLBACK_URL: str = "https://diatomaceous-preventively-amber.ngrok-free.dev/api/v1/mpesa/callback/"
    
    # PayPal & Flutterwave
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_MODE: str = "sandbox"
    PAYPAL_WEBHOOK_ID: str = ""
    PAYPAL_CALLBACK_URL: str = "https://diatomaceous-preventively-amber.ngrok-free.dev/api/v1/transactions/paypal_callback/"
    FLUTTERWAVE_PUBLIC_KEY: str = ""
    
    # Firebase
    FIREBASE_API_KEY: str = ""
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""
    
    # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_STORAGE_BUCKET_NAME: str = "jmcdonations"
    AWS_S3_REGION_NAME: str = "us-east-1"
    
    # Celery & Redis
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
