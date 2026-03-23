from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CreateRatingRequest(BaseModel):
    session_id: str
    rating: int = Field(..., ge=1, le=5) 
    comment: Optional[str] = None

class CreateRatingResponse(BaseModel):
    id: str
    session_id: str
    session_title: str
    session_date: datetime  # ← Changed from date to datetime
    host_id: str
    host_name: str
    reviewer_id: str
    reviewer_name: str
    rating: int
    comment: Optional[str] = ""
    created_at: datetime

class SessionRatingsResponse(BaseModel):
    session_id: str
    session_title: str
    average_rating: float
    total_ratings: int
    ratings: list[CreateRatingResponse]

class HostRatingSummary(BaseModel):
    host_id: str
    host_name: str
    average_rating: float
    total_ratings: int
    ratings_breakdown: dict