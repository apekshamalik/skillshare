from datetime import date, datetime
from pydantic import BaseModel
from typing import Optional

class SessionCreateRequest(BaseModel):
    title: str
    description: str
    skill_category: str
    location: str
    start_time: datetime
    end_time: datetime
    date: date
    capacity: int
    price: float #only needed for materials (operating on free model)

class SessionCreateResponse(SessionCreateRequest):
    id: str
    host_id: str
    date: date
    enrolled_count: int
    status: str         # "active", "cancelled", "completed"
    created_at: datetime


class SessionInDB(SessionCreateRequest):
    id: str
    host_id: str
    enrolled_count: int
    status: str
    created_at: datetime

class SessionUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    skill_category: Optional[str] = None
    date: Optional[date] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    capacity: Optional[int] = None
    price: Optional[float] = None