import pytest
import os

# CRITICAL: Set test database BEFORE importing app
os.environ["DATABASE_NAME"] = "skillshare_test"

from httpx import AsyncClient, ASGITransport
from main import app
from src.database.database import connect_to_mongo, close_mongo_connection, get_database


# Remove the custom event_loop fixture - let pytest-asyncio handle it

@pytest.fixture(scope="module", autouse=True)
async def setup_database():
    """Connect to database once for all tests"""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


@pytest.fixture(autouse=True)
async def clean_database():
    """Clean database after each test"""
    yield  # Test runs here
    
    # Clean up after test
    try:
        db = get_database()
        collections = await db.list_collection_names()
        for collection_name in collections:
            await db[collection_name].delete_many({})
    except Exception as e:
        print(f"Cleanup warning: {e}")


@pytest.fixture
async def test_client():
    """HTTP client for making test requests"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
async def test_user(test_client):
    """Create and login a test user"""
    user_data = {
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
        "bio": "Test bio"
    }
    
    response = await test_client.post("/users/register", json=user_data)
    assert response.status_code == 201
    user = response.json()
    
    login_response = await test_client.post("/users/login", json={
        "username_or_email": "testuser",
        "password": "password123"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    return {"user": user, "token": token, "credentials": user_data}


@pytest.fixture
async def test_user2(test_client):
    """Create a second test user"""
    user_data = {
        "first_name": "Test",
        "last_name": "User2",
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "password123",
        "bio": "Test bio 2"
    }
    
    response = await test_client.post("/users/register", json=user_data)
    assert response.status_code == 201
    user = response.json()
    
    login_response = await test_client.post("/users/login", json={
        "username_or_email": "testuser2",
        "password": "password123"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    return {"user": user, "token": token, "credentials": user_data}


@pytest.fixture
async def test_session(test_client, test_user):
    """Create a test session"""
    from datetime import datetime, timedelta, timezone
    
    future_date = datetime.now(timezone.utc) + timedelta(days=7)
    
    session_data = {
        "title": "Test Session",
        "description": "Test description",
        "skill_category": "Cooking",
        "location": "Test Location",
        "start_time": future_date.isoformat(),
        "end_time": (future_date + timedelta(hours=2)).isoformat(),
        "date": future_date.date().isoformat(),
        "capacity": 5,
        "price": 0.0
    }
    
    response = await test_client.post(
        "/sessions/create",
        json=session_data,
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    assert response.status_code == 201
    
    return response.json()