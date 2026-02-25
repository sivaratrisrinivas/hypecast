from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from models import ENERGY_THRESHOLD, CommentaryEntry, GameSession
from services.commentary_tracker import CommentaryTracker
from services.store import sessions


@pytest.fixture(autouse=True)
def _clear_sessions() -> None:
    sessions.clear()


def _dummy_session(session_id: str = "abc123") -> GameSession:
    session = GameSession(id=session_id, stream_call_id=f"pickup-{session_id}")
    # Backdate created_at slightly to make timestamps stable in tests.
    session.created_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    sessions[session_id] = session
    return session


@pytest.mark.parametrize(
    ("text", "expected_highlight"),
    [
        ("UNBELIEVABLE shot from the corner!", True),
        ("What a shot from downtown!", True),
        ("INCREDIBLE defensive effort!", True),
        ("Nice ball movement around the perimeter.", False),
        ("Calm setup at half court.", False),
    ],
)
def test_energy_scoring_highlight_keywords(text: str, expected_highlight: bool) -> None:
    tracker = CommentaryTracker()
    energy = tracker.score_energy(text)
    assert (energy > ENERGY_THRESHOLD) is expected_highlight


def test_record_appends_entry_to_session_log() -> None:
    session = _dummy_session("session-1")
    tracker = CommentaryTracker()

    now = session.created_at + timedelta(seconds=12.3)
    entry = tracker.record(session.id, "UNBELIEVABLE finish at the rim!", now=now)

    assert isinstance(entry, CommentaryEntry)
    assert len(session.commentary_log) == 1
    stored = session.commentary_log[0]
    assert stored is entry
    # Timestamp should be relative to created_at (≈ 12.3s)
    assert pytest.approx(stored.timestamp, rel=1e-3) == 12.3
    assert stored.energy_level > ENERGY_THRESHOLD
    assert stored.is_highlight is True


def test_record_no_session_is_noop() -> None:
    tracker = CommentaryTracker()
    entry = tracker.record("missing-session", "Great ball movement!")
    assert entry is None

