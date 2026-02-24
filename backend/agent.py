from __future__ import annotations

import logging
from typing import Any

from dotenv import load_dotenv
from vision_agents.core import Agent, AgentLauncher, Runner, ServeOptions, User

from app.main import app

load_dotenv()
logging.basicConfig(level=logging.INFO)


async def create_agent(**kwargs: Any) -> Agent:
    """
    Factory for the Vision Agents `Agent`.

    NOTE: For Sprint 3.1 we only need the HTTP runner wiring in place.
    The concrete agent (edge transport, LLM, TTS, etc.) will be wired
    in during later Sprint 3/4 tasks.
    """
    raise NotImplementedError(
        "Agent factory will be implemented in Sprint 3.2+ when wiring the full pipeline.",
    )


async def join_call(agent: Agent, call_type: str, call_id: str, **kwargs: Any) -> None:
    """
    Called when the agent should join a call.

    This will be implemented in later sprints once `create_agent` is
    configured with the Stream edge transport and commentary pipeline.
    """
    raise NotImplementedError(
        "join_call will be implemented in Sprint 3.2+ when enabling agent call joins.",
    )


runner = Runner(
    AgentLauncher(
        create_agent=create_agent,
        join_call=join_call,
        max_concurrent_sessions=1,
        max_sessions_per_call=1,
        max_session_duration_seconds=300,
    ),
    # Reuse the FastAPI app from Sprint 2 so `/api/*` and `/health`
    # remain available under the same server as the Vision Agents runner.
    serve_options=ServeOptions(fast_api=app),
)


if __name__ == "__main__":
    runner.cli()

