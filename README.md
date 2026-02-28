# HypeCast (Rebuilt)

HypeCast is a real-time sports commentary app with:

- **Frontend:** Next.js/React webcam client
- **Backend:** FastAPI API (Railway-ready)
- **AI layer:** Vision Agents SDK + Gemini (with optional ElevenLabs fallback)

## Local development

### Frontend (port 3000)

```bash
cd frontend
pnpm install
pnpm dev
```

### Backend (port 8000)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Run full Vision Agents runner

```bash
cd backend
uv run agent.py serve --host 0.0.0.0 --port 8000
```

Required env vars for full AI pipeline:

- `STREAM_API_KEY`
- `STREAM_API_SECRET`
- `GOOGLE_API_KEY`
- `ELEVENLABS_API_KEY` (optional fallback voice output)

## Railway deployment (backend)

The backend includes `railway.json` and a `Procfile`.

- Start command: `uv run agent.py serve --host 0.0.0.0 --port $PORT`
- Healthcheck path: `/health`

## API overview

- `GET /health`
- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `WS /api/ws/sessions/{session_id}/commentary`

## Quality checks

```bash
cd frontend && pnpm lint && pnpm build
cd backend && uv run ruff check . && uv run pytest -v
```
