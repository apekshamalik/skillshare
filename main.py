# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.database.database import connect_to_mongo, close_mongo_connection
from src.routes.user.user_routes import router as user_router
from src.routes.session.session_routes import router as session_router
from src.routes.ratings.ratings_routes import router as ratings_routes
from src.routes.enrollment.enrollment_routes import router as enrollment_router
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    await connect_to_mongo()
    yield
    # Shutdown: Close MongoDB connection
    await close_mongo_connection()


app = FastAPI(title="SkillShare Local API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow all origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(user_router, prefix="/users", tags=["Users"])
app.include_router(session_router, prefix="/sessions", tags=["Sessions"])
app.include_router(ratings_routes, prefix="/ratings", tags=["Ratings"])
app.include_router(enrollment_router, prefix="/enrollments", tags=["Enrollments"])