from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import Optional

class SessionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Session title")
    description: str = Field(..., min_length=1, max_length=2000, description="Session description")
    skill_category: str = Field(..., min_length=1, max_length=100, description="Skill category")
    location: str = Field(..., min_length=1, max_length=300, description="Session location")
    start_time: datetime
    end_time: datetime
    date: date
    capacity: int = Field(..., ge=1, description="Maximum number of participants (must be at least 1)")
    price: float = Field(..., ge=0.0, description="Price for materials (must be non-negative)")

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