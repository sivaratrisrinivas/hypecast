from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from queue import SimpleQueue

from app.models import GameSession

sessions: dict[str, GameSession] = {}
commentary_queues: dict[str, list[SimpleQueue[dict[str, str]]]] = {}


@asynccontextmanager
async def subscribe_commentary(session_id: str) -> AsyncIterator[SimpleQueue[dict[str, str]]]:
    queue: SimpleQueue[dict[str, str]] = SimpleQueue()
    commentary_queues.setdefault(session_id, []).append(queue)
    try:
        yield queue
    finally:
        commentary_queues[session_id].remove(queue)
        if not commentary_queues[session_id]:
            commentary_queues.pop(session_id, None)


def publish_commentary(session_id: str, payload: dict[str, str]) -> None:
    for queue in commentary_queues.get(session_id, []):
        queue.put(payload)
