"""Tests for session store, POST /api/sessions (task 2.1), GET token (task 2.2)."""

import time
from unittest.mock import patch

import httpx
import jwt
import pytest

from app.main import app
from models import SessionStatus
from services.store import sessions

TEST_JWT_SECRET = "test-secret-for-integration-test"


def _make_test_token(user_id: str) -> str:
    """Build a JWT with Stream-like payload (user_id, iat, exp) for integration test."""
    now = int(time.time())
    payload = {"user_id": user_id, "iat": now, "exp": now + 3600}
    return jwt.encode(
        payload, TEST_JWT_SECRET, algorithm="HS256"
    )


@pytest.fixture(autouse=True)
def clear_sessions() -> None:
    """Isolate tests by clearing the in-memory session store."""
    sessions.clear()
    yield
    sessions.clear()


@pytest.mark.anyio
async def test_create_session_updates_store_and_initializes_waiting() -> None:
    """POST /api/sessions creates a session, store is updated, SessionStatus is WAITING."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions")
    assert response.status_code == 201
    body = response.json()
    session_id = body["session_id"]
    assert body["stream_call_id"] == f"pickup-{session_id}"
    assert body["join_url"] == f"/game/{session_id}"
    assert session_id in sessions
    stored = sessions[session_id]
    assert stored.status is SessionStatus.WAITING
    assert stored.id == session_id
    assert stored.stream_call_id == body["stream_call_id"]


# --- GET /api/sessions/{id}/token (task 2.2) ---


@pytest.mark.anyio
async def test_get_token_returns_404_when_session_missing() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/sessions/nonexistent/token?role=spectator")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


@pytest.mark.anyio
async def test_get_token_returns_400_for_invalid_role() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/sessions")
        sessions_list = list(sessions.keys())
        session_id = sessions_list[0]
        response = await client.get(
            f"/api/sessions/{session_id}/token?role=invalid_role"
        )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_get_token_integration_decodes_to_correct_user_id() -> None:
    """Integration test: GET token returns JWT that decodes to correct user_id (mock Stream key)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/sessions")
        assert create_resp.status_code == 201
        session_id = create_resp.json()["session_id"]
        call_id = create_resp.json()["stream_call_id"]

    def mock_create_token(api_key: str, api_secret: str, user_id: str, **kwargs) -> str:
        return _make_test_token(user_id)

    with (
        patch("routes.sessions._get_stream_credentials", return_value=("key", "secret")),
        patch("routes.sessions.create_stream_token", side_effect=mock_create_token),
    ):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/sessions/{session_id}/token?role=spectator"
            )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == f"spectator-{session_id}"
    assert body["call_id"] == call_id
    stream_token = body["stream_token"]
    decoded = jwt.decode(
        stream_token, TEST_JWT_SECRET, algorithms=["HS256"]
    )
    assert decoded["user_id"] == f"spectator-{session_id}"
