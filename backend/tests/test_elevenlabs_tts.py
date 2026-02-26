from __future__ import annotations

import pytest
from vision_agents.core.events import EventManager
from agent import create_agent


class _FakeRealtime:
    """Fake gemini.Realtime for tests."""

    def __init__(
        self,
        *,
        model: str = "",
        fps: int = 1,
        api_key: str | None = None,
        **_: object,
    ) -> None:
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


class _FakeTTS:
    """Fake elevenlabs.TTS for tests."""

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str = "",
        **_: object,
    ) -> None:
        self.api_key = api_key
        self.voice_id = voice_id
        self.events = EventManager()

    def synthesize(self, text: str) -> bytes:
        return b"fake_audio"

    def stream_audio(self, text: str):
        return b"fake_audio"


@pytest.mark.asyncio
async def test_create_agent_uses_realtime_and_tts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify agent uses gemini.Realtime + elevenlabs.TTS + RFDETRProcessor."""
    created_llms: list[_FakeRealtime] = []
    created_tts: list[_FakeTTS] = []

    def _fake_realtime(**kwargs: object) -> _FakeRealtime:
        llm = _FakeRealtime(**kwargs)  # type: ignore[arg-type]
        created_llms.append(llm)
        return llm

    def _fake_tts(**kwargs: object) -> _FakeTTS:
        tts = _FakeTTS(**kwargs)  # type: ignore[arg-type]
        created_tts.append(tts)
        return tts

    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")

    import agent as agent_module

    monkeypatch.setattr(
        agent_module.gemini, "Realtime", _fake_realtime, raising=True
    )
    monkeypatch.setattr(
        agent_module.getstream, "Edge", _FakeEdge, raising=True
    )
    monkeypatch.setattr(
        agent_module, "Agent", _FakeAgentObject, raising=True
    )
    monkeypatch.setattr(
        agent_module.elevenlabs, "TTS", _fake_tts, raising=True
    )

    agent = await create_agent()

    # Verify Realtime LLM
    assert len(created_llms) == 1
    llm = created_llms[0]
    assert llm.fps == 3

    # Verify TTS
    assert len(created_tts) == 1
    tts = created_tts[0]
    assert tts.api_key == "test-elevenlabs-key"
    assert tts.voice_id == "Anr9GtYh2VRXxiPplzxM"

    # Verify Agent has tts configured
    assert agent.tts is not None
    assert hasattr(agent.tts, "stream_audio")

    # RF-DETR processor should be in the list
    from services.rfdetr_detection import RFDetrDetectionProcessor

    assert any(
        isinstance(p, RFDetrDetectionProcessor)
        for p in agent.processors
    )
