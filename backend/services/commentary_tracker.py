"""Commentary tracking and energy scoring utilities."""

# ruff: noqa: I001

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import logging

from models import CommentaryEntry, ENERGY_THRESHOLD, HIGHLIGHT_KEYWORDS
from services.store import sessions

logger = logging.getLogger(__name__)


class CommentaryTracker:
    """
    Track Gemini commentary text per game session and compute an "energy" score.

    This is intentionally lightweight: Sprint 4.4 only requires that we:
      - Capture raw Gemini text outputs
      - Compute an energy_level in [0.0, 1.0]
      - Flag entries as highlights when energy_level > ENERGY_THRESHOLD
    """

    def __init__(
        self,
        *,
        highlight_keywords: list[str] | None = None,
        energy_threshold: float = ENERGY_THRESHOLD,
    ) -> None:
        self._keywords = [k.upper() for k in (highlight_keywords or HIGHLIGHT_KEYWORDS)]
        self._threshold = energy_threshold
        self._sessions_logged: set[str] = set()

    @property
    def energy_threshold(self) -> float:
        return self._threshold

    def score_energy(self, text: str) -> float:
        """
        Heuristic "energy" scoring for commentary text.

        Requirements from spec:
          - Entries containing strong hype keywords like "UNBELIEVABLE" must
            score > 0.75 so they are treated as highlight candidates.
        """
        if not text:
            return 0.0

        upper = text.upper()
        for kw in self._keywords:
            if kw in upper:
                # Hard bump for explicit highlight phrases.
                return 0.95

        # Lightweight heuristic for non-keyword lines:
        # - more exclamation marks -> more hype
        # - slightly reward longer sentences
        bang_bonus = min(upper.count("!"), 3) * 0.1
        length_bonus = min(len(upper) / 120.0, 0.3)
        base = 0.2
        score = base + bang_bonus + length_bonus
        # Clamp to [0, 1]
        return max(0.0, min(score, 1.0))

    def record(
        self,
        session_id: str,
        text: str,
        *,
        now: datetime | None = None,
    ) -> CommentaryEntry | None:
        """
        Append a CommentaryEntry to the session's log and return it.

        - timestamp is seconds since GameSession.created_at
        - energy_level / is_highlight computed from text
        """
        session = sessions.get(session_id)
        if session is None:
            logger.warning(
                "[commentary_tracker] Session %s not found; dropping commentary: %r",
                session_id,
                text,
            )
            return None

        now_dt = now or datetime.now(timezone.utc)
        created_at = session.created_at
        # Both are timezone-aware (UTC); total_seconds may be negative in degenerate cases
        elapsed = (now_dt - created_at).total_seconds()
        timestamp = max(0.0, float(elapsed))

        energy = self.score_energy(text)
        is_highlight = energy > self._threshold

        entry = CommentaryEntry(
            timestamp=timestamp,
            text=text,
            energy_level=energy,
            is_highlight=is_highlight,
        )
        session.commentary_log.append(entry)
        if session_id not in self._sessions_logged:
            self._sessions_logged.add(session_id)
            logger.info(
                "[SPRINT 4] CommentaryTracker: first commentary recorded (energy scoring + highlight flagging) for session %s",
                session_id,
            )
        logger.info(
            "[commentary_tracker] Recorded: session=%s energy=%.2f highlight=%s text=%.60s...",
            session_id,
            entry.energy_level,
            entry.is_highlight,
            entry.text,
        )
        return entry


# Singleton tracker used by the agent pipeline.
commentary_tracker = CommentaryTracker()

