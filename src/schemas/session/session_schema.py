from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class SessionCreateRequest(BaseModel):
    title: str
    description: str
    skill_category: str
    location: str
    start_time: datetime
    end_time: datetime
    capacity: int
    price: float #only needed for materials (operating on free model)

class SessionCreateResponse(SessionCreateRequest):
    id: str
    host_id: str
    enrolled_count: int
    status: str         # "active", "cancelled", "completed"
    created_at: datetime


class SessionInDB(SessionCreate):
    id: str
    host_id: str
    enrolled_count: int
    status: str
    created_at: datetime
