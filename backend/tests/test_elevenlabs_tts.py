from __future__ import annotations

import os
import pytest
from vision_agents.core.events import EventManager
from agent import create_agent

class _FakeVLM:
    """Fake gemini.VLM for tests."""
    def __init__(self, *, model: str = "", fps: int = 1, api_key: str | None = None, **_: object) -> None:
        self.model = model
        self.fps = fps
        self.api_key = api_key
        self.events = EventManager()

    def _attach_agent(self, _agent: object) -> None:
        return None

class _FakeTTS:
    """Fake elevenlabs.TTS for tests."""
    def __init__(self, api_key: str | None = None, voice_id: str = "", **_: object) -> None:
        self.api_key = api_key
        self.voice_id = voice_id
        self.events = EventManager()
    
    def synthesize(self, text: str) -> bytes:
        return b"fake_audio"

@pytest.mark.anyio
async def test_create_agent_uses_separate_vlm_and_tts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that the agent uses separate Gemini VLM and ElevenLabs TTS (Sprint 4)."""
    created_llms: list[_FakeVLM] = []
    created_tts: list[_FakeTTS] = []

    def _fake_vlm(**kwargs: object) -> _FakeVLM:
        llm = _FakeVLM(**kwargs)  # type: ignore[arg-type]
        created_llms.append(llm)
        return llm

    def _fake_tts(**kwargs: object) -> _FakeTTS:
        tts = _FakeTTS(**kwargs)  # type: ignore[arg-type]
        created_tts.append(tts)
        return tts

    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")
    monkeypatch.setenv("ROBOFLOW_API_KEY", "test-roboflow-key")

    import agent as agent_module
    monkeypatch.setattr(agent_module.gemini, "VLM", _fake_vlm, raising=True)
    monkeypatch.setattr(agent_module.elevenlabs, "TTS", _fake_tts, raising=True)

    agent = await create_agent()

    # Verify VLM
    assert len(created_llms) == 1
    llm = created_llms[0]
    assert llm.model == "gemini-3-flash-preview"
    assert llm.fps == 3

    # Verify TTS
    assert len(created_tts) == 1
    tts = created_tts[0]
    assert tts.api_key == "test-elevenlabs-key"
    assert tts.voice_id == "Chris"

    # Verify Agent has tts configured
    assert agent.tts is not None
    # Agent.tts might be wrapped by our fallback wrapper, but it should still be there.
    assert hasattr(agent.tts, "synthesize")
