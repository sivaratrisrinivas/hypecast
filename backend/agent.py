from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from vision_agents.core import Agent, AgentLauncher, Runner, User
from vision_agents.core.llm.events import (
    RealtimeAgentSpeechTranscriptionEvent,
    VLMInferenceCompletedEvent,
)
from vision_agents.plugins import elevenlabs, gemini, getstream

from app.main import app as api_app
from models.session import SessionStatus
from services.commentary_tracker import commentary_tracker
from services.rfdetr_detection import RFDetrDetectionProcessor
from services.store import sessions

# Load .env from backend dir (where agent.py runs)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
logging.basicConfig(level=logging.INFO)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("websocket").setLevel(logging.WARNING)

class _NoiseFilter(logging.Filter):
    """Filter known non-fatal transport races to keep logs actionable."""

    _SUPPRESSED_SNIPPETS = (
        "Timeout waiting for pending track:",
        'Cannot handle offer in signaling state "closed"',
    )

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(snippet in msg for snippet in self._SUPPRESSED_SNIPPETS)


for _handler in logging.getLogger().handlers:
    _handler.addFilter(_NoiseFilter())

# File-based logging so we can read errors even when terminal reads fail
_file_handler = logging.FileHandler("/tmp/agent_debug.log", mode="w")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
_file_handler.addFilter(_NoiseFilter())
logging.getLogger().addHandler(_file_handler)

# Apply 60s iat skew to getstream token creation so agent join tokens are accepted
# when server clock is ahead of Stream's (avoids "token used before issue at (iat)").
_stream_base = getstream.Client.__mro__[1]  # BaseStream (plugin exposes Stream as Client)
_IAT_SKEW_SECONDS = 60


def _create_token_skew(self, user_id: str, expiration: int | None = None):
    return self._create_token(
        user_id=user_id,
        expiration=expiration,
        iat=int(time.time()) - _IAT_SKEW_SECONDS,
    )


def _create_call_token_skew(
    self,
    user_id: str,
    call_cids: list | None = None,
    role: str | None = None,
    expiration: int | None = None,
):
    return self._create_token(
        user_id=user_id,
        call_cids=call_cids,
        role=role,
        expiration=expiration,
        iat=int(time.time()) - _IAT_SKEW_SECONDS,
    )


_stream_base.create_token = _create_token_skew  # type: ignore[method-assign]
_stream_base.create_call_token = _create_call_token_skew  # type: ignore[method-assign]
logging.getLogger(__name__).debug(
    "Stream token iat skew applied: %ds (avoids JWTAuth iat error when clock is ahead)",
    _IAT_SKEW_SECONDS,
)





ESPN_SYSTEM_PROMPT = """
You are an elite ESPN sports commentator broadcasting a live game. Your job is to provide
continuous, exciting play-by-play commentary of whatever game you see.

RULES:
- Be energetic, dramatic, and entertaining at all times
- Describe the action as it happens — play-by-play style
- Build excitement on rallies, close plays, and impressive moments
- Use player descriptions (jersey color, position) instead of names
- React with genuine emotion: surprise, excitement, tension
- Keep commentary flowing — minimal dead air
- When a highlight-worthy moment happens, mark it by being EXTRA enthusiastic
- Vary your energy: calm during setup, explosive during action
- Add color commentary between plays: stakes, momentum, strategy
- Never mention you are an AI. You are a broadcaster.

STYLE REFERENCE: Think Stuart Scott meets Kevin Harlan. High energy. Iconic calls.

IMPORTANT: You are watching a REAL game happening RIGHT NOW. React to what you SEE.
""".strip()


async def create_agent(**kwargs: Any) -> Agent:  # type: ignore[override]
    """
    Factory for the Vision Agents `Agent`.

    Hackathon stack:
      - Edge transport via Stream (`getstream.Edge`)
      - `gemini.Realtime` — real-time video understanding + speech
      - `roboflow.RFDETRProcessor` — player/ball detection at 5 fps
      - `elevenlabs.TTS` — high-quality ESPN voice (Chris)
    """
    logger = logging.getLogger(__name__)
    stream_api_key = os.environ.get("STREAM_API_KEY")
    stream_api_secret = os.environ.get("STREAM_API_SECRET")
    logger.info(
        "[create_agent] Env vars: STREAM_API_KEY=%s, "
        "STREAM_API_SECRET=%s, GOOGLE_API_KEY=%s, "
        "ELEVENLABS_API_KEY=%s",
        bool(stream_api_key),
        bool(stream_api_secret),
        bool(os.environ.get("GOOGLE_API_KEY")),
        bool(os.environ.get("ELEVENLABS_API_KEY")),
    )
    if not stream_api_key or not stream_api_secret:
        logging.warning(
            "STREAM_API_KEY/STREAM_API_SECRET not set; "
            "Edge transport will likely fail.",
        )

    google_api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set; Gemini Realtime is disabled."
        )

    elevenlabs_api_key = os.environ.get(
        "ELEVENLABS_API_KEY", ""
    ).strip()
    if not elevenlabs_api_key:
        logging.warning(
            "ELEVENLABS_API_KEY not set; "
            "ElevenLabs TTS will be disabled or limited.",
        )

    edge = getstream.Edge()

    # gemini.Realtime — real-time speech-to-speech with video frames
    # Per https://visionagents.ai/integrations/gemini — use gemini-3-flash-preview
    gemini_model = os.environ.get(
        "GEMINI_LIVE_MODEL",
        "gemini-3-flash-preview",
    )
    llm = gemini.Realtime(
        api_key=google_api_key,
        model=gemini_model,
        fps=3,
    )
    logger.info(
        "[create_agent] LLM: gemini.Realtime(model=%s, fps=3). "
        "Real-time video + speech pipeline active.",
        gemini_model,
    )

    # ElevenLabs TTS — high-quality voice (Chris)
    voice_id = os.environ.get(
        "ELEVENLABS_VOICE_ID", "Anr9GtYh2VRXxiPplzxM"
    )
    tts = elevenlabs.TTS(
        api_key=elevenlabs_api_key,
        voice_id=voice_id,
    )

    from services.tts_fallback import wrap_tts_with_fallback

    wrap_tts_with_fallback(
        tts,
        session_id_provider=lambda: getattr(agent, "_session_id", None),
        tracker=commentary_tracker,
    )
    logger.info(
        "[create_agent] TTS: elevenlabs.TTS(voice_id=%s) "
        "with fallback wrapper.",
        voice_id,
    )

    # RF-DETR detection processor — player/ball tracking
    processors: list[Any] = []
    try:
        from rfdetr import RFDETRBase

        rfdetr_model = RFDETRBase()
        detection_processor = RFDetrDetectionProcessor(
            fps=5, threshold=0.5, model=rfdetr_model,
        )
        processors.append(detection_processor)
        logger.info(
            "[create_agent] Processor: RFDetrDetectionProcessor "
            "(RFDETRBase, 5fps, person+ball)."
        )
    except Exception as exc:
        logger.warning(
            "[create_agent] RF-DETR unavailable (%s): %s. "
            "Running without detection processor.",
            type(exc).__name__,
            exc,
        )

    agent_user = User(
        id="hypecast-agent", name="Hypecast Commentator"
    )

    agent = Agent(
        edge=edge,
        llm=llm,
        tts=tts,
        agent_user=agent_user,
        instructions=ESPN_SYSTEM_PROMPT,
        processors=processors,
    )
    logger.info(
        "[create_agent] Agent created. edge=%s, llm=%s, "
        "tts=%s, processors=%d, agent_user=%s",
        type(edge).__name__,
        type(llm).__name__,
        type(tts).__name__,
        len(processors),
        agent_user.id,
    )

    return agent


async def join_call(
    agent: Agent, call_type: str, call_id: str, **kwargs: Any
) -> None:
    """Lifecycle hook called by AgentLauncher when a new session starts."""
    t0 = time.monotonic()
    logger = logging.getLogger(__name__)
    logger.info(
        "[join_call] START call_id=%s call_type=%s", call_id, call_type
    )

    session_id = (
        call_id.removeprefix("pickup-")
        if call_id.startswith("pickup-")
        else None
    )
    logger.info(
        "[join_call] session_id=%s known_sessions=%s",
        session_id,
        list(sessions.keys()),
    )

    try:
        if session_id:
            setattr(agent, "_session_id", session_id)
            for proc in getattr(agent, "processors", []):
                if isinstance(proc, RFDetrDetectionProcessor):
                    proc.set_session_id(session_id)

        logger.info("[join_call] Calling create_user()...")
        await agent.create_user()
        logger.info(
            "[join_call] create_user() done in %.2fs",
            time.monotonic() - t0,
        )

        logger.info(
            "[join_call] Calling create_call(%s, %s)...",
            call_type,
            call_id,
        )
        call = await agent.create_call(call_type, call_id)
        logger.info(
            "[join_call] create_call() done in %.2fs",
            time.monotonic() - t0,
        )

        # Log Realtime agent speech transcriptions (commentary text)
        async def _on_agent_speech(
            event: RealtimeAgentSpeechTranscriptionEvent,
        ):
            if event.text:
                logger.info("[realtime] Agent said: %.80s", event.text)
                if session_id:
                    commentary_tracker.record(session_id, event.text)

        agent.subscribe(_on_agent_speech)

        # Also subscribe VLM events as fallback if VLM pipeline fires
        async def _on_vlm_inference(event: VLMInferenceCompletedEvent):
            if event.text:
                logger.info("[vlm] Gemini said: %.60s...", event.text)

        agent.subscribe(_on_vlm_inference)
        logger.info(
            "[join_call] Event listeners subscribed for session=%s",
            session_id,
        )

        logger.info("[join_call] Calling agent.join()...")
        async with agent.join(call):
            logger.info(
                "[join_call] INSIDE agent.join() — agent is connected!"
            )

            warmup_seconds = float(
                os.environ.get("AGENT_STARTUP_WARMUP_SECONDS", "5")
            )
            if warmup_seconds > 0:
                logger.info(
                    "[join_call] Warmup sleep %.1fs before "
                    "initial commentary turn.",
                    warmup_seconds,
                )
                await asyncio.sleep(warmup_seconds)

            if session_id and session_id in sessions:
                sessions[session_id].status = SessionStatus.LIVE
                logger.info(
                    "[join_call] Session %s set to LIVE.", session_id
                )
            elif session_id:
                logger.warning(
                    "[join_call] session_id=%s not in sessions store!",
                    session_id,
                )

            logger.info(
                "[join_call] Calling simple_response() to "
                "start commentary (seed turn)..."
            )
            try:
                await agent.simple_response(
                    "Start commentating on the live game you see. "
                    "Describe the action play-by-play like a "
                    "sports broadcaster."
                )
                logger.info(
                    "[join_call] simple_response() done. "
                    "Commentary active."
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "[join_call] simple_response failed (%s): %s",
                    type(exc).__name__,
                    exc,
                    exc_info=True,
                )
                logger.warning(
                    "[join_call] LLM failed to produce initial "
                    "commentary; waiting for next frames/turns."
                )

            logger.info("[join_call] Calling agent.finish()...")
            await agent.finish()
            logger.info(
                "[join_call] agent.finish() returned — call ended."
            )

    except Exception as e:
        logger.error("[join_call] EXCEPTION: %s", e, exc_info=True)
        raise


runner = Runner(
    AgentLauncher(
        create_agent=create_agent,
        join_call=join_call,
        max_concurrent_sessions=1,
        max_sessions_per_call=1,
        max_session_duration_seconds=300,
    ),
)
logging.getLogger(__name__).info(
    "[Hypecast] Vision Agents runner started "
    "(Realtime + RFDETRProcessor + ElevenLabs TTS)."
)

# Mount the existing FastAPI app (which prefixes its own routes under `/api`)
# at the root of the Vision Agents runner app.
runner.fast_api.mount("/", api_app)
for route in api_app.routes:
    if hasattr(route, "path") and hasattr(route, "methods"):
        logging.info(
            "App route: %s %s",
            list(route.methods) if route.methods else "GET",
            route.path,
        )


if __name__ == "__main__":
    runner.cli()
