from fastapi import FastAPI, HTTPException
from argon2 import PasswordHasher
from src.utils.id import generate_objectid
from datetime import datetime, timezone
from typing import Dict
from src.schemas.user.user_schema import UserCreateRequest, UserCreateResponse, UserInDB

ph = PasswordHasher()

router = APIRouter()

users: Dict[str, 'UserInDB'] = {}

@router.post("/register", response_model = UserCreateResponse)
def register_user(user: UserCreateRequest):
    if any(created_user.username == user.username for created_user in users.values()):
        raise HTTPException(status_code=400, detail="Username already taken")
    if any(created_user.email == user.email for created_user in users.values()):
        raise HTTPException(status_code=400, detail="Email already in use")

    hashed_password = ph.hash(user.password)

    user_id = generate_objectid()
    user_in_db = UserInDB(
        id=user_id, 
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        email=user.email,
        bio=user.bio,
        password=hashed_password,
        date_joined=datetime.now(timezone.utc)
    )

    users[user_id] = user_in_db

    return UserCreateResponse(
        id=user_in_db.id,
        first_name=user_in_db.first_name,
        last_name=user_in_db.last_name,
        username=user_in_db.username,
        email=user_in_db.email,
        bio=user_in_db.bio,
        date_joined=user_in_db.date_joined
    )