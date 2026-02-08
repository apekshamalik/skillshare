from fastapi import FastAPI, HTTPException, APIRouter, Depends, status
from typing import List
from bson import ObjectId
from src.schemas.session.session_schema import SessionCreateRequest, SessionCreateResponse, SessionInDB, SessionUpdateRequest
from datetime import datetime, timezone
from src.database.database import get_sessions_collection
from src.auth.dependencies import get_current_user
from src.schemas.user.user_schema import UserInDB


router = APIRouter()


#create a new session(requires authentication)
@router.post("/create", response_model = SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(session: SessionCreateRequest, current_user: UserInDB = Depends(get_current_user)):

    sessions_collection = get_sessions_collection()
    
    session_doc = {
        "title": session.title,
        "description": session.description,
        "skill_category": session.skill_category,
        "location": session.location,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "date": session.date,
        "capacity": session.capacity,
        "price": session.price,
        "host_id": current_user.id,
        "enrolled_count": 0,
        "status": "active",
        "created_at": datetime.now(timezone.utc)
    }

    result = await sessions_collection.insert_one(session_doc)
    session_doc["_id"] = result.inserted_id

    return SessionCreateResponse(
        id = str(session_doc["_id"]),
        title = session_doc["title"],
        description = session_doc["description"],
        skill_category = session_doc["skill_category"],
        location = session_doc["location"],
        start_time = session_doc["start_time"],
        end_time = session_doc["end_time"],
        date = session_doc["date"],
        capacity = session_doc["capacity"],
        price = session_doc["price"],
        host_id = session_doc["host_id"],
        enrolled_count = session_doc["enrolled_count"],
        status = session_doc["status"],
        created_at = session_doc["created_at"]
    )


#list all active sessions
@router.get("/all", response_model=List[SessionCreateResponse])
async def list_sessions(): 
    sessions_collection = get_sessions_collection()

    try:
        cursor = sessions_collection.find({"status": "active"})
        sessions = await cursor.to_list(length=100)

    except:
        raise HTTPException(status_code=500, detail="Error retrieving sessions")

    if not sessions:
        raise HTTPException(status_code=404, detail="No active sessions found")

    return [
        SessionCreateResponse(
            id=str(session["_id"]),
            title=session["title"],
            description=session["description"],
            skill_category=session["skill_category"],
            location=session["location"],
            start_time=session["start_time"],
            end_time=session["end_time"],
            date=session["date"],
            capacity=session["capacity"],
            price=session["price"],
            host_id=session["host_id"],
            enrolled_count=session["enrolled_count"],
            status=session["status"],
            created_at=session["created_at"]
        ) for session in sessions
    ]
    


#get a single session id
@router.get("/{session_id}", response_model=SessionCreateResponse)
async def get_session(session_id: str):
    sessions_collection = get_sessions_collection()

    try:
        session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionCreateResponse(
        id=str(session["_id"]),
        title=session["title"],
        description=session["description"],
        skill_category=session["skill_category"],
        location=session["location"],
        start_time=session["start_time"],
        end_time=session["end_time"],
        date=session["date"],
        capacity=session["capacity"],
        price=session["price"],
        host_id=session["host_id"],
        enrolled_count=session["enrolled_count"],
        status=session["status"],
        created_at=session["created_at"]
    )


@router.put("/{session_id}", response_model=SessionCreateResponse)
async def update_session(
    session_id: str, 
    session_update: SessionUpdateRequest, 
    current_user: UserInDB = Depends(get_current_user)
):
    sessions_collection = get_sessions_collection()

    try:
        obj_id = ObjectId(session_id)
        session = await sessions_collection.find_one({"_id": obj_id})
    except:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["host_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this session")

    update_data = {k: v for k, v in session_update.model_dump().items() if v is not None}

    if update_data:
        await sessions_collection.update_one({"_id": obj_id}, {"$set": update_data})
        session = await sessions_collection.find_one({"_id": obj_id})

    return SessionCreateResponse(
        id=str(session["_id"]),
        title=session["title"],
        description=session["description"],
        skill_category=session["skill_category"],
        location=session["location"],
        start_time=session["start_time"],
        end_time=session["end_time"],
        date=session["date"],
        capacity=session["capacity"],
        price=session["price"],
        host_id=session["host_id"],
        enrolled_count=session["enrolled_count"],
        status=session["status"],
        created_at=session["created_at"]
    )

#delete a session
@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str, 
    current_user: UserInDB = Depends(get_current_user)
):
    sessions_collection = get_sessions_collection()

    try:
        obj_id = ObjectId(session_id)
        session = await sessions_collection.find_one({"_id": obj_id})
    except:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["host_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this session")

    await sessions_collection.update_one({"_id": obj_id}, {"$set": {"status": "cancelled"}})
    
    return


