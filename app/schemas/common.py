from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

T = TypeVar("T")

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int

class MessageResponse(BaseModel):
    message: str
    success: bool = True

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool = False
    detail: str
    error_code: Optional[str] = None

