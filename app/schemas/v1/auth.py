from typing import Optional, Any
from pydantic import BaseModel, model_validator

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None

class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    email_or_username: Optional[str] = None
    password: str

class FirebaseLoginRequest(BaseModel):
    id_token: Optional[str] = None
    idToken: Optional[str] = None
    token: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_token(cls, data: Any) -> Any:
        if isinstance(data, dict):
            resolved = data.get("id_token") or data.get("idToken") or data.get("token")
            if not resolved:
                raise ValueError("Firebase ID token is required (expected 'id_token', 'idToken', or 'token')")
            data["id_token"] = resolved
        return data

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class FCMTokenRequest(BaseModel):
    fcm_token: str

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

