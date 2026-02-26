"""Session REST API. Mountable via ServeOptions(fast_api=app) for Vision Agents Runner."""

import logging
import os
import secrets

from fastapi import APIRouter, HTTPException, Query

# Avoid 0/O, 1/I/l in session IDs so QR codes and links don't get misread (e.g. 0 vs O).
_SESSION_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
_SESSION_ID_LENGTH = 12
from pydantic import BaseModel

from models.session import GameSession, SessionStatus
from services.store import sessions
from services.stream_token import create_stream_token

router = APIRouter(tags=["sessions"])
logger = logging.getLogger(__name__)
_sprint2_polled_sessions: set[str] = set()

TOKEN_VALIDITY_SECONDS = 3600
VALID_ROLES = ("camera", "spectator")


class SessionCreateResponse(BaseModel):
    session_id: str
    stream_call_id: str
    stream_token: str
    join_url: str


class SessionTokenResponse(BaseModel):
    stream_token: str
    user_id: str
    call_id: str


class SessionReadResponse(BaseModel):
    """Session status for polling. GET /api/sessions/{id}."""

    status: SessionStatus
    reel_id: str | None = None
    reel_url: str | None = None


def _get_stream_credentials() -> tuple[str, str]:
    api_key = os.environ.get("STREAM_API_KEY", "").strip()
    api_secret = os.environ.get("STREAM_API_SECRET", "").strip()
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=503,
            detail="Stream credentials not configured (STREAM_API_KEY / STREAM_API_SECRET)",
        )
    return api_key, api_secret


def _generate_session_id() -> str:
    """Session ID safe for URLs/QR: no 0/O, 1/I/l to avoid misread."""
    return "".join(secrets.choice(_SESSION_ALPHABET) for _ in range(_SESSION_ID_LENGTH))


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
def create_session() -> SessionCreateResponse:
    """Create a game session and return join details."""
    logger.info("[sessions] POST /api/sessions called")
    session_id = _generate_session_id()
    stream_call_id = f"pickup-{session_id}"
    session = GameSession(id=session_id, stream_call_id=stream_call_id)
    sessions[session_id] = session
    logger.info("[SPRINT 2] Session created (session store + POST /api/sessions): session_id=%s", session_id)
    try:
        api_key, api_secret = _get_stream_credentials()
        user_id = f"camera-{session_id}"
        stream_token = create_stream_token(
            api_key, api_secret, user_id, expiration_seconds=TOKEN_VALIDITY_SECONDS
        )
    except HTTPException:
        stream_token = "placeholder"
    logger.info(
        "[sessions] POST /sessions → 201 session_id=%s stream_call_id=%s (Runner will create call on Stream when it handles POST /sessions)",
        session_id,
        stream_call_id,
    )
    return SessionCreateResponse(
        session_id=session_id,
        stream_call_id=stream_call_id,
        stream_token=stream_token,
        join_url=f"/game/{session_id}",
    )


@router.get(
    "/sessions/{session_id}/token",
    response_model=SessionTokenResponse,
    status_code=200,
)
def get_session_token(
    session_id: str,
    role: str = Query(..., description="Participant role: camera or spectator"),
) -> SessionTokenResponse:
    """Generate a Stream user token for a participant (camera or spectator) joining the call."""
    logger.info("[sessions] GET /api/sessions/%s/token called. role=%s", session_id, role)
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"role must be one of {list(VALID_ROLES)}",
        )
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[session_id]
    api_key, api_secret = _get_stream_credentials()
    user_id = f"{role}-{session_id}"
    stream_token = create_stream_token(
        api_key, api_secret, user_id, expiration_seconds=TOKEN_VALIDITY_SECONDS
    )
    logger.info("[SPRINT 2] Stream token issued (GET /api/sessions/{id}/token): session_id=%s role=%s", session_id, role)
    return SessionTokenResponse(
        stream_token=stream_token,
        user_id=user_id,
        call_id=session.stream_call_id,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionReadResponse,
    status_code=200,
)
def get_session(session_id: str) -> SessionReadResponse:
    """Get session status for polling. Used by frontend to track WAITING -> LIVE -> etc."""
    logger.info("[sessions] GET /api/sessions/%s called", session_id)
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[session_id]
    if session_id not in _sprint2_polled_sessions:
        _sprint2_polled_sessions.add(session_id)
        logger.info("[SPRINT 2] Session status returned (GET /api/sessions/{id} polling): session_id=%s status=%s", session_id, session.status)
    return SessionReadResponse(
        status=session.status,
        reel_id=session.reel_id,
        reel_url=session.reel_url,
    )
