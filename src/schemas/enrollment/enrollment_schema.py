from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class EnrollmentInDB(BaseModel):
    id: str
    user_id: str
    session_id: str
    enrolled_at: datetime
    status: str

class EnrollmentResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    enrolled_at: datetime
    status: str
