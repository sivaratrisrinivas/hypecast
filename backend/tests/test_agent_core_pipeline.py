from __future__ import annotations

import pytest

from agent import join_call
from models.session import GameSession
from models.session import SessionStatus
from services.store import sessions


class _FakeCall:
    pass


class _FakeJoinContext:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeAgent:
    def __init__(self) -> None:
        self.processors = []
        self._session_id = None
        self.create_user_called = False
        self.create_call_args: tuple[str, str] | None = None
        self.simple_response_text: str | None = None
        self.finish_called = False
        self.subscribed = False

    async def create_user(self) -> None:
        self.create_user_called = True

    async def create_call(self, call_type: str, call_id: str):
        self.create_call_args = (call_type, call_id)
        return _FakeCall()

    def subscribe(self, _fn):
        self.subscribed = True

    def join(self, _call):
        return _FakeJoinContext()

    async def simple_response(self, text: str) -> None:
        self.simple_response_text = text

    async def finish(self) -> None:
        self.finish_called = True


@pytest.mark.asyncio
async def test_join_call_applies_warmup_and_marks_session_live(monkeypatch: pytest.MonkeyPatch) -> None:
    session_id = "warmup-session"
    sessions[session_id] = GameSession(id=session_id, stream_call_id=f"pickup-{session_id}")

    slept: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setenv("AGENT_STARTUP_WARMUP_SECONDS", "2")
    monkeypatch.setattr("agent.asyncio.sleep", _fake_sleep, raising=True)

    fake_agent = _FakeAgent()
    await join_call(fake_agent, "default", f"pickup-{session_id}")

    assert fake_agent._session_id == session_id
    assert fake_agent.create_user_called is True
    assert fake_agent.create_call_args == ("default", f"pickup-{session_id}")
    assert fake_agent.simple_response_text is not None
    assert fake_agent.finish_called is True
    assert sessions[session_id].status == SessionStatus.LIVE
    assert slept == [2.0]
