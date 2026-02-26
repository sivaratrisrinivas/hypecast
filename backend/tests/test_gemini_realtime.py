from __future__ import annotations

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


class _FakeEdge:
    pass


class _FakeAgentObject:
    def __init__(self, **kwargs: object) -> None:
        self.tts = kwargs.get("tts")
        self.processors = kwargs.get("processors")
        self.instructions = kwargs.get("instructions")

@pytest.mark.asyncio
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
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")

    import agent as agent_module
    monkeypatch.setattr(agent_module.gemini, "VLM", _fake_vlm, raising=True)
    monkeypatch.setattr(agent_module.getstream, "Edge", _FakeEdge, raising=True)
    monkeypatch.setattr(agent_module, "Agent", _FakeAgentObject, raising=True)

    agent = await create_agent()

    assert len(created_llms) == 1
    llm = created_llms[0]
    assert llm.fps == 3
    assert llm.model == "gemini-3-flash-preview"

    assert agent.instructions == ESPN_SYSTEM_PROMPT
