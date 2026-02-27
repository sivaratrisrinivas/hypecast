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

### Agent Pipeline Stack

The agent (`agent.py`) uses:
- `gemini.Realtime(fps=3)` — real-time speech-to-speech with video frames via WebSocket. Generates ESPN-style play-by-play commentary natively.
- `RFDetrDetectionProcessor(fps=5)` — RF-DETR local player/ball detection (downloads ~370MB model weights on first run). Injects detection state into LLM context.
- `elevenlabs.TTS(voice_id=Chris)` — ElevenLabs TTS fallback for text-only scenarios.

To run the full agent runner (not just the API): `cd backend && uv run agent.py serve --host 0.0.0.0 --port 8000`. Requires all four secrets. The runner mounts the FastAPI app at `/` and adds the Vision Agents session lifecycle at `POST /sessions`.

Frontend needs `NEXT_PUBLIC_STREAM_API_KEY` in `frontend/.env.local` (same value as `STREAM_API_KEY`) for the Stream Video React SDK.

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
- `GEMINI_LIVE_MODEL` (optional): Override Gemini Live API model. Default `gemini-2.5-flash-native-audio-preview-12-2025` (required for bidiGenerateContent; `gemini-2.0-flash` is not supported).
- The `rfdetr` package downloads ~370MB model weights (`rf-detr-base.pth`) on first import. These are gitignored. The download happens during `create_agent()` and is cached locally after the first run.
