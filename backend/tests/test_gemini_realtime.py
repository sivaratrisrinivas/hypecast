from __future__ import annotations

import os

import pytest
from vision_agents.core.events import EventManager

from agent import ESPN_SYSTEM_PROMPT, create_agent


class _FakeRealtime:
    def __init__(self, *, model: str, fps: int, api_key: str | None = None, **_: object) -> None:
        self.model = model
        self.fps = fps
        self.api_key = api_key
        self.connected = False
        self.events = EventManager()

    async def connect(self) -> None:
        self.connected = True

    def _attach_agent(self, _agent: object) -> None:
        # Real implementations use this to wire callbacks; no-op for this test.
        return None


@pytest.mark.anyio
async def test_create_agent_uses_gemini_realtime_with_espn_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    created_llms: list[_FakeRealtime] = []

    def _fake_realtime(**kwargs: object) -> _FakeRealtime:
        llm = _FakeRealtime(**kwargs)  # type: ignore[arg-type]
        created_llms.append(llm)
        return llm

    # Ensure GOOGLE_API_KEY is present so create_agent does not raise.
    monkeypatch.setenv("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY", "test-key"))
    # Avoid needing a real ElevenLabs key for this test.
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    # Patch gemini.Realtime constructor used inside agent.create_agent.
    import agent as agent_module

    monkeypatch.setattr(agent_module.gemini, "Realtime", _fake_realtime, raising=True)

    agent = await create_agent()

    # Our fake Realtime should have been constructed exactly once.
    assert len(created_llms) == 1
    llm = created_llms[0]
    assert llm.model == "gemini-2.5-flash"
    assert llm.fps == 3
    # api_key should be wired through from env; value may vary per environment.
    assert isinstance(llm.api_key, str)
    assert llm.api_key != ""

    # Agent should be configured with the strict ESPN commentator system prompt.
    assert getattr(agent.instructions, "input_text", None) == ESPN_SYSTEM_PROMPT

