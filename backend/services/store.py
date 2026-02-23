"""In-memory session store for MVP. Keyed by session ID."""

from models.session import GameSession

sessions: dict[str, GameSession] = {}
