from __future__ import annotations

import os
import pytest
from vision_agents.core.events import EventManager
from agent import ESPN_SYSTEM_PROMPT, create_agent

class _FakeVLM:
    """Fake gemini.VLM for tests."""
    def __init__(self, *, model: str = "", fps: int = 1, api_key: str | None = None, **_: object) -> None:
        self.model = model
        self.fps = fps
        self.api_key = api_key
        self.events = EventManager()

    def _attach_agent(self, _agent: object) -> None:
        return None

@pytest.mark.anyio
async def test_create_agent_uses_gemini_vlm_with_espn_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that the agent uses Gemini VLM with the correct system prompt (Sprint 4.2)."""
    created_llms: list[_FakeVLM] = []

    def _fake_vlm(**kwargs: object) -> _FakeVLM:
        llm = _FakeVLM(**kwargs)  # type: ignore[arg-type]
        created_llms.append(llm)
        return llm

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("ROBOFLOW_API_KEY", "test-roboflow-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")

    import agent as agent_module
    monkeypatch.setattr(agent_module.gemini, "VLM", _fake_vlm, raising=True)

    agent = await create_agent()

    assert len(created_llms) == 1
    llm = created_llms[0]
    assert llm.fps == 3
    assert llm.model == "gemini-3-flash-preview"

    # In Sprint 4.2+, Agent.instructions holds the prompt
    assert getattr(agent.instructions, "input_text", None) == ESPN_SYSTEM_PROMPT
