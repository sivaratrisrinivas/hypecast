from __future__ import annotations

import logging
from typing import Any, Callable, Protocol

from services.commentary_hub import commentary_hub
from services.commentary_tracker import CommentaryTracker, commentary_tracker

logger = logging.getLogger(__name__)


class _Synthesizer(Protocol):
    def stream_audio(self, text: str, *args: Any, **kwargs: Any) -> Any: ...


def wrap_tts_with_fallback(
    tts: Any,
    *,
    session_id_provider: Callable[[], str | None],
    tracker: CommentaryTracker | None = None,
) -> None:
    """
    Wrap an ElevenLabs TTS instance (stream_audio) so that:

    - All text passed to stream_audio() is recorded via CommentaryTracker.
    - Exceptions trigger a graceful fallback that:
        - Logs the failure
        - Publishes raw text to the commentary WebSocket hub.
    """
    tracker = tracker or commentary_tracker

    if not hasattr(tts, "stream_audio"):
        logger.warning("TTS instance %r has no stream_audio() method; fallback wrapper skipped.", tts)
        return

    original = tts.stream_audio

    def safe_stream_audio(text: str, *args: Any, **kwargs: Any) -> Any:
        session_id = session_id_provider()
        logger.info("[tts_fallback] Requesting TTS for: %.60s...", text)
        entry = None
        if session_id and tracker is not None:
            entry = tracker.record(session_id, text)
            if entry:
                commentary_hub.publish_nowait(
                    session_id,
                    {
                        "text": entry.text,
                        "energy_level": entry.energy_level,
                        "is_highlight": entry.is_highlight,
                    },
                )

        try:
            result = original(text, *args, **kwargs)
            if result is None:
                logger.warning("[tts_fallback] stream_audio returned None (No audio generated).")
            else:
                logger.info("[tts_fallback] stream_audio SUCCESS (type=%s)", type(result).__name__)
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "[SPRINT 4] [tts_fallback] ElevenLabs TTS (stream_audio) FAILED: %s",
                exc,
                exc_info=True
            )
            if session_id and entry is None:
                energy = tracker.score_energy(text) if tracker is not None else 0.0
                commentary_hub.publish_nowait(
                    session_id,
                    {
                        "text": text,
                        "energy_level": energy,
                        "is_highlight": energy > (tracker.energy_threshold if tracker is not None else 0.75),
                    },
                )
            # Return None to avoid crashing the agent loop
            return None

    tts.stream_audio = safe_stream_audio
    logger.info("[SPRINT 4] TTS fallback wrapper installed (stream_audio + CommentaryTracker).")

