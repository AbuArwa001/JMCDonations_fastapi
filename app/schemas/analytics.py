import uuid
from typing import List, Optional
from pydantic import BaseModel

class DonationTrendItem(BaseModel):
    name: str
    amount: float

class DashboardSummaryResponse(BaseModel):
    total_collected: float
    total_collected_week: float
    total_collected_month: float
    active_drives: int
    donation_trends: List[DonationTrendItem]

class CategoryBreakdownResponse(BaseModel):
    category_name: str
    total_amount: float
    color: str

class DriveProgressResponse(BaseModel):
    donation: str
    total_collected: float
    unique_donors: int
    target: float

class PendingCashResponse(BaseModel):
    id: uuid.UUID
    amount: float
    donation: str
