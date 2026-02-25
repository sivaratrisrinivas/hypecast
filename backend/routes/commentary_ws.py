from __future__ import annotations

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.commentary_hub import commentary_hub

router = APIRouter(tags=["commentary"])


@router.websocket("/ws/sessions/{session_id}/commentary")
async def ws_session_commentary(websocket: WebSocket, session_id: str) -> None:
    """
    Stream commentary lines (or fallback text) to the frontend.

    Payload schema:
      {
        "text": str,
        "energy_level": float,
        "is_highlight": bool,
      }
    """
    await websocket.accept()
    q = await commentary_hub.subscribe(session_id)
    try:
        while True:
            payload: dict[str, Any] = await q.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        return
    finally:
        await commentary_hub.unsubscribe(session_id, q)

