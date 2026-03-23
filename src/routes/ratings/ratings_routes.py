from fastapi import HTTPException, APIRouter, Depends, status
from bson import ObjectId
from datetime import datetime, timezone
from typing import List

from src.schemas.ratings.ratings_schema import (
    CreateRatingRequest, 
    CreateRatingResponse, 
    SessionRatingsResponse,
    HostRatingSummary
)
from src.schemas.user.user_schema import UserInDB
from src.database.database import (
    get_enrollments_collection,
    get_ratings_collection,
    get_sessions_collection,
    get_users_collection,
)
from src.auth.dependencies import get_current_user

router = APIRouter()


@router.post("/", response_model=CreateRatingResponse, status_code=status.HTTP_201_CREATED)
async def create_rating(
    rating: CreateRatingRequest, 
    current_user: UserInDB = Depends(get_current_user)
):
    """Create a rating for a session (PROTECTED)"""
    enrollments_collection = get_enrollments_collection()
    ratings_collection = get_ratings_collection()
    sessions_collection = get_sessions_collection()
    users_collection = get_users_collection()
    
    # 1. Check if session exists
    try:
        session = await sessions_collection.find_one({"_id": ObjectId(rating.session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Check if user is the host (can't rate your own session)
    if session["host_id"] == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot rate your own session")

    # 3. Check if session is cancelled
    if session["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot rate a cancelled session")

    # 4. Check if session has ended
    if session["end_time"] > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400, 
            detail="Cannot rate a session that hasn't ended yet"
        )

    # 5. Check if user was enrolled
    enrollment = await enrollments_collection.find_one({
        "session_id": ObjectId(rating.session_id),
        "user_id": ObjectId(current_user.id),
        "status": "enrolled"
    })

    if not enrollment:
        raise HTTPException(
            status_code=403, 
            detail="Must be enrolled to rate this session"
        )

    # 6. Check if user already rated this session
    existing_rating = await ratings_collection.find_one({
        "session_id": ObjectId(rating.session_id),
        "reviewer_id": ObjectId(current_user.id)
    })

    if existing_rating:
        raise HTTPException(
            status_code=400, 
            detail="You already rated this session"
        )

    # 7. Get host information
    host = await users_collection.find_one({"_id": ObjectId(session["host_id"])})
    if not host:
        raise HTTPException(status_code=500, detail="Session host not found")
    
    host_name = f"{host['first_name']} {host['last_name']}"

    # 8. Create rating document
    rating_doc = {
        "session_id": ObjectId(rating.session_id),
        "session_title": session["title"],
        "session_date": session["start_time"].date(),
        "host_id": ObjectId(session["host_id"]),
        "host_name": host_name,
        "reviewer_id": ObjectId(current_user.id),
        "reviewer_name": f"{current_user.first_name} {current_user.last_name}",
        "rating": rating.rating,
        "comment": rating.comment,
        "created_at": datetime.now(timezone.utc)
    }

    result = await ratings_collection.insert_one(rating_doc)
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
        comment=rating_doc.get("comment", ""),
        created_at=rating_doc["created_at"]
    )


@router.get("/sessions/{session_id}/ratings", response_model=SessionRatingsResponse)
async def get_session_ratings(session_id: str):
    """Get all ratings for a specific session (PUBLIC)"""
    sessions_collection = get_sessions_collection()
    ratings_collection = get_ratings_collection()
    
    # Check session exists
    try:
        session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all ratings for this session
    cursor = ratings_collection.find({"session_id": ObjectId(session_id)})
    ratings_list = await cursor.to_list(length=None)

    if not ratings_list:
        return SessionRatingsResponse(
            session_id=session_id,
            session_title=session["title"],
            average_rating=0.0,
            total_ratings=0,
            ratings=[]
        )

    # Calculate average
    total_rating = sum(r["rating"] for r in ratings_list)
    average_rating = total_rating / len(ratings_list)

    # Convert to response models
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
        )
        for r in ratings_list
    ]

    return SessionRatingsResponse(
        session_id=session_id,
        session_title=session["title"],
        average_rating=round(average_rating, 2),
        total_ratings=len(ratings_list),
        ratings=ratings_response
    )


@router.get("/hosts/{host_id}/summary", response_model=HostRatingSummary)
async def get_host_rating_summary(host_id: str):
    """Get rating summary for a host/instructor (PUBLIC)"""
    ratings_collection = get_ratings_collection()
    users_collection = get_users_collection()
    
    # Check host exists
    try:
        host = await users_collection.find_one({"_id": ObjectId(host_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid host ID format")
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    host_name = f"{host['first_name']} {host['last_name']}"
    
    # Aggregate ratings for this host
    pipeline = [
        {"$match": {"host_id": ObjectId(host_id)}},
        {"$group": {
            "_id": None,
            "average_rating": {"$avg": "$rating"},
            "total_ratings": {"$sum": 1},
            "ratings": {"$push": "$rating"}
        }}
    ]
    
    result = await ratings_collection.aggregate(pipeline).to_list(1)
    
    if not result:
        return HostRatingSummary(
            host_id=host_id,
            host_name=host_name,
            average_rating=0.0,
            total_ratings=0,
            ratings_breakdown={5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        )
    
    # Calculate breakdown (how many 5-star, 4-star, etc.)
    ratings_list = result[0]["ratings"]
    breakdown = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in ratings_list:
        breakdown[r] += 1
    
    return HostRatingSummary(
        host_id=host_id,
        host_name=host_name,
        average_rating=round(result[0]["average_rating"], 2),
        total_ratings=result[0]["total_ratings"],
        ratings_breakdown=breakdown
    )


@router.get("/my-ratings", response_model=List[CreateRatingResponse])
async def get_my_ratings(current_user: UserInDB = Depends(get_current_user)):
    """Get all ratings I've written (PROTECTED)"""
    ratings_collection = get_ratings_collection()
    
    cursor = ratings_collection.find({"reviewer_id": ObjectId(current_user.id)})
    ratings_list = await cursor.to_list(length=None)
    
    return [
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
        )
        for r in ratings_list
    ]


@router.get("/my-received-ratings", response_model=List[CreateRatingResponse])
async def get_my_received_ratings(current_user: UserInDB = Depends(get_current_user)):
    """Get all ratings I've received as a host (PROTECTED)"""
    ratings_collection = get_ratings_collection()
    
    cursor = ratings_collection.find({"host_id": ObjectId(current_user.id)})
    ratings_list = await cursor.to_list(length=None)
    
    return [
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
        )
        for r in ratings_list
    ]