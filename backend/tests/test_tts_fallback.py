from __future__ import annotations

from typing import Any
import pytest

from models.session import GameSession
from services.commentary_hub import CommentaryHub
from services.commentary_tracker import CommentaryTracker
from services.store import sessions
from services.tts_fallback import wrap_tts_with_fallback


class _FakeTTS:
    def __init__(self) -> None:
        self._calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self._should_raise = False

    def stream_audio(self, text: str, *args: Any, **kwargs: Any) -> Any:
        self._calls.append((text, args, kwargs))
        if self._should_raise:
            raise RuntimeError("rate limited")
        return b"ok"


def test_wrap_tts_with_fallback_records_and_falls_back(monkeypatch) -> None:
    # Prepare session and tracker
    session_id = "test-session-fallback"
    session = GameSession(id=session_id, stream_call_id=f"pickup-{session_id}")
    sessions[session_id] = session
    tracker = CommentaryTracker()

    # Use a local hub so we can introspect published payloads without touching globals.
    hub = CommentaryHub()
    published: list[dict[str, Any]] = []

    # Monkeypatch publish_nowait to record synchronously for the test.
    def _publish_nowait(sid: str, payload: dict[str, Any]) -> None:
        published.append({"session_id": sid, **payload})

    import services.tts_fallback as tts_fallback_module
    monkeypatch.setattr(tts_fallback_module, "commentary_hub", hub, raising=True)
    monkeypatch.setattr(hub, "publish_nowait", _publish_nowait, raising=True)

    tts = _FakeTTS()
    tts._should_raise = True

    wrap_tts_with_fallback(
        tts,
        session_id_provider=lambda: session_id,
        tracker=tracker,
    )

    # Calling stream_audio() should:
    #   - not propagate the exception (returns None instead)
    #   - record a commentary entry on the session
    #   - publish a fallback payload to the commentary hub
    result = tts.stream_audio("UNBELIEVABLE buzzer-beater at the horn!")
    assert result is None

    assert len(session.commentary_log) == 1
    entry = session.commentary_log[0]
    assert entry.is_highlight is True

    assert len(published) >= 1, "Expected a fallback payload to be published"
    payload = published[-1]
    assert payload["session_id"] == session_id
    assert "text" in payload and "energy_level" in payload and "is_highlight" in payload
    assert payload["text"].startswith("UNBELIEVABLE")
    assert payload["is_highlight"] is True


class _FakeAsyncTTS:
    def __init__(self, should_raise: bool) -> None:
        self._should_raise = should_raise

    async def stream_audio(self, text: str, *args: Any, **kwargs: Any) -> Any:
        if self._should_raise:
            raise RuntimeError("async rate limited")
        return b"ok-async"


def test_wrap_tts_with_fallback_handles_async_stream_audio_errors(monkeypatch) -> None:
    session_id = "test-session-async-fallback"
    session = GameSession(id=session_id, stream_call_id=f"pickup-{session_id}")
    sessions[session_id] = session
    tracker = CommentaryTracker()

    hub = CommentaryHub()
    published: list[dict[str, Any]] = []

    def _publish_nowait(sid: str, payload: dict[str, Any]) -> None:
        published.append({"session_id": sid, **payload})

    import services.tts_fallback as tts_fallback_module
    monkeypatch.setattr(tts_fallback_module, "commentary_hub", hub, raising=True)
    monkeypatch.setattr(hub, "publish_nowait", _publish_nowait, raising=True)

    tts = _FakeAsyncTTS(should_raise=True)
    wrap_tts_with_fallback(
        tts,
        session_id_provider=lambda: session_id,
        tracker=tracker,
    )

    import asyncio
    result = asyncio.run(tts.stream_audio("What an explosive final minute!"))
    assert result is None
    assert len(session.commentary_log) == 1
    assert published[-1]["session_id"] == session_id


class _FakeSendTTS:
    def stream_audio(self, text: str, *args: Any, **kwargs: Any) -> Any:
        return b"ok"

    async def send(self, text: str, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("concurrent_limit_exceeded")


def test_wrap_tts_with_fallback_wraps_send_and_publishes_on_send_failure(monkeypatch) -> None:
    session_id = "test-session-send-fallback"
    session = GameSession(id=session_id, stream_call_id=f"pickup-{session_id}")
    sessions[session_id] = session
    tracker = CommentaryTracker()

    hub = CommentaryHub()
    published: list[dict[str, Any]] = []

    def _publish_nowait(sid: str, payload: dict[str, Any]) -> None:
        published.append({"session_id": sid, **payload})

    import services.tts_fallback as tts_fallback_module
    monkeypatch.setattr(tts_fallback_module, "commentary_hub", hub, raising=True)
    monkeypatch.setattr(hub, "publish_nowait", _publish_nowait, raising=True)

    tts = _FakeSendTTS()
    wrap_tts_with_fallback(
        tts,
        session_id_provider=lambda: session_id,
        tracker=tracker,
    )

    # Record commentary text so send() fallback has context, then trigger send failure.
    tts.stream_audio("What a huge momentum swing!")

    import asyncio
    result = asyncio.run(tts.send("ignored by fallback"))
    assert result is None
    assert len(published) >= 1
    assert published[-1]["session_id"] == session_id
