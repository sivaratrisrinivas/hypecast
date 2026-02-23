from datetime import datetime

from models import (
    ENERGY_THRESHOLD,
    CommentaryEntry,
    GameSession,
    Highlight,
    SessionStatus,
)


def test_game_session_defaults() -> None:
    session = GameSession(id="abc123", stream_call_id="pickup-abc123")
    assert session.status is SessionStatus.WAITING
    assert isinstance(session.created_at, datetime)
    assert session.ended_at is None
    assert session.commentary_log == []
    assert session.highlights == []
    assert session.reel_id is None
    assert session.reel_url is None


def test_commentary_entry_fields() -> None:
    entry = CommentaryEntry(
        timestamp=10.5,
        text="WHAT A SHOT from downtown!",
        energy_level=0.9,
        is_highlight=True,
    )
    assert entry.timestamp == 10.5
    assert "SHOT" in entry.text.upper()
    assert entry.energy_level > ENERGY_THRESHOLD
    assert entry.is_highlight is True


def test_highlight_job_relationships() -> None:
    highlight = Highlight(
        start_time=5.0,
        end_time=10.0,
        energy_score=0.8,
        commentary_text="Incredible finish at the rim!",
    )
    session = GameSession(id="abc123", stream_call_id="pickup-abc123")
    session.highlights.append(highlight)

    assert len(session.highlights) == 1
    assert session.highlights[0].energy_score >= 0.8
