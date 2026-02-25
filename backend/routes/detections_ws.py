from __future__ import annotations

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.detections_hub import detections_hub

router = APIRouter(tags=["detections"])


@router.websocket("/ws/sessions/{session_id}/detections")
async def ws_session_detections(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    q = await detections_hub.subscribe(session_id)
    try:
        while True:
            payload: dict[str, Any] = await q.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        return
    finally:
        await detections_hub.unsubscribe(session_id, q)

