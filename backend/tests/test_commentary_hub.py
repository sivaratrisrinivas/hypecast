from __future__ import annotations

import asyncio
import pytest

from services.commentary_hub import CommentaryHub


@pytest.mark.asyncio
async def test_commentary_hub_replays_recent_history_for_late_subscriber() -> None:
    hub = CommentaryHub()
    session_id = "history-session"

    await hub.publish(session_id, {"text": "line 1", "energy_level": 0.2, "is_highlight": False})
    await hub.publish(session_id, {"text": "line 2", "energy_level": 0.9, "is_highlight": True})

    q = await hub.subscribe(session_id)
    first = await asyncio.wait_for(q.get(), timeout=0.5)
    second = await asyncio.wait_for(q.get(), timeout=0.5)

    assert first["text"] == "line 1"
    assert second["text"] == "line 2"

    await hub.unsubscribe(session_id, q)
