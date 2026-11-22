from typing import Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

class EntityNotFoundException(AppException):
    def __init__(self, entity_name: str, identifier: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

class BadRequestException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, details=details)

class UnauthorizedException(AppException):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)

class ForbiddenException(AppException):
    def __init__(self, message: str = "Operation not permitted"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)

class ConflictException(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT)

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException):
        payload = {"detail": exc.message}
        if exc.details is not None:
            payload["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=payload)

