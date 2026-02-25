from __future__ import annotations

import logging
from typing import Any, Callable, Protocol

from services.commentary_hub import commentary_hub
from services.commentary_tracker import CommentaryTracker, commentary_tracker

logger = logging.getLogger(__name__)


class _Synthesizer(Protocol):
    def synthesize(self, text: str, *args: Any, **kwargs: Any) -> bytes: ...


def wrap_tts_with_fallback(
    tts: _Synthesizer,
    *,
    session_id_provider: Callable[[], str | None],
    tracker: CommentaryTracker | None = None,
) -> None:
    """
    Wrap an ElevenLabs TTS instance so that:

    - All text passed to synthesize() is recorded via CommentaryTracker.
    - Exceptions from ElevenLabs trigger a graceful fallback that:
        - Logs the failure
        - Publishes raw text to the commentary WebSocket hub so the frontend
          can drive SpeechSynthesis or another client-side TTS.

    This mutates the instance in-place (replacing tts.synthesize) so existing
    tests that assert identity (agent.tts is TTS instance) continue to hold.
    """
    tracker = tracker or commentary_tracker

    if not hasattr(tts, "synthesize"):
        logger.warning("TTS instance %r has no synthesize() method; fallback wrapper skipped.", tts)
        return

    original = tts.synthesize  # type: ignore[assignment]

    def safe_synthesize(text: str, *args: Any, **kwargs: Any) -> bytes:  # type: ignore[override]
        session_id = session_id_provider()
        if session_id and tracker is not None:
            tracker.record(session_id, text)
        try:
            return original(text, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[tts_fallback] ElevenLabs TTS failed for session %s: %s. "
                "Falling back to text/WebSocket delivery.",
                session_id,
                exc,
            )
            if session_id:
                commentary_hub.publish_nowait(
                    session_id,
                    {
                        "text": text,
                        # We don't have direct access to the computed CommentaryEntry here,
                        # but the tracker.record() call above has already appended it to
                        # the session log. For the WebSocket payload we only need a
                        # coarse energy/highlight signal; recompute using tracker.
                        "energy_level": tracker.score_energy(text) if tracker is not None else 0.0,
                        "is_highlight": (
                            tracker.score_energy(text) > tracker.energy_threshold if tracker is not None else False
                        ),
                    },
                )
            # Return silence (empty bytes) so the agent pipeline doesn't crash.
            return b""

    tts.synthesize = safe_synthesize  # type: ignore[assignment]

