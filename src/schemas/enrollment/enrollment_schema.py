from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class EnrollmentCreateRequest(BaseModel):
    session_id: Optional[str] = None  

class EnrollmentResponse(BaseModel):
    id: str
    session_id: str
    session_title: str
    session_start_time: datetime
    session_end_time: datetime
    session_location: str
    host_id: str
    host_name: str
    user_id: str
    user_name: str
    enrolled_at: datetime
    status: str  # "enrolled", "cancelled", "completed"

class EnrollmentInDB(BaseModel):
    id: str
    session_id: str
    user_id: str
    enrolled_at: datetime
    status: str

class UserEnrollmentsSummary(BaseModel):
    user_id: str
    user_name: str
    upcoming_sessions: int
    past_sessions: int
    cancelled_sessions: int
    total_sessions: int

class SessionEnrolleesResponse(BaseModel):
    session_id: str
    session_title: str
    capacity: int
    enrolled_count: int
    available_spots: int
    enrollees: list  # List of user info