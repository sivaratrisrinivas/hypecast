from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from vision_agents.core import Agent, AgentLauncher, Runner, User
from vision_agents.core.edge.events import CallEndedEvent
from vision_agents.plugins import elevenlabs, gemini, getstream

from app.main import app as api_app
from models.session import SessionStatus
from services.frame_capture import FrameCaptureProcessor
from services.rfdetr_detection import RFDetrDetectionProcessor
from services.store import sessions

# Load .env from backend dir (where agent.py runs)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
logging.basicConfig(level=logging.INFO)

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

    This wires the real pipeline:
      - Edge transport via Stream (`getstream.Edge`)
      - Gemini Realtime vision LLM
      - ElevenLabs TTS
      - Roboflow local detection processor
    """
    stream_api_key = os.environ.get("STREAM_API_KEY")
    stream_api_secret = os.environ.get("STREAM_API_SECRET")
    if not stream_api_key or not stream_api_secret:
        logging.warning(
            "STREAM_API_KEY/STREAM_API_SECRET not set; Edge transport will likely fail.",
        )

    google_api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Set it in backend/.env or the environment. "
            "Without it the agent will spam 'Gemini Session is not established' and produce no commentary."
        )

    eleven_api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not eleven_api_key:
        logging.warning("ELEVENLABS_API_KEY not set; ElevenLabs TTS will not output audio.")
    eleven_voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "Chris")

    # Stream Edge reads STREAM_API_KEY / STREAM_API_SECRET from env
    edge = getstream.Edge()

    # Gemini Realtime text model; audio is handled by ElevenLabs TTS (Sprint 4.3).
    # See https://visionagents.ai/integrations/gemini for reference.
    llm = gemini.Realtime(
        model="gemini-2.5-flash",
        fps=3,
        api_key=google_api_key,
    )

    tts = elevenlabs.TTS(
        api_key=eleven_api_key,
        voice_id=eleven_voice_id,
    )

    # Frame capture: save incoming WebRTC frames to GCS raw.webm (path set in join_call).
    frame_capture = FrameCaptureProcessor(fps=15)
    detection = RFDetrDetectionProcessor(fps=5, threshold=0.5)
    processors: list[Any] = [frame_capture, detection]

    agent_user = User(id="hypecast-agent", name="Hypecast Commentator")

    agent = Agent(
        edge=edge,
        llm=llm,
        tts=tts,
        agent_user=agent_user,
        instructions=ESPN_SYSTEM_PROMPT,
        processors=processors,
        streaming_tts=True,
        broadcast_metrics=True,
    )

    return agent


async def join_call(agent: Agent, call_type: str, call_id: str, **kwargs: Any) -> None:
    """
    Called when the agent should join a call.

    This function:
      - Creates/joins the Stream call via Edge
      - Joins the call with the Agent
      - Runs until the call ends, then cleans up
    """
    logging.info("[join_call] Joining call_id=%s call_type=%s", call_id, call_type)

    # Register the agent user with Stream and set edge.agent_user_id so create_call can send created_by_id.
    await agent.create_user()
    # Create or fetch the Stream call via Edge (requires agent_user_id for server-side auth).
    call = await agent.edge.create_call(call_id=call_id, call_type=call_type)  # type: ignore[arg-type]

    # Set GCS path for frame capture before join so raw.webm is written to sessions/{session_id}/raw.webm.
    session_id = call_id.removeprefix("pickup-") if call_id.startswith("pickup-") else None
    if session_id:
        for p in agent.processors:
            if isinstance(p, FrameCaptureProcessor):
                p.set_output_blob_path(f"sessions/{session_id}/raw.webm")
                break
        for p in agent.processors:
            if isinstance(p, RFDetrDetectionProcessor):
                p.set_session_id(session_id)
                break

    # Establish Gemini (or other Realtime LLM) session before edge.join().
    # The agent's normal join() does llm.connect() then edge.join(); we must do the same or
    # video frames are sent before _real_session exists and we get "Gemini Session is not established yet".
    if hasattr(agent.llm, "connect") and callable(agent.llm.connect):
        await agent.llm.connect()
        logging.info("[join_call] Realtime LLM connected.")

    # Join call and run until completion.
    # StreamConnection has no .wait(); we wait for CallEndedEvent from the edge instead.
    connection = await agent.edge.join(agent, call)
    # Mark app session LIVE so frontend polling stops showing "Awaiting connection...".
    if session_id and session_id in sessions:
        sessions[session_id].status = SessionStatus.LIVE
        logging.info("[join_call] Session %s set to LIVE.", session_id)
    logging.info("[join_call] Agent joined call; waiting for call to end.")

    call_ended = asyncio.Event()
    max_wait = 300.0  # match max_session_duration_seconds

    async def on_call_ended(_event: CallEndedEvent):
        call_ended.set()

    agent.edge.events.subscribe(on_call_ended)
    try:
        try:
            await asyncio.wait_for(call_ended.wait(), timeout=max_wait)
        except asyncio.TimeoutError:
            logging.info("[join_call] Max session duration reached; ending call.")
    finally:
        agent.edge.events.unsubscribe(on_call_ended)
        logging.info("[join_call] Call finished; closing agent and edge transport.")
        await agent.close()


runner = Runner(
    AgentLauncher(
        create_agent=create_agent,
        join_call=join_call,
        max_concurrent_sessions=1,
        max_sessions_per_call=1,
        max_session_duration_seconds=300,
    ),
)

# Mount the existing FastAPI app (which prefixes its own routes under `/api`)
# at the root of the Vision Agents runner app.
runner.fast_api.mount("/", api_app)
for route in api_app.routes:
    if hasattr(route, "path") and hasattr(route, "methods"):
        logging.info("App route: %s %s", list(route.methods) if route.methods else "GET", route.path)


if __name__ == "__main__":
    runner.cli()

