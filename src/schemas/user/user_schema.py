from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Dict

class UserCreateRequest(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    password: str
    bio: Optional[str] = ""

class UserCreateResponse(BaseModel):
    id: str             
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    bio: Optional[str] = ""
    date_joined: datetime

class UserInDB(BaseModel):
    id: str
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    bio: Optional[str] 
    date_joined: datetime
