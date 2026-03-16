from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


class TestSessionCreation:
    @pytest.mark.asyncio
    async def test_create_session_success(
        self,
        test_client: AsyncClient,
        test_user,
        auth_headers,
    ):
        start_time = datetime.now(timezone.utc) + timedelta(days=10)
        payload = {
            "title": "  Bread Basics  ",
            "description": "  Learn to bake bread  ",
            "skill_category": "  Cooking  ",
            "location": "  Student Center  ",
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(hours=2)).isoformat(),
            "capacity": 8,
            "price": 12.5,
        }

        response = await test_client.post(
            "/sessions/create",
            json=payload,
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Bread Basics"
        assert data["description"] == "Learn to bake bread"
        assert data["skill_category"] == "Cooking"
        assert data["location"] == "Student Center"
        assert data["capacity"] == 8
        assert data["price"] == 12.5
        assert data["host_id"] == test_user["user"]["id"]
        assert data["enrolled_count"] == 0
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_session_requires_auth(self, test_client: AsyncClient):
        start_time = datetime.now(timezone.utc) + timedelta(days=2)
        response = await test_client.post(
            "/sessions/create",
            json={
                "title": "Session",
                "description": "Description",
                "skill_category": "Cooking",
                "location": "Campus",
                "start_time": start_time.isoformat(),
                "end_time": (start_time + timedelta(hours=1)).isoformat(),
                "capacity": 5,
                "price": 0,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_session_rejects_past_date(
        self,
        test_client: AsyncClient,
        test_user,
        auth_headers,
    ):
        start_time = datetime.now(timezone.utc) - timedelta(days=1)

        response = await test_client.post(
            "/sessions/create",
            json={
                "title": "Past Session",
                "description": "Description",
                "skill_category": "Cooking",
                "location": "Campus",
                "start_time": start_time.isoformat(),
                "end_time": (start_time + timedelta(hours=1)).isoformat(),
                "capacity": 5,
                "price": 0,
            },
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "Session date cannot be in the past"

    @pytest.mark.asyncio
    async def test_create_session_rejects_end_before_start(
        self,
        test_client: AsyncClient,
        test_user,
        auth_headers,
    ):
        start_time = datetime.now(timezone.utc) + timedelta(days=4)

        response = await test_client.post(
            "/sessions/create",
            json={
                "title": "Bad Times",
                "description": "Description",
                "skill_category": "Cooking",
                "location": "Campus",
                "start_time": start_time.isoformat(),
                "end_time": (start_time - timedelta(minutes=30)).isoformat(),
                "capacity": 5,
                "price": 0,
            },
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "end_time must be after start_time"

    @pytest.mark.asyncio
    async def test_create_session_rejects_cross_day_times(
        self,
        test_client: AsyncClient,
        test_user,
        auth_headers,
    ):
        start_time = datetime.now(timezone.utc) + timedelta(days=5)
        end_time = start_time + timedelta(days=1, hours=1)

        response = await test_client.post(
            "/sessions/create",
            json={
                "title": "Overnight Session",
                "description": "Description",
                "skill_category": "Cooking",
                "location": "Campus",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "capacity": 5,
                "price": 0,
            },
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "start_time and end_time must be on the same date"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("field", "value", "detail"),
        [
            ("title", "   ", "Title cannot be empty or whitespace only"),
            ("description", "   ", "Description cannot be empty or whitespace only"),
            ("skill_category", "   ", "Skill category cannot be empty or whitespace only"),
            ("location", "   ", "Location cannot be empty or whitespace only"),
        ],
    )
    async def test_create_session_rejects_whitespace_only_fields(
        self,
        field,
        value,
        detail,
        test_client: AsyncClient,
        test_user,
        auth_headers,
    ):
        start_time = datetime.now(timezone.utc) + timedelta(days=3)
        payload = {
            "title": "Session",
            "description": "Description",
            "skill_category": "Cooking",
            "location": "Campus",
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(hours=1)).isoformat(),
            "capacity": 5,
            "price": 0,
        }
        payload[field] = value

        response = await test_client.post(
            "/sessions/create",
            json=payload,
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == detail


class TestSessionQueries:
    @pytest.mark.asyncio
    async def test_list_sessions_returns_active_sessions_only(
        self,
        test_client: AsyncClient,
        test_user,
        session_factory,
        auth_headers,
    ):
        response_one = await session_factory(test_user["token"], title="Cooking 101")
        response_two = await session_factory(test_user["token"], title="Pottery Basics")

        await test_client.delete(
            f"/sessions/{response_two.json()['id']}",
            headers=auth_headers(test_user["token"]),
        )

        list_response = await test_client.get("/sessions/all")

        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data) == 1
        assert data[0]["id"] == response_one.json()["id"]
        assert data[0]["title"] == "Cooking 101"

    @pytest.mark.asyncio
    async def test_list_sessions_returns_404_when_empty(self, test_client: AsyncClient):
        response = await test_client.get("/sessions/all")

        assert response.status_code == 404
        assert response.json()["detail"] == "No active sessions found"

    @pytest.mark.asyncio
    async def test_get_session_success(self, test_client: AsyncClient, test_session):
        response = await test_client.get(f"/sessions/{test_session['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_session["id"]
        assert data["title"] == test_session["title"]

    @pytest.mark.asyncio
    async def test_get_session_invalid_id(self, test_client: AsyncClient):
        response = await test_client.get("/sessions/not-a-valid-id")

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid session ID format"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, test_client: AsyncClient):
        response = await test_client.get("/sessions/507f1f77bcf86cd799439011")

        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"


class TestSessionUpdate:
    @pytest.mark.asyncio
    async def test_host_can_update_session(
        self,
        test_client: AsyncClient,
        test_user,
        test_session,
        auth_headers,
    ):
        response = await test_client.put(
            f"/sessions/{test_session['id']}",
            json={
                "title": "Updated Session",
                "description": "Updated description",
                "capacity": 12,
                "price": 25,
            },
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Session"
        assert data["description"] == "Updated description"
        assert data["capacity"] == 12
        assert data["price"] == 25
        assert data["skill_category"] == test_session["skill_category"]

    @pytest.mark.asyncio
    async def test_update_session_requires_auth(self, test_client: AsyncClient, test_session):
        response = await test_client.put(
            f"/sessions/{test_session['id']}",
            json={"title": "Updated Session"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_host_cannot_update_session(
        self,
        test_client: AsyncClient,
        test_user2,
        test_session,
        auth_headers,
    ):
        response = await test_client.put(
            f"/sessions/{test_session['id']}",
            json={"title": "Hijacked Title"},
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Not authorized to update this session"

    @pytest.mark.asyncio
    async def test_update_session_invalid_id(
        self,
        test_client: AsyncClient,
        test_user,
        auth_headers,
    ):
        response = await test_client.put(
            "/sessions/not-a-valid-id",
            json={"title": "Updated Session"},
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid session ID format"

    @pytest.mark.asyncio
    async def test_update_session_not_found(
        self,
        test_client: AsyncClient,
        test_user,
        auth_headers,
    ):
        response = await test_client.put(
            "/sessions/507f1f77bcf86cd799439011",
            json={"title": "Updated Session"},
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"


class TestSessionCancellation:
    @pytest.mark.asyncio
    async def test_host_can_cancel_session(
        self,
        test_client: AsyncClient,
        test_user,
        test_session,
        auth_headers,
    ):
        response = await test_client.delete(
            f"/sessions/{test_session['id']}",
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 204

        fetch_response = await test_client.get(f"/sessions/{test_session['id']}")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_session_requires_auth(self, test_client: AsyncClient, test_session):
        response = await test_client.delete(f"/sessions/{test_session['id']}")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_host_cannot_cancel_session(
        self,
        test_client: AsyncClient,
        test_user2,
        test_session,
        auth_headers,
    ):
        response = await test_client.delete(
            f"/sessions/{test_session['id']}",
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Not authorized to cancel this session"

    @pytest.mark.asyncio
    async def test_cancel_session_invalid_id(
        self,
        test_client: AsyncClient,
        test_user,
        auth_headers,
    ):
        response = await test_client.delete(
            "/sessions/not-a-valid-id",
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid session ID format"

    @pytest.mark.asyncio
    async def test_cancel_session_not_found(
        self,
        test_client: AsyncClient,
        test_user,
        auth_headers,
    ):
        response = await test_client.delete(
            "/sessions/507f1f77bcf86cd799439011",
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"
