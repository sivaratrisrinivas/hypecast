from __future__ import annotations

import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from vision_agents.core import Agent, AgentLauncher, Runner, User
from vision_agents.plugins import elevenlabs, gemini, getstream

from app.main import app as api_app

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

    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        logging.warning("GOOGLE_API_KEY not set; Gemini Realtime will not be able to connect.")

    eleven_api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not eleven_api_key:
        logging.warning("ELEVENLABS_API_KEY not set; ElevenLabs TTS will not output audio.")

    # Stream Edge reads STREAM_API_KEY / STREAM_API_SECRET from env
    edge = getstream.Edge()

    llm = gemini.Realtime(
        model="gemini-2.5-flash",
        fps=3,
        api_key=google_api_key,
    )

    tts = elevenlabs.TTS(
        api_key=eleven_api_key,
        voice_id="Anr9GtYh2VRXxiPplzxM",
    )

    # Roboflow optional: vision-agents-plugins-roboflow conflicts with getstream's aiohttp;
    # add it when the ecosystem resolves. Until then, commentary works without object detection.
    processors: list[Any] = []
    try:
        from vision_agents.plugins import roboflow
        roboflow_processor = roboflow.RoboflowLocalDetectionProcessor(
            model_id="rfdetr-base",
            fps=5,
            conf_threshold=0.5,
            classes=["person", "sports ball"],
            annotate=False,
        )
        processors.append(roboflow_processor)
    except (ImportError, AttributeError) as e:
        logging.warning("Roboflow processor unavailable (optional): %s", e)

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

    # Join call and run until completion.
    connection = await agent.edge.join(agent, call)
    logging.info("[join_call] Agent joined call; waiting for call to end.")

    try:
        await connection.wait()
    finally:
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

# Mount the existing FastAPI app under `/api` on the Vision Agents runner app.
# The app's routes are defined WITHOUT an /api prefix (see routes/sessions.py);
# mounting at /api exposes them as /api/sessions, /api/health, etc.
runner.fast_api.mount("/api", api_app)
for route in api_app.routes:
    if hasattr(route, "path") and hasattr(route, "methods"):
        logging.info("App route: %s %s", list(route.methods) if route.methods else "GET", route.path)


if __name__ == "__main__":
    runner.cli()

