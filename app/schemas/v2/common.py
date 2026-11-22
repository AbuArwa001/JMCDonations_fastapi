from typing import Generic, TypeVar, Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    meta: Dict[str, Any] = Field(default_factory=lambda: {"version": "v2", "timestamp": datetime.now(timezone.utc).isoformat()})

class PaginatedAPIResponse(BaseModel, Generic[T]):
    success: bool = True
    items: List[T]
    pagination: PaginationMeta
    meta: Dict[str, Any] = Field(default_factory=lambda: {"version": "v2", "timestamp": datetime.now(timezone.utc).isoformat()})

