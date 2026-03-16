import os
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# CRITICAL: Set test database BEFORE importing app
os.environ["DATABASE_NAME"] = "skillshare_test"

import main as main_module
import src.database.database as database_module
from main import app
from tests.fake_mongo import FakeMongoClient


async def _clear_database():
    """Delete all documents from every collection in the test database."""
    db = database_module.get_database()
    collections = await db.list_collection_names()
    for collection_name in collections:
        await db[collection_name].delete_many({})


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def setup_database():
    """Provide a local in-memory Mongo substitute for the full test session."""
    database_module.client = FakeMongoClient()

    async def _noop():
        return None

    database_module.connect_to_mongo = _noop
    database_module.close_mongo_connection = _noop
    main_module.connect_to_mongo = _noop
    main_module.close_mongo_connection = _noop

    await _clear_database()
    yield
    await _clear_database()
    database_module.client = None


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    """Provide per-test isolation around the shared test database."""
    await _clear_database()
    yield
    try:
        await _clear_database()
    except Exception as exc:
        print(f"Cleanup warning: {exc}")


@pytest_asyncio.fixture
async def test_client():
    """HTTP client for making test requests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_headers():
    """Generate Authorization headers for bearer-authenticated requests."""
    return lambda token: {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def db():
    """Expose the test database for rare direct state adjustments in tests."""
    return database_module.get_database()


@pytest_asyncio.fixture
async def user_factory(test_client):
    """Create and log in users with unique credentials by default."""
    counter = 0

    async def create_user(**overrides):
        nonlocal counter
        counter += 1
        user_data = {
            "first_name": "Test",
            "last_name": f"User{counter}",
            "username": f"testuser{counter}",
            "email": f"test{counter}@example.com",
            "password": "password123",
            "bio": f"Test bio {counter}",
        }
        user_data.update(overrides)

        response = await test_client.post("/users/register", json=user_data)
        assert response.status_code == 201
        user = response.json()

        login_response = await test_client.post(
            "/users/login",
            json={
                "username_or_email": user_data["username"],
                "password": user_data["password"],
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        return {"user": user, "token": token, "credentials": user_data}

    return create_user


@pytest_asyncio.fixture
async def session_factory(test_client, auth_headers):
    """Create sessions with a future default schedule and overridable fields."""

    async def create_session(token, **overrides):
        start_time = overrides.pop("start_time", datetime.now(timezone.utc) + timedelta(days=7))
        end_time = overrides.pop("end_time", start_time + timedelta(hours=2))

        session_data = {
            "title": "Test Session",
            "description": "Test description",
            "skill_category": "Cooking",
            "location": "Test Location",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "capacity": 5,
            "price": 0.0,
        }
        session_data.update(overrides)

        response = await test_client.post(
            "/sessions/create",
            json=session_data,
            headers=auth_headers(token),
        )
        return response

    return create_session


@pytest_asyncio.fixture
async def test_user(user_factory):
    """Create and log in a canonical test user."""
    return await user_factory(
        first_name="Test",
        last_name="User",
        username="testuser",
        email="test@example.com",
        bio="Test bio",
    )


@pytest_asyncio.fixture
async def test_user2(user_factory):
    """Create and log in a second canonical test user."""
    return await user_factory(
        first_name="Test",
        last_name="User2",
        username="testuser2",
        email="test2@example.com",
        bio="Test bio 2",
    )


@pytest_asyncio.fixture
async def test_session(session_factory, test_user):
    """Create a canonical future session hosted by test_user."""
    response = await session_factory(test_user["token"])
    assert response.status_code == 201
    return response.json()
