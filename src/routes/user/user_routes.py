from fastapi import FastAPI, HTTPException, APIRouter, Depends, status
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from src.utils.id import generate_objectid
from datetime import datetime, timezone, timedelta
from typing import Dict
from src.schemas.user.user_schema import UserCreateRequest, UserCreateResponse, UserInDB, UserUpdateRequest
from src.schemas.auth.auth_schemas import LoginRequest, Token

from src.auth.auth_utils import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from src.auth.dependencies import get_current_user


ph = PasswordHasher()
router = APIRouter()

users: Dict[str, 'UserInDB'] = {}

@router.post("/register", response_model = UserCreateResponse, status_code=status.HTTP_201_CREATED)
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
        password_hash = hashed_password,
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

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest):
        # find the user
    user = next(
        (u for u in users.values() if u.username == login_data.username_or_email or u.email == login_data.username_or_email),
        None
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials")
    
    try:
        ph.verify(user.password_hash, login_data.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserCreateResponse)
async def get_current_user(current_user: UserInDB = Depends(get_current_user)):
    return UserCreateResponse(
        id=current_user.id,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        username=current_user.username,
        email=current_user.email,
        bio=current_user.bio,
        date_joined=current_user.date_joined
    )

@router.get("/{user_id}", response_model=UserCreateResponse)
def get_user(user_id: str):
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserCreateResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        email=user.email,
        bio=user.bio,
        date_joined=user.date_joined
    )


@router.put("/me", response_model=UserCreateResponse)
async def update_current_user(user_update: UserUpdateRequest, current_user: UserInDB = Depends(get_current_user)):
    
    if user_update.first_name is not None:
        current_user.first_name = user_update.first_name
    if user_update.last_name is not None:
        current_user.last_name = user_update.last_name
    if user_update.bio is not None:
        current_user.bio = user_update.bio
    
    users[current_user.id] = current_user
    
    return UserCreateResponse(
        id=current_user.id,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        username=current_user.username,
        email=current_user.email,
        bio=current_user.bio,
        date_joined=current_user.date_joined
    )