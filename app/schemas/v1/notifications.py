from typing import List
from pydantic import BaseModel

class NotificationStateResponse(BaseModel):
    deleted_ids: List[str] = []
    read_ids: List[str] = []

class NotificationStateUpdate(BaseModel):
    notification_ids: List[str]

class NotificationSyncRequest(BaseModel):
    deleted_ids: List[str] = []
    read_ids: List[str] = []

