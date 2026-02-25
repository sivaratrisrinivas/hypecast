from __future__ import annotations

import os

import pytest
from vision_agents.core.events import EventManager

from agent import create_agent


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


class _FakeTTS:
    def __init__(
        self,
        *,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        api_key: str | None = None,
        **_: object,
    ) -> None:
        self.voice_id = voice_id
        self.model_id = model_id
        self.api_key = api_key
        self._chunks: list[str] = []
        self.events = EventManager()

    def synthesize(self, text: str) -> bytes:
        """Simulate TTS synthesis: record text and return fake audio bytes."""
        self._chunks.append(text)
        return b"fake-audio-bytes"


@pytest.mark.anyio
async def test_create_agent_wires_elevenlabs_tts_with_chris_voice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_tts: list[_FakeTTS] = []

    def _fake_realtime(**kwargs: object) -> _FakeRealtime:
        return _FakeRealtime(**kwargs)  # type: ignore[arg-type]

    def _fake_tts(**kwargs: object) -> _FakeTTS:
        tts = _FakeTTS(**kwargs)  # type: ignore[arg-type]
        created_tts.append(tts)
        return tts

    # Ensure GOOGLE_API_KEY is present so create_agent does not raise.
    monkeypatch.setenv("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY", "test-google-key"))
    # Provide a dummy ElevenLabs API key so the TTS plugin is instantiated.
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-eleven-key")
    # Ensure default voice ("Chris") is used when ELEVENLABS_VOICE_ID is not set.
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)

    import agent as agent_module

    # Patch gemini.Realtime and elevenlabs.TTS used inside agent.create_agent.
    monkeypatch.setattr(agent_module.gemini, "Realtime", _fake_realtime, raising=True)
    monkeypatch.setattr(agent_module.elevenlabs, "TTS", _fake_tts, raising=True)

    agent = await create_agent()

    # Our fake TTS should have been constructed exactly once.
    assert len(created_tts) == 1
    tts = created_tts[0]
    assert tts.voice_id == "Chris"
    # API key should be wired through from env; value may vary per environment.
    assert isinstance(tts.api_key, str)
    assert tts.api_key != ""

    # Agent should be configured with streaming TTS enabled and use our fake TTS instance.
    assert agent.tts is tts  # type: ignore[attr-defined]
    assert getattr(agent, "streaming_tts", False) is True

    # Simulate Gemini emitting a text chunk and ensure the TTS handler produces audio bytes.
    audio = tts.synthesize("UNBELIEVABLE shot from the corner!")
    assert isinstance(audio, (bytes, bytearray))
    assert len(audio) > 0
    assert tts._chunks == ["UNBELIEVABLE shot from the corner!"]

