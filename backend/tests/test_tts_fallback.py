from __future__ import annotations

from typing import Any

from services.commentary_hub import CommentaryHub
from services.commentary_tracker import CommentaryTracker
from services.store import sessions
from models import GameSession
from services.tts_fallback import wrap_tts_with_fallback


class _FakeTTS:
    def __init__(self) -> None:
        self._calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self._should_raise = False

    def synthesize(self, text: str, *args: Any, **kwargs: Any) -> bytes:
        self._calls.append((text, args, kwargs))
        if self._should_raise:
            raise RuntimeError("rate limited")
        return b"ok"


def test_wrap_tts_with_fallback_records_and_falls_back(monkeypatch) -> None:
    # Prepare session and tracker
    session = GameSession(id="session-xyz", stream_call_id="pickup-session-xyz")
    sessions[session.id] = session
    tracker = CommentaryTracker()

    # Use a local hub so we can introspect published payloads without touching globals.
    hub = CommentaryHub()

    published: list[dict[str, Any]] = []

    def _publish(session_id: str, payload: dict[str, Any]) -> None:
        assert session_id == session.id
        published.append(payload)

    # Monkeypatch publish_nowait to call our coroutine inline for determinism.
    def _publish_nowait(session_id: str, payload: dict[str, Any]) -> None:
        # We don't await here; just record synchronously for the test.
        published.append({"session_id": session_id, **payload})

    monkeypatch.setattr(hub, "publish", _publish, raising=True)
    monkeypatch.setattr(hub, "publish_nowait", _publish_nowait, raising=True)

    # Patch the module-level hub used by wrap_tts_with_fallback to our local instance.
    import services.tts_fallback as tts_fallback_module

    monkeypatch.setattr(tts_fallback_module, "commentary_hub", hub, raising=True)

    tts = _FakeTTS()
    tts._should_raise = True

    wrap_tts_with_fallback(
        tts,
        session_id_provider=lambda: session.id,
        tracker=tracker,
    )

    # Calling synthesize() should:
    #   - not propagate the exception (returns empty bytes instead)
    #   - record a commentary entry on the session
    #   - publish a fallback payload to the commentary hub
    result = tts.synthesize("UNBELIEVABLE buzzer-beater at the horn!")
    assert result == b""

    assert len(session.commentary_log) == 1
    entry = session.commentary_log[0]
    assert entry.is_highlight is True

    assert published, "Expected a fallback payload to be published"
    payload = published[-1]
    assert "text" in payload and "energy_level" in payload and "is_highlight" in payload
    assert payload["text"].startswith("UNBELIEVABLE")
    assert payload["is_highlight"] is True

