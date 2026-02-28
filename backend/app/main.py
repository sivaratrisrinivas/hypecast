import asyncio
import secrets
from contextlib import suppress

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.models import GameSession, SessionCreateResponse, SessionReadResponse, SessionStatus
from app.store import publish_commentary, sessions, subscribe_commentary

app = FastAPI(title="HypeCast API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sessions", response_model=SessionCreateResponse)
def create_session() -> SessionCreateResponse:
    session_id = secrets.token_urlsafe(8)
    join_url = f"/game/{session_id}"
    sessions[session_id] = GameSession(id=session_id, join_url=join_url)
    return SessionCreateResponse(session_id=session_id, join_url=join_url)


@app.get("/api/sessions/{session_id}", response_model=SessionReadResponse)
def read_session(session_id: str) -> SessionReadResponse:
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionReadResponse(session_id=session.id, status=session.status)


async def commentary_simulator(session_id: str) -> None:
    lines = [
        "And we are live from the park!",
        "Great movement in transition, pressure building!",
        "WHAT A PLAY! That's a highlight moment right there!",
    ]
    for line in lines:
        publish_commentary(session_id, {"text": line})
        await asyncio.sleep(1.5)


@app.websocket("/api/ws/sessions/{session_id}/commentary")
async def ws_commentary(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    if session_id not in sessions:
        await websocket.send_json({"text": "Session not found."})
        await websocket.close()
        return

    simulator_task = asyncio.create_task(commentary_simulator(session_id))
    try:
        async with subscribe_commentary(session_id) as queue:
            while True:
                while queue.empty():
                    await asyncio.sleep(0.1)
                await websocket.send_json(queue.get())
    except WebSocketDisconnect:
        pass
    finally:
        simulator_task.cancel()
        with suppress(asyncio.CancelledError):
            await simulator_task
