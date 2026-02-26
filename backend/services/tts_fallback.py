from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

from services.commentary_hub import commentary_hub
from services.commentary_tracker import CommentaryTracker, commentary_tracker

logger = logging.getLogger(__name__)


def wrap_tts_with_fallback(
    tts: Any,
    *,
    session_id_provider: Callable[[], str | None],
    tracker: CommentaryTracker | None = None,
) -> None:
    """
    Wrap a TTS instance so commentary text is always tracked and safely published,
    even if audio synthesis fails.
    """
    tracker = tracker or commentary_tracker

    if not hasattr(tts, "stream_audio"):
        logger.warning("TTS instance %r has no stream_audio() method; fallback wrapper skipped.", tts)
        return

    original = tts.stream_audio

    def _record_commentary(text: str) -> tuple[str | None, bool]:
        session_id = session_id_provider()
        logger.info("[tts_fallback] Requesting TTS for: %.60s...", text)
        entry_exists = False

        if session_id and tracker is not None:
            entry = tracker.record(session_id, text)
            if entry:
                entry_exists = True
                commentary_hub.publish_nowait(
                    session_id,
                    {
                        "text": entry.text,
                        "energy_level": entry.energy_level,
                        "is_highlight": entry.is_highlight,
                    },
                )

        return session_id, entry_exists

    def _publish_fallback_text(session_id: str | None, text: str, entry_exists: bool) -> None:
        if session_id and not entry_exists:
            energy = tracker.score_energy(text) if tracker is not None else 0.0
            commentary_hub.publish_nowait(
                session_id,
                {
                    "text": text,
                    "energy_level": energy,
                    "is_highlight": energy > (tracker.energy_threshold if tracker is not None else 0.75),
                },
            )

    def _log_success_or_empty(result: Any) -> Any:
        if result is None:
            logger.warning("[tts_fallback] stream_audio returned None (No audio generated).")
        else:
            logger.info("[tts_fallback] stream_audio SUCCESS (type=%s)", type(result).__name__)
        return result

    if inspect.iscoroutinefunction(original):

        async def safe_stream_audio(text: str, *args: Any, **kwargs: Any) -> Any:
            session_id, entry_exists = _record_commentary(text)
            try:
                result = await original(text, *args, **kwargs)
                return _log_success_or_empty(result)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "[SPRINT 4] [tts_fallback] ElevenLabs TTS (stream_audio) FAILED: %s",
                    exc,
                    exc_info=True,
                )
                _publish_fallback_text(session_id, text, entry_exists)
                return None

    else:

        def safe_stream_audio(text: str, *args: Any, **kwargs: Any) -> Any:
            session_id, entry_exists = _record_commentary(text)
            try:
                result = original(text, *args, **kwargs)
                return _log_success_or_empty(result)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "[SPRINT 4] [tts_fallback] ElevenLabs TTS (stream_audio) FAILED: %s",
                    exc,
                    exc_info=True,
                )
                _publish_fallback_text(session_id, text, entry_exists)
                return None

    tts.stream_audio = safe_stream_audio
    logger.info("[SPRINT 4] TTS fallback wrapper installed (stream_audio + CommentaryTracker).")
