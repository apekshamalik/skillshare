# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.database import connect_to_mongo, close_mongo_connection
from src.routes.user import router as user_routes 
app = FastAPI(title="SkillShare Local API")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    await connect_to_mongo()
    yield
    # Shutdown: Close MongoDB connection
    await close_mongo_connection()

# Include the users router under /users
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
