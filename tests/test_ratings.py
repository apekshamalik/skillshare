from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from httpx import AsyncClient


async def _mark_session_ended(db, session_id):
    end_time = datetime.now(timezone.utc) - timedelta(hours=1)
    await db.sessions.update_one(
        {"_id": ObjectId(session_id)},
        {
            "$set": {
                "start_time": end_time - timedelta(hours=2),
                "end_time": end_time,
            }
        },
    )


class TestCreateRating:
    @pytest.mark.asyncio
    async def test_create_rating_success(
        self,
        test_client: AsyncClient,
        test_user,
        test_user2,
        test_session,
        db,
        auth_headers,
    ):
        session_id = test_session["id"]

        enroll_response = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )
        assert enroll_response.status_code == 201

        await _mark_session_ended(db, session_id)

        response = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": session_id, "rating": 5, "comment": "Excellent session"},
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == session_id
        assert data["session_title"] == test_session["title"]
        assert data["host_id"] == test_user["user"]["id"]
        assert data["reviewer_id"] == test_user2["user"]["id"]
        assert data["rating"] == 5
        assert data["comment"] == "Excellent session"

    @pytest.mark.asyncio
    async def test_create_rating_requires_auth(self, test_client: AsyncClient, test_session):
        response = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": test_session["id"], "rating": 5, "comment": "Great"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_host_cannot_self_rate(
        self,
        test_client: AsyncClient,
        test_user,
        test_session,
        db,
        auth_headers,
    ):
        await _mark_session_ended(db, test_session["id"])

        response = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": test_session["id"], "rating": 5, "comment": "Self review"},
            headers=auth_headers(test_user["token"]),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Host cannot self-rate"

    @pytest.mark.asyncio
    async def test_cannot_rate_session_that_has_not_ended_yet(
        self,
        test_client: AsyncClient,
        test_user2,
        test_session,
        auth_headers,
    ):
        session_id = test_session["id"]
        enroll_response = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )
        assert enroll_response.status_code == 201

        response = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": session_id, "rating": 4, "comment": "Too early"},
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Cannot rate a session that has not ended yet"

    @pytest.mark.asyncio
    async def test_cannot_rate_cancelled_session(
        self,
        test_client: AsyncClient,
        test_user,
        test_user2,
        test_session,
        auth_headers,
    ):
        session_id = test_session["id"]
        await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )
        cancel_response = await test_client.delete(
            f"/sessions/{session_id}",
            headers=auth_headers(test_user["token"]),
        )
        assert cancel_response.status_code == 204

        response = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": session_id, "rating": 4, "comment": "Cancelled"},
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Cannot rate a cancelled session"

    @pytest.mark.asyncio
    async def test_only_enrolled_users_can_rate(
        self,
        test_client: AsyncClient,
        test_session,
        user_factory,
        db,
        auth_headers,
    ):
        outsider = await user_factory()
        await _mark_session_ended(db, test_session["id"])

        response = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": test_session["id"], "rating": 3, "comment": "I was not there"},
            headers=auth_headers(outsider["token"]),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Only enrolled users can rate this session"

    @pytest.mark.asyncio
    async def test_cannot_rate_same_session_twice(
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
        await _mark_session_ended(db, session_id)

        first_response = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": session_id, "rating": 4, "comment": "First review"},
            headers=auth_headers(test_user2["token"]),
        )
        assert first_response.status_code == 201

        second_response = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": session_id, "rating": 5, "comment": "Second review"},
            headers=auth_headers(test_user2["token"]),
        )

        assert second_response.status_code == 400
        assert second_response.json()["detail"] == "User has already rated this session"

    @pytest.mark.asyncio
    async def test_create_rating_invalid_session_id(
        self,
        test_client: AsyncClient,
        test_user2,
        auth_headers,
    ):
        response = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": "not-a-valid-id", "rating": 4, "comment": "Bad id"},
            headers=auth_headers(test_user2["token"]),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid session id"


class TestGetRatingsForSession:
    @pytest.mark.asyncio
    async def test_get_ratings_for_session_returns_empty_summary(
        self,
        test_client: AsyncClient,
        test_session,
    ):
        response = await test_client.get(f"/ratings/session/{test_session['id']}/ratings")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == test_session["id"]
        assert data["average_rating"] == 0.0
        assert data["total_ratings"] == 0
        assert data["ratings"] == []

    @pytest.mark.asyncio
    async def test_get_ratings_for_session_aggregates_results(
        self,
        test_client: AsyncClient,
        test_user,
        test_user2,
        test_session,
        user_factory,
        db,
        auth_headers,
    ):
        attendee_two = await user_factory(
            first_name="Second",
            last_name="Reviewer",
            username="reviewer2",
            email="reviewer2@example.com",
        )
        session_id = test_session["id"]

        first_enrollment = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers=auth_headers(test_user2["token"]),
        )
        second_enrollment = await test_client.post(
            f"/enrollments/sessions/{session_id}/enroll",
            headers=auth_headers(attendee_two["token"]),
        )
        assert first_enrollment.status_code == 201
        assert second_enrollment.status_code == 201

        await _mark_session_ended(db, session_id)

        first_rating = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": session_id, "rating": 4, "comment": "Helpful"},
            headers=auth_headers(test_user2["token"]),
        )
        second_rating = await test_client.post(
            "/ratings/create-rating",
            json={"session_id": session_id, "rating": 5, "comment": "Excellent"},
            headers=auth_headers(attendee_two["token"]),
        )
        assert first_rating.status_code == 201
        assert second_rating.status_code == 201

        response = await test_client.get(f"/ratings/session/{session_id}/ratings")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["session_title"] == test_session["title"]
        assert data["average_rating"] == 4.5
        assert data["total_ratings"] == 2
        reviewer_names = {rating["reviewer_name"] for rating in data["ratings"]}
        assert reviewer_names == {"Test User2", "Second Reviewer"}
        host_ids = {rating["host_id"] for rating in data["ratings"]}
        assert host_ids == {test_user["user"]["id"]}

    @pytest.mark.asyncio
    async def test_get_ratings_for_session_invalid_id(self, test_client: AsyncClient):
        response = await test_client.get("/ratings/session/not-a-valid-id/ratings")

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid session id"
