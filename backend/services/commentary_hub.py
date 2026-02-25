from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class CommentaryHub:
    """
    In-memory pubsub for streaming commentary text to WebSocket subscribers.

    Mirrors the semantics of DetectionHub, but payloads are commentary lines:
      {"text": "...", "energy_level": 0.0-1.0, "is_highlight": bool}
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    async def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=16)
        async with self._lock:
            self._subscribers[session_id].add(q)
        return q

    async def unsubscribe(self, session_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            subs = self._subscribers.get(session_id)
            if not subs:
                return
            subs.discard(q)
            if not subs:
                self._subscribers.pop(session_id, None)

    async def publish(self, session_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            subs = list(self._subscribers.get(session_id, set()))
        if not subs:
            return
        for q in subs:
            if q.full():
                try:
                    _ = q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                # If we raced between full-check and put, drop silently.
                pass

    def publish_nowait(self, session_id: str, payload: dict[str, Any]) -> None:
        """
        Fire-and-forget helper for sync contexts (e.g. TTS synthesize wrapper).
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop: nothing to deliver to; best-effort only.
            return
        loop.create_task(self.publish(session_id, payload))


commentary_hub = CommentaryHub()

