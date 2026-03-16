import pytest
from bson import ObjectId
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone


class TestEnrollment:
    """Test enrollment workflows"""
    
    @pytest.mark.asyncio
    async def test_enroll_in_session_success(
        self, 
        test_client: AsyncClient, 
        test_user, 
        test_user2, 
        test_session
    ):
        """Test successful enrollment in a session"""
        # test_user created the session, test_user2 enrolls
        session_id = test_session["id"]
        
        response = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == session_id
        assert data["session_title"] == "Test Session"
        assert data["status"] == "enrolled"
        assert data["user_id"] == test_user2["user"]["id"]
    
    @pytest.mark.asyncio
    async def test_cannot_enroll_in_own_session(
        self, 
        test_client: AsyncClient, 
        test_user, 
        test_session
    ):
        """Test that host cannot enroll in their own session"""
        session_id = test_session["id"]
        
        response = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 400
        assert "Cannot enroll in your own session" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_cannot_enroll_twice(
        self, 
        test_client: AsyncClient, 
        test_user2, 
        test_session
    ):
        """Test that user cannot enroll in same session twice"""
        session_id = test_session["id"]
        
        # First enrollment
        response1 = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        assert response1.status_code == 201
        
        # Second enrollment (should fail)
        response2 = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        assert response2.status_code == 400
        assert "already enrolled" in response2.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_enrollment_increases_count(
        self, 
        test_client: AsyncClient, 
        test_user2, 
        test_session
    ):
        """Test that enrollment increases enrolled_count"""
        session_id = test_session["id"]
        
        # Get initial count
        initial_response = await test_client.get(f"/sessions/{session_id}")
        initial_count = initial_response.json()["enrolled_count"]
        
        # Enroll
        await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        # Check count increased
        updated_response = await test_client.get(f"/sessions/{session_id}")
        updated_count = updated_response.json()["enrolled_count"]
        
        assert updated_count == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_cannot_enroll_when_full(
        self, 
        test_client: AsyncClient, 
        test_user
    ):
        """Test that enrollment fails when session is at capacity"""
        # Create session with capacity 1
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        session_data = {
            "title": "Small Session",
            "description": "Only 1 spot",
            "skill_category": "Test",
            "location": "Test",
            "start_time": future_date.isoformat(),
            "end_time": (future_date + timedelta(hours=2)).isoformat(),
            "date": future_date.date().isoformat(),
            "capacity": 1,
            "price": 0.0
        }
        
        create_response = await test_client.post(
            "/sessions/create",
            json=session_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        session_id = create_response.json()["id"]
        
        # Create 2 users and try to enroll both
        user1_data = {
            "first_name": "User", "last_name": "One",
            "username": "user1", "email": "user1@test.com",
            "password": "pass123", "bio": ""
        }
        user2_data = {
            "first_name": "User", "last_name": "Two",
            "username": "user2", "email": "user2@test.com",
            "password": "pass123", "bio": ""
        }
        
        await test_client.post("/users/register", json=user1_data)
        await test_client.post("/users/register", json=user2_data)
        
        login1 = await test_client.post("/users/login", json={
            "username_or_email": "user1", "password": "pass123"
        })
        login2 = await test_client.post("/users/login", json={
            "username_or_email": "user2", "password": "pass123"
        })
        
        token1 = login1.json()["access_token"]
        token2 = login2.json()["access_token"]
        
        # First enrollment should succeed
        response1 = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response1.status_code == 201
        
        # Second enrollment should fail (full)
        response2 = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response2.status_code == 400
        assert "full capacity" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_cannot_enroll_in_cancelled_session(
        self,
        test_client: AsyncClient,
        test_user,
        test_user2,
        test_session,
        auth_headers,
    ):
        session_id = test_session["id"]

        cancel_response = await test_client.delete(
            f"/sessions/{session_id}",
            headers=auth_headers(test_user["token"]),
        )
        assert cancel_response.status_code == 204

        response = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Cannot enroll in cancelled session"

    @pytest.mark.asyncio
    async def test_cannot_enroll_after_session_starts(
        self,
        test_client: AsyncClient,
        test_user2,
        test_session,
        db,
        auth_headers,
    ):
        session_id = test_session["id"]
        started_at = datetime.now(timezone.utc) - timedelta(hours=1)

        await db.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "start_time": started_at,
                    "end_time": started_at + timedelta(hours=2),
                }
            },
        )

        response = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Cannot enroll in a session that has already started"


class TestCancelEnrollment:
    """Test enrollment cancellation"""
    
    @pytest.mark.asyncio
    async def test_cancel_enrollment_success(
        self, 
        test_client: AsyncClient, 
        test_user2, 
        test_session
    ):
        """Test successful enrollment cancellation"""
        session_id = test_session["id"]
        
        # Enroll first
        await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        # Cancel enrollment
        response = await test_client.delete(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_cancel_decreases_count(
        self, 
        test_client: AsyncClient, 
        test_user2, 
        test_session
    ):
        """Test that cancellation decreases enrolled_count"""
        session_id = test_session["id"]
        
        # Enroll
        await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        # Get count after enrollment
        response1 = await test_client.get(f"/sessions/{session_id}")
        count_after_enroll = response1.json()["enrolled_count"]
        
        # Cancel
        await test_client.delete(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        # Check count decreased
        response2 = await test_client.get(f"/sessions/{session_id}")
        count_after_cancel = response2.json()["enrolled_count"]
        
        assert count_after_cancel == count_after_enroll - 1

    @pytest.mark.asyncio
    async def test_cannot_cancel_when_not_enrolled(
        self,
        test_client: AsyncClient,
        test_user2,
        test_session,
        auth_headers,
    ):
        response = await test_client.delete(
            f"/enrollments/sessions/{test_session['id']}/enroll",
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "You are not enrolled in this session"

    @pytest.mark.asyncio
    async def test_cannot_cancel_after_session_starts(
        self,
        test_client: AsyncClient,
        test_user2,
        test_session,
        db,
        auth_headers,
    ):
        session_id = test_session["id"]
        await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )

        started_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "start_time": started_at,
                    "end_time": started_at + timedelta(hours=2),
                }
            },
        )

        response = await test_client.delete(
            f"/enrollments/sessions/{session_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Cannot cancel enrollment after session has started"


class TestEnrollmentViews:
    @pytest.mark.asyncio
    async def test_get_session_enrollees(
        self,
        test_client: AsyncClient,
        test_user2,
        test_session,
        auth_headers,
    ):
        session_id = test_session["id"]
        await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )

        response = await test_client.get(f"/enrollments/sessions/{session_id}/enrollees")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["enrolled_count"] == 1
        assert data["available_spots"] == test_session["capacity"] - 1
        assert len(data["enrollees"]) == 1
        assert data["enrollees"][0]["user_id"] == test_user2["user"]["id"]
        assert data["enrollees"][0]["username"] == test_user2["user"]["username"]


class TestMyEnrollments:
    """Test viewing user's enrollments"""
    
    @pytest.mark.asyncio
    async def test_get_my_enrollments(
        self, 
        test_client: AsyncClient, 
        test_user2, 
        test_session
    ):
        """Test getting list of user's enrollments"""
        session_id = test_session["id"]
        
        # Enroll in session
        await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        # Get my enrollments
        response = await test_client.get(
            "/enrollments/my-enrollments",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["session_id"] == session_id
        assert data[0]["status"] == "enrolled"
    
    @pytest.mark.asyncio
    async def test_check_enrollment_status(
        self, 
        test_client: AsyncClient, 
        test_user2, 
        test_session
    ):
        """Test checking if user is enrolled in a session"""
        session_id = test_session["id"]
        
        # Check before enrollment
        response1 = await test_client.get(
            f"/enrollments/sessions/{session_id}/check-enrollment",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        assert response1.json()["enrolled"] is False
        
        # Enroll
        await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        # Check after enrollment
        response2 = await test_client.get(
            f"/enrollments/sessions/{session_id}/check-enrollment",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        assert response2.json()["enrolled"] is True

    @pytest.mark.asyncio
    async def test_get_my_enrollments_by_status_filter(
        self,
        test_client: AsyncClient,
        test_user,
        test_user2,
        session_factory,
        auth_headers,
    ):
        active_session = await session_factory(test_user["token"], title="Active Session")
        cancelled_session = await session_factory(test_user["token"], title="Cancelled Session")

        active_id = active_session.json()["id"]
        cancelled_id = cancelled_session.json()["id"]

        await test_client.post(
            f"/enrollments/sessions/{active_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )
        await test_client.post(
            f"/enrollments/sessions/{cancelled_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )
        await test_client.delete(
            f"/enrollments/sessions/{cancelled_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )

        response = await test_client.get(
            "/enrollments/my-enrollments?status_filter=cancelled",
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["session_id"] == cancelled_id
        assert data[0]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_get_my_enrollments_summary(
        self,
        test_client: AsyncClient,
        test_user,
        test_user2,
        session_factory,
        db,
        auth_headers,
    ):
        upcoming_response = await session_factory(test_user["token"], title="Upcoming Session")
        past_response = await session_factory(test_user["token"], title="Past Session")
        cancelled_response = await session_factory(test_user["token"], title="Cancelled Session")

        upcoming_id = upcoming_response.json()["id"]
        past_id = past_response.json()["id"]
        cancelled_id = cancelled_response.json()["id"]

        await test_client.post(
            f"/enrollments/sessions/{upcoming_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )
        await test_client.post(
            f"/enrollments/sessions/{past_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )
        await test_client.post(
            f"/enrollments/sessions/{cancelled_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )
        await test_client.delete(
            f"/enrollments/sessions/{cancelled_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )

        past_end = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.sessions.update_one(
            {"_id": ObjectId(past_id)},
            {
                "$set": {
                    "start_time": past_end - timedelta(hours=2),
                    "end_time": past_end,
                }
            },
        )

        response = await test_client.get(
            "/enrollments/my-enrollments/summary",
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["upcoming_sessions"] == 1
        assert data["past_sessions"] == 1
        assert data["cancelled_sessions"] == 1
        assert data["total_sessions"] == 3

    @pytest.mark.asyncio
    async def test_check_enrollment_invalid_session_id(
        self,
        test_client: AsyncClient,
        test_user2,
        auth_headers,
    ):
        response = await test_client.get(
            "/enrollments/sessions/not-a-valid-id/check-enrollment",
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid session ID format"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path",
        [
            "/enrollments/my-enrollments",
            "/enrollments/my-enrollments/summary",
        ],
    )
    async def test_enrollment_views_require_auth(self, path, test_client: AsyncClient):
        response = await test_client.get(path)

        assert response.status_code == 401
