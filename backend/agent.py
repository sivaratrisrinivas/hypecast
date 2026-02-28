"""Vision Agents runner wrapper for HypeCast.

This keeps FastAPI app mounted while enabling live sessions when secrets are set.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from vision_agents.core import Agent, AgentLauncher, Runner, User
from vision_agents.plugins import elevenlabs, gemini, getstream

from app.main import app as api_app

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ESPN_SYSTEM_PROMPT = """
You are an elite ESPN sports commentator. Keep play-by-play energetic, concise, and exciting.
Focus on visible action, momentum swings, and highlight moments.
""".strip()


async def create_agent(**_: Any) -> Agent:  # type: ignore[override]
    edge = getstream.Edge()
    llm = gemini.Realtime(
        api_key=os.environ.get("GOOGLE_API_KEY", ""),
        model=os.environ.get("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025"),
        fps=3,
    )
    tts = elevenlabs.TTS(
        api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
        voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "Anr9GtYh2VRXxiPplzxM"),
    )
    return Agent(
        edge=edge,
        llm=llm,
        tts=tts,
        agent_user=User(id="hypecast-agent", name="HypeCast Commentator"),
        instructions=ESPN_SYSTEM_PROMPT,
    )


launcher = AgentLauncher(create_agent=create_agent)
runner = Runner(launcher, app=api_app)


if __name__ == "__main__":
    runner.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
