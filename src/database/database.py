from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Optional
import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = "skillshare_db"

client: Optional[AsyncIOMotorClient] = None


def get_database():
    """Get database instance"""
    return client[DATABASE_NAME]

async def connect_to_mongo():
    """Connect to MongoDB on startup"""
    global client
    client = AsyncIOMotorClient(MONGO_URL)
    print(f"Connected to MongoDB at {MONGO_URL}")

async def close_mongo_connection():
    """Close MongoDB connection on shutdown"""
    global client
    if client:
        client.close()
        print("Closed MongoDB connection")

# Collections
def get_users_collection():
    db = get_database()
    return db.users

# def get_sessions_collection():
#     db = get_database()
#     return db.sessions

# def get_enrollments_collection():
#     db = get_database()
#     return db.enrollments

# def get_ratings_collection():
#     db = get_database()
#     return db.ratings

# def get_discussions_collection():
#     db = get_database()
#     return db.discussions