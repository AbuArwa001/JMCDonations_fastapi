from typing import List, Dict, Any
from pydantic import BaseModel

class MetricTrend(BaseModel):
    current: float
    previous: float
    percentage_change: float

class AnalyticsV2Response(BaseModel):
    total_revenue: MetricTrend
    active_campaigns_count: int
    total_donors_count: int
    conversion_rate: float
    breakdown_by_category: List[Dict[str, Any]]
    monthly_series: List[Dict[str, Any]]

