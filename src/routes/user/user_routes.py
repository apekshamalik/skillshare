from fastapi import FastAPI, HTTPException, APIRouter, Depends, status
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from src.utils.id import generate_objectid
from datetime import datetime, timezone, timedelta
from typing import Dict
from bson import ObjectId
from src.schemas.user.user_schema import UserCreateRequest, UserCreateResponse, UserInDB, UserUpdateRequest
from src.schemas.auth.auth_schemas import LoginRequest, Token

from src.auth.auth_utils import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from src.auth.dependencies import get_current_user
from src.database.database import get_users_collection

ph = PasswordHasher()
router = APIRouter()


@router.post("/register", response_model = UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreateRequest):
    
    users_collection = get_users_collection()

    existing_username = await users_collection.find_one({"username": user.username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    existing_email = await users_collection.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already in use")
    
    hashed_password = ph.hash(user.password)

    user_doc = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "password_hash": hashed_password,
        "bio": user.bio,
        "date_joined": datetime.now(timezone.utc)
    }

    result = await users_collection.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    return UserCreateResponse(
       id = str(user_doc["_id"]),
       first_name = user_doc["first_name"],
       last_name = user_doc["last_name"],
       username = user_doc["username"],
       email = user_doc["email"],
       bio = user_doc["bio"],
       date_joined = user_doc["date_joined"]
    )

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    
    users_collection = get_users_collection()

    user = await users_collection.find_one({"$or": [
            {"username": login_data.username_or_email},
            {"email": login_data.username_or_email}
    ]
    })

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials")
    
    try:
        ph.verify(user["password_hash"], login_data.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserCreateResponse)
async def get_current_user_info(current_user: UserInDB = Depends(get_current_user)):
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
    users_collection = get_users_collection()

    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=404, detail="Invalid user ID format")
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserCreateResponse(
        id=str(user["_id"]),
        first_name=user["first_name"],
        last_name=user["last_name"],
        username=user["username"],
        email=user["email"],
        bio=user.get("bio", ""),
        date_joined=user["date_joined"]
    )


@router.put("/me", response_model=UserCreateResponse)
async def update_current_user(user_update: UserUpdateRequest, current_user: UserInDB = Depends(get_current_user)):
    users_collection = get_users_collection()

    update_doc = {}
    if user_update.first_name is not None:
        update_doc["first_name"] = user_update.first_name
    if user_update.last_name is not None:
        update_doc["last_name"] = user_update.last_name
    if user_update.bio is not None:
        update_doc["bio"] = user_update.bio
    
    if update_doc:
        await users_collection.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": update_doc}
        )

        updated_user = await users_collection.find_ones({"_id": ObjectId(current_user.id)})
    
    return UserCreateResponse(
        id = str(updated_user["_id"]),
        first_name = updated_user["first_name"],
        last_name = updated_user["last_name"],
        username = updated_user["username"],
        email = updated_user["email"],
        bio = updated_user.get("bio", ""),
        date_joined = updated_user["date_joined"]
    )