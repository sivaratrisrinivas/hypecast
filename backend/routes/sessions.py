"""Session REST API. Mountable via ServeOptions(fast_api=app) for Vision Agents Runner."""

import secrets

from fastapi import APIRouter
from pydantic import BaseModel

from models.session import GameSession
from services.store import sessions

router = APIRouter(prefix="/api", tags=["sessions"])


class SessionCreateResponse(BaseModel):
    session_id: str
    stream_call_id: str
    stream_token: str
    join_url: str


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
def create_session() -> SessionCreateResponse:
    """Create a game session and return join details. Stream token is placeholder until 2.2."""
    session_id = secrets.token_urlsafe(9)
    stream_call_id = f"pickup-{session_id}"
    session = GameSession(id=session_id, stream_call_id=stream_call_id)
    sessions[session_id] = session
    return SessionCreateResponse(
        session_id=session_id,
        stream_call_id=stream_call_id,
        stream_token="placeholder",
        join_url=f"/game/{session_id}",
    )
