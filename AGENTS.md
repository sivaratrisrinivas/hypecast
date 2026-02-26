# Agents

## Cursor Cloud specific instructions

### Overview

Hypecast is a two-service app (Next.js frontend + Python/FastAPI backend). See `README.md` for full details.

### Services

| Service | Dir | Dev command | Port |
|---------|-----|-------------|------|
| Frontend (Next.js) | `frontend/` | `pnpm dev` | 3000 |
| Backend (FastAPI) | `backend/` | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | 8000 |

The backend can also be started via `uv run agent.py serve --host 0.0.0.0 --port 8000` which wraps the FastAPI app inside the Vision Agents Runner (requires `GOOGLE_API_KEY`, `STREAM_API_KEY`, `STREAM_API_SECRET`). For local dev/testing without external API keys, the simpler `uvicorn app.main:app` works for API endpoints.

### Lint / Test / Build

See `README.md` "Check code quality" section. Quick reference:

- **Frontend lint:** `cd frontend && pnpm lint`
- **Frontend tests:** `cd frontend && pnpm test -- --run`
- **Backend lint:** `cd backend && uv run ruff check .`
- **Backend tests:** `cd backend && uv run pytest -v`
- **Frontend build:** `cd frontend && pnpm build`

### Gotchas

- The `pnpm install` may warn about ignored build scripts for `esbuild`. This is non-blocking; the install still succeeds.
- Backend ruff lint has pre-existing warnings (E501 line length, E402 import order, etc.) in debug scripts and some source files. These are in the existing codebase.
- The backend uses an in-memory session store (no database needed).
- `uv` must be on `$PATH`. It installs to `~/.local/bin` — the update script handles this via `PATH` export.
- Python 3.12 is required (`.python-version` in `backend/`). The system Python 3.12.3 works fine.
- External API keys (`STREAM_API_KEY`, `STREAM_API_SECRET`, `GOOGLE_API_KEY`, `ELEVENLABS_API_KEY`) are only needed for full agent pipeline (live commentary). The FastAPI server, tests, and frontend all work without them.
