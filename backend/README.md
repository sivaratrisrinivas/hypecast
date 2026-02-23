# Hypecast Backend

## What it is

The backend is the server side of Hypecast. It will eventually:

- Create and track game sessions when someone taps START on their phone
- Issue secure tokens so the phone and laptop can join the same video call
- Run the AI that watches the stream and generates commentary
- Build the highlight reel after a game and hand out a shareable link

Right now it is a small API that exposes a health check so the rest of the system can confirm the server is running.

## Why it exists

The phone and laptop need a shared place to coordinate: when a session starts, who can join, when it ends, and where to get the finished reel. The backend holds that state and runs the AI pipeline. Keeping this in a separate service lets the frontend stay simple and allows the heavy work (video, AI, storage) to run on a single server.

## How to run it

**Prerequisites:** Python 3.11 or newer. We use [uv](https://docs.astral.sh/uv/) to manage dependencies and the environment.

**From the repo root:**

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

The API will be at `http://localhost:8000`. Open `http://localhost:8000/health` to see `{"status":"ok"}`.

**Run tests:**

```bash
cd backend
uv run pytest -v
```

**Lint:**

```bash
cd backend
uv run ruff check .
```

## Layout

- **`app/main.py`** — FastAPI app and routes (e.g. `/health`). More routes will be added as we build session and reel APIs.
- **`models/`** — Data shapes used by the backend: sessions, commentary entries, highlights, reels. These stay in sync with the frontend types so both sides agree on the structure of requests and responses.
- **`tests/`** — Pytest tests for the app and models.

Future work will add: session store, Stream token generation, Vision Agents runner, and reel generation (FFmpeg + storage). See `docs/sprints.md` for the full plan.
