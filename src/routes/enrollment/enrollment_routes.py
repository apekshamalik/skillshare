from fastapi import APIRouter, HTTPException, Depends, status
from bson import ObjectId
from datetime import datetime, timezone
from typing import List

from src.schemas.enrollment.enrollment_schema import (
    EnrollmentCreateRequest,
    EnrollmentResponse,
    UserEnrollmentsSummary,
    SessionEnrolleesResponse
)
from src.schemas.user.user_schema import UserInDB
from src.auth.dependencies import get_current_user
from src.database.database import (
    get_enrollments_collection,
    get_sessions_collection,
    get_users_collection
)

router = APIRouter()


@router.post("/sessions/{session_id}/enroll", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_in_session(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Session must exist and be active
    Session must not be at capacity
    User cannot enroll in their own session
    User cannot enroll twice in same session
    Session must not have already started
    """
    enrollments_collection = get_enrollments_collection()
    sessions_collection = get_sessions_collection()
    users_collection = get_users_collection()
    
    #Check if session exists
    try:
        session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    #Check if session is active
    if session["status"] != "active":
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot enroll in {session['status']} session"
        )
    
    #Check if session has already started
    if session["start_time"] <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Cannot enroll in a session that has already started"
        )
    
    #Check if user is the host
    if session["host_id"] == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot enroll in your own session"
        )
    
    #Check if session is at capacity
    if session["enrolled_count"] >= session["capacity"]:
        raise HTTPException(
            status_code=400,
            detail="Session is at full capacity"
        )
    
    #Check if user is already enrolled
    existing_enrollment = await enrollments_collection.find_one({
        "session_id": ObjectId(session_id),
        "user_id": ObjectId(current_user.id),
        "status": "enrolled"
    })
    
    if existing_enrollment:
        raise HTTPException(
            status_code=400,
            detail="You are already enrolled in this session"
        )
    
    #Get host information
    host = await users_collection.find_one({"_id": ObjectId(session["host_id"])})
    if not host:
        raise HTTPException(status_code=500, detail="Session host not found")
    
    host_name = f"{host['first_name']} {host['last_name']}"
    
    #Create enrollment
    enrollment_doc = {
        "session_id": ObjectId(session_id),
        "user_id": ObjectId(current_user.id),
        "enrolled_at": datetime.now(timezone.utc),
        "status": "enrolled"
    }
    
    result = await enrollments_collection.insert_one(enrollment_doc)
    enrollment_doc["_id"] = result.inserted_id
    
    await sessions_collection.update_one(
        {"_id": ObjectId(session_id)},
        {"$inc": {"enrolled_count": 1}}
    )
    

    return EnrollmentResponse(
        id=str(enrollment_doc["_id"]),
        session_id=session_id,
        session_title=session["title"],
        session_start_time=session["start_time"],
        session_end_time=session["end_time"],
        session_location=session["location"],
        host_id=session["host_id"],
        host_name=host_name,
        user_id=current_user.id,
        user_name=f"{current_user.first_name} {current_user.last_name}",
        enrolled_at=enrollment_doc["enrolled_at"],
        status=enrollment_doc["status"]
    )


@router.delete("/sessions/{session_id}/enroll", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_enrollment(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    - Must be enrolled in the session
    - Cannot cancel after session has started
    """
    enrollments_collection = get_enrollments_collection()
    sessions_collection = get_sessions_collection()
    

    try:
        session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    

    if session["start_time"] <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel enrollment after session has started"
        )
    

    enrollment = await enrollments_collection.find_one({
        "session_id": ObjectId(session_id),
        "user_id": ObjectId(current_user.id),
        "status": "enrolled"
    })
    
    if not enrollment:
        raise HTTPException(
            status_code=404,
            detail="You are not enrolled in this session"
        )
    
    await enrollments_collection.update_one(
        {"_id": enrollment["_id"]},
        {"$set": {"status": "cancelled"}}
    )
    
    await sessions_collection.update_one(
        {"_id": ObjectId(session_id)},
        {"$inc": {"enrolled_count": -1}}
    )
    
    return


@router.get("/sessions/{session_id}/enrollees", response_model=SessionEnrolleesResponse)
async def get_session_enrollees(session_id: str):
    """
    Get list of users enrolled in a session (PUBLIC)
    """
    enrollments_collection = get_enrollments_collection()
    sessions_collection = get_sessions_collection()
    users_collection = get_users_collection()
    
    try:
        session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    enrolled = enrollments_collection.find({
        "session_id": ObjectId(session_id),
        "status": "enrolled"
    })
    enrollments = await enrolled.to_list(length=None)
    
    # 3. Get user details for each enrollment
    enrollees = []
    for enrollment in enrollments:
        user = await users_collection.find_one({"_id": enrollment["user_id"]})
        if user:
            enrollees.append({
                "user_id": str(user["_id"]),
                "name": f"{user['first_name']} {user['last_name']}",
                "username": user["username"],
                "enrolled_at": enrollment["enrolled_at"]
            })
    
    available_spots = session["capacity"] - session["enrolled_count"]
    
    return SessionEnrolleesResponse(
        session_id=session_id,
        session_title=session["title"],
        capacity=session["capacity"],
        enrolled_count=session["enrolled_count"],
        available_spots=available_spots,
        enrollees=enrollees
    )

@router.get("/my-enrollments", response_model=List[EnrollmentResponse])
async def get_my_enrollments(
    current_user: UserInDB = Depends(get_current_user),
    status_filter: str = "enrolled"  # "enrolled", "cancelled", "completed", "all"
):
    """status_filter: "enrolled", "cancelled", "completed", "all" (default: "enrolled")
    """
    enrollments_collection = get_enrollments_collection()
    sessions_collection = get_sessions_collection()
    users_collection = get_users_collection()
    
    query = {"user_id": ObjectId(current_user.id)}
    if status_filter != "all":
        query["status"] = status_filter

    cursor = enrollments_collection.find(query)
    enrollments = await cursor.to_list(length=None)
    
    result = []
    for enrollment in enrollments:
        session = await sessions_collection.find_one({"_id": enrollment["session_id"]})
        if not session:
            continue  # Skip if session was deleted
        
        host = await users_collection.find_one({"_id": ObjectId(session["host_id"])})
        host_name = f"{host['first_name']} {host['last_name']}" if host else "Unknown"
        
        result.append(EnrollmentResponse(
            id=str(enrollment["_id"]),
            session_id=str(enrollment["session_id"]),
            session_title=session["title"],
            session_start_time=session["start_time"],
            session_end_time=session["end_time"],
            session_location=session["location"],
            host_id=session["host_id"],
            host_name=host_name,
            user_id=current_user.id,
            user_name=f"{current_user.first_name} {current_user.last_name}",
            enrolled_at=enrollment["enrolled_at"],
            status=enrollment["status"]
        ))
    
    return result


@router.get("/my-enrollments/summary", response_model=UserEnrollmentsSummary)
async def get_my_enrollments_summary(
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Get summary of current user's enrollments
    """
    enrollments_collection = get_enrollments_collection()
    sessions_collection = get_sessions_collection()
    
    cursor = enrollments_collection.find({"user_id": ObjectId(current_user.id)})
    enrollments = await cursor.to_list(length=None)
    upcoming = 0
    past = 0
    cancelled = 0
    now = datetime.now(timezone.utc)
    
    for enrollment in enrollments:
        if enrollment["status"] == "cancelled":
            cancelled += 1
            continue
        
        session = await sessions_collection.find_one({"_id": enrollment["session_id"]})
        if session:
            if session["end_time"] > now:
                upcoming += 1
            else:
                past += 1
    
    return UserEnrollmentsSummary(
        user_id=current_user.id,
        user_name=f"{current_user.first_name} {current_user.last_name}",
        upcoming_sessions=upcoming,
        past_sessions=past,
        cancelled_sessions=cancelled,
        total_sessions=len(enrollments)
    )


@router.get("/sessions/{session_id}/check-enrollment")
async def check_enrollment_status(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Check if current user is enrolled in a session
    Useful for frontend to show "Enroll" vs "Cancel Enrollment" button
    """
    enrollments_collection = get_enrollments_collection()
    
    try:
        enrollment = await enrollments_collection.find_one({
            "session_id": ObjectId(session_id),
            "user_id": ObjectId(current_user.id),
            "status": "enrolled"
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    
    return {
        "enrolled": enrollment is not None,
        "enrollment_id": str(enrollment["_id"]) if enrollment else None
    }