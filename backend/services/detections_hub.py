from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class DetectionHub:
    """
    Simple in-memory pubsub for streaming detection payloads.

    - Each subscriber gets an asyncio.Queue(maxsize=1) (latest-wins).
    - Publisher fan-outs to all current subscribers for the session_id.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    async def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1)
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
            # latest-wins: if queue is full, drop the old payload
            if q.full():
                try:
                    _ = q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                # If it races between full-check and put, just drop.
                pass


detections_hub = DetectionHub()

