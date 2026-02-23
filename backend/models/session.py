from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .commentary import CommentaryEntry
from .highlight import Highlight


class SessionStatus(str, Enum):
    WAITING = "waiting"
    LIVE = "live"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class GameSession:
    id: str                                # nanoid
    stream_call_id: str
    stream_call_type: str = "default"
    status: SessionStatus = SessionStatus.WAITING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    commentary_log: list[CommentaryEntry] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)
    reel_id: str | None = None
    reel_url: str | None = None
