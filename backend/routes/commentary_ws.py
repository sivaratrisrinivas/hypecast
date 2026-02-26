from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.commentary_hub import commentary_hub

router = APIRouter(tags=["commentary"])
logger = logging.getLogger(__name__)


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
    logger.info("[commentary_ws] Client connecting for session_id=%r", session_id)
    try:
        await websocket.accept()
    except Exception as e:
        logger.warning("[commentary_ws] accept() failed session_id=%r: %s", session_id, e)
        return
    try:
        q = await commentary_hub.subscribe(session_id)
    except Exception as e:
        logger.warning("[commentary_ws] subscribe() failed session_id=%r: %s", session_id, e)
        return
    logger.info("[commentary_ws] Subscribed session_id=%r", session_id)
    try:
        while True:
            payload: dict[str, Any] = await q.get()
            logger.info("[commentary_ws] Sending payload to client for session=%s: text=%.60s...", session_id, payload.get("text", ""))
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        return
    finally:
        await commentary_hub.unsubscribe(session_id, q)

