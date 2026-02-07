# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.database.database import connect_to_mongo, close_mongo_connection
from src.routes.user.user_routes import router as user_router
from src.routes.session.session_routes import router as session_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    await connect_to_mongo()
    yield
    # Shutdown: Close MongoDB connection
    await close_mongo_connection()


app = FastAPI(title="SkillShare Local API", lifespan=lifespan)

# Include routers
app.include_router(user_router, prefix="/users", tags=["Users"])
app.include_router(session_router, prefix="/sessions", tags=["Sessions"])
