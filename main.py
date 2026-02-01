# main.py
from fastapi import FastAPI
from src.routes.user import user_routes

app = FastAPI(title="SkillShare Local API")

# Include the users router under /users
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
