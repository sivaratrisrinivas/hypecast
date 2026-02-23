"""Tests for session store and POST /api/sessions (task 2.1)."""

import httpx
import pytest

from app.main import app
from models import SessionStatus
from services.store import sessions


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
