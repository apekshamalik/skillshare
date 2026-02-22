from fastapi import FastAPI, HTTPException, APIRouter, Depends, status
from bson import ObjectId
from datetime import date, datetime
from src.schemas.ratings.ratings_schema import CreateRatingRequest, CreateRatingResponse, SessionRatingsResponse
from src.schemas.user.user_schema import UserInDB
from src.database.database import get_ratings_collection, get_sessions_collection, get_users_collection
from src.auth.dependencies import get_current_user

router = APIRouter()

@router.post("/create-rating", response_model=CreateRatingResponse, status_code=status.HTTP_201_CREATED)
async def create_rating(rating: CreateRatingRequest, current_user: UserInDB = Depends(get_current_user)):

    sessions_collection = get_sessions_collection()
    users_collection = get_users_collection()
    
    try:
        session = await sessions_collection.find_one({"_id": ObjectId(rating.session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session id")

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["host_id"] == current_user.id:
        raise HTTPException(status_code=400, detail="Host cannot self-rate")

    if session["end_time"] > datetime.now():
        raise HTTPException(status_code=400, detail="Cannot rate a session that has not ended yet")

    if session["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot rate a cancelled session")
    
    #TODO: Check if user was enrolled
    # If not enrolled, cannot rate

    existing_rating = await get_ratings_collection().find_one({
        "session_id": ObjectId(rating.session_id),
        "rater_id": ObjectId(current_user.id)
    })

    if existing_rating:
        raise HTTPException(status_code=400, detail="User has already rated this session")

    host = await users_collection.find_one({"_id": ObjectId(session["host_id"])})
    if not host:
        raise HTTPException(status_code=404, detail="Host user not found")
    
    host_name = f"{host['first_name']} {host['last_name']}"

    rating_doc = {
        "session_id": ObjectId(rating.session_id),
        "session_title": session["title"],
        "session_date": session["date"],
        "rater_id": ObjectId(current_user.id),
        "host_id": ObjectId(session["host_id"]),
        "host_name": host_name,
        "reviewer_id": ObjectId(current_user.id),
        "reviewer_name": f"{current_user.first_name} {current_user.last_name}",
        "rating": rating.rating,
        "comment": rating.comment,
        "created_at": datetime.now()
    }

    result = await get_ratings_collection().insert_one(rating_doc)
    rating_doc["_id"] = result.inserted_id

    return CreateRatingResponse(
        id=str(rating_doc["_id"]),
        session_id=str(rating_doc["session_id"]),
        session_title=rating_doc["session_title"],
        session_date=rating_doc["session_date"],
        host_id=str(rating_doc["host_id"]),
        host_name=rating_doc["host_name"],
        reviewer_id=str(rating_doc["reviewer_id"]),
        reviewer_name=rating_doc["reviewer_name"],
        rating=rating_doc["rating"],
        comment=rating_doc["comment"],
        created_at=rating_doc["created_at"]
    )

@router.get("/session/{session_id}/ratings", response_model=SessionRatingsResponse)
async def get_ratings_for_session(session_id: str):
    
    sessions_collection = get_sessions_collection()
    users_collection = get_users_collection()
    ratings_collection = get_ratings_collection()
    try:
        session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session id")
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    ratings_list = ratings_collection.find({"session_id": ObjectId(session_id)})
    ratings = await ratings_list.to_list(length=None)

    if not ratings:
        return SessionRatingsResponse(
            session_id=session_id,
            session_title=session["title"],
            average_rating=0.0,
            total_ratings=0,
            ratings=[]
        )

    total_rating = sum(r["rating"] for r in ratings)
    average_rating = total_rating / len(ratings)

    ratings_response = [
        CreateRatingResponse(
            id=str(r["_id"]),
            session_id=str(r["session_id"]),
            session_title=r["session_title"],
            session_date=r["session_date"],
            host_id=str(r["host_id"]),
            host_name=r["host_name"],
            reviewer_id=str(r["reviewer_id"]),
            reviewer_name=r["reviewer_name"],
            rating=r["rating"],
            comment=r.get("comment", ""),
            created_at=r["created_at"]
        ) for r in ratings
    ]

    return SessionRatingsResponse(
        session_id=session_id,
        session_title=session["title"],
        average_rating=average_rating,
        total_ratings=len(ratings),
        ratings=ratings_response
        )

