from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Optional
import os
from dotenv import load_dotenv
import certifi
import ssl

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
    
    # Create SSL context
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    client = AsyncIOMotorClient(
        MONGO_URL,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=20000,
    )
    
    # Test the connection
    try:
        await client.admin.command('ping')
        print(f"Successfully connected to MongoDB")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise
    
async def close_mongo_connection():
    """Close MongoDB connection on shutdown"""
    global client
    if client:
        client.close()
        print("Closed MongoDB connection")


def get_users_collection():
    db = get_database()
    return db.users

def get_sessions_collection():
    db = get_database()
    return db.sessions

def get_enrollments_collection():
    db = get_database()
    return db.enrollments
       
def get_ratings_collection():
    db = get_database()
    return db.ratings

def get_discussions_collection():
    db = get_database()
    return db.discussions