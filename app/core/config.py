from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices

class Settings(BaseSettings):
    PROJECT_NAME: str = "JMCDonations FastAPI"
    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"

    SECRET_KEY: str = Field(default="django-insecure-default-key-for-local-dev-only-do-not-use-in-prod", alias="DJANGO_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_HOSTS: str = "*"
    CORS_ALLOWED_ORIGIN: str = "*"
    ADMIN_DASHBOARD_URL: str = "http://localhost:3000"

    DATABASE_URL: str = "sqlite+aiosqlite:///./db.sqlite3"
    SYNC_DATABASE_URL: str = "sqlite:///./db.sqlite3"

    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_API_URL: str = Field(default="https://sandbox.safaricom.co.ke", validation_alias=AliasChoices("MPESA_API_URL", "MPESA_BASE_URL"))
    MPESA_PASSKEY: str = ""
    MPESA_SHORTCODE: str = ""
    MPESA_CALLBACK_URL: str = "https://donations-api.jamiamosque.co.ke/api/v1/mpesa/callback/"

    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_SECRET: str = ""
    PAYPAL_MODE: str = "sandbox"
    PAYPAL_WEBHOOK_ID: str = ""
    PAYPAL_CALLBACK_URL: str = "https://donations-api.jamiamosque.co.ke/api/v1/transactions/paypal_callback/"
    FLUTTERWAVE_PUBLIC_KEY: str = ""

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_REGION_NAME: str = "us-east-1"
    AWS_STORAGE_BUCKET_NAME: str = "jmcdonations"

    FIREBASE_API_KEY: str = ""
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
