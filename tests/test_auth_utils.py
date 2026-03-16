from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from src.auth import auth_utils


def test_create_access_token_round_trips_payload(monkeypatch):
    monkeypatch.setattr(auth_utils, "SECRET_KEY", "unit-test-secret")

    token = auth_utils.create_access_token({"sub": "user-123"})
    payload = auth_utils.verify_token(token)

    assert payload["sub"] == "user-123"
    assert "exp" in payload


def test_create_access_token_respects_custom_expiration(monkeypatch):
    monkeypatch.setattr(auth_utils, "SECRET_KEY", "unit-test-secret")
    expires_delta = timedelta(minutes=5)

    token = auth_utils.create_access_token({"sub": "user-456"}, expires_delta=expires_delta)
    payload = jwt.decode(token, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM])
    expiration = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    assert expiration <= datetime.now(timezone.utc) + timedelta(minutes=6)
    assert expiration >= datetime.now(timezone.utc) + timedelta(minutes=4)


def test_verify_token_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(auth_utils, "SECRET_KEY", "unit-test-secret")

    with pytest.raises(HTTPException) as exc_info:
        auth_utils.verify_token("not-a-real-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


def test_verify_token_rejects_expired_token(monkeypatch):
    monkeypatch.setattr(auth_utils, "SECRET_KEY", "unit-test-secret")
    token = auth_utils.create_access_token(
        {"sub": "user-789"},
        expires_delta=timedelta(minutes=-1),
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_utils.verify_token(token)

    assert exc_info.value.status_code == 401
