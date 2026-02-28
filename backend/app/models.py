from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SessionStatus(StrEnum):
    WAITING = "waiting"
    LIVE = "live"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class GameSession(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: SessionStatus = SessionStatus.WAITING
    join_url: str


class SessionCreateResponse(BaseModel):
    session_id: str
    join_url: str


class SessionReadResponse(BaseModel):
    session_id: str
    status: SessionStatus
