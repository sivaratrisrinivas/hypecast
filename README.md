# Hypecast

## What it is

Hypecast turns a casual sports game into a live broadcast with commentary. You point your phone at the game and tap **START**. An AI commentator watches the video stream and speaks play-by-play on your laptop in real time. When you tap **END**, the app builds a short highlight reel with that commentary and gives you a link you can share for 48 hours.

You use two devices with one link: the **phone** is the camera, the **laptop** is where you hear the commentary. The app figures out which device you’re on from screen size, or you can force it with `?role=camera` or `?role=spectator` in the URL.

---

## Why it exists

The goal is one-tap, zero-setup commentary: no accounts, no choosing a sport or typing names. You open the link, tap START, and the AI describes what it sees. After the game, you get a packaged highlight reel instead of a long raw clip. It’s built for the **Vision Possible: Agent Protocol** hackathon (WeMakeDevs, Feb–Mar 2026) and uses Stream’s [Vision Agents](https://visionagents.ai) tools.

---

## How to run it

**What you need:** Node.js and pnpm for the frontend; Python 3.11+ and [uv](https://docs.astral.sh/uv/) for the backend.

**Run the app (frontend)**

```bash
cd frontend
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). Use `?role=camera` for the phone view (camera placeholder and START button) or `?role=spectator` for the laptop view (e.g. “Awaiting connection…”).

**Run the API (backend)**

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

The API is at [http://localhost:8000](http://localhost:8000). Check [http://localhost:8000/health](http://localhost:8000/health) to confirm it’s up. **POST /api/sessions** creates a game session (in-memory store; returns `session_id`, `stream_call_id`, `join_url`, `stream_token`). **GET /api/sessions/{id}** returns session status for polling (WAITING → LIVE, etc.). **GET /api/sessions/{id}/token?role=...** issues Stream tokens. Session end and reel APIs come in later sprints.

**Check code quality**

```bash
# Frontend: lint and tests
cd frontend && pnpm lint && pnpm test

# Backend: tests and lint
cd backend && uv run pytest -v && uv run ruff check .
```

---

## What’s in this repo

| Part | Role |
|------|------|
| **frontend/** | Web app: landing, camera view (phone), spectator view (laptop). Next.js, React, Tailwind, TypeScript. |
| **backend/** | Server that creates sessions, issues Stream tokens, and exposes session polling. FastAPI app in `app/main.py`; session API in `routes/sessions.py` (POST/GET session, GET token), in-memory store in `services/store.py`; `models/` for data shapes, `tests/` for pytest. |
| **docs/spec.md** | Full design: data shapes, APIs, how video and commentary flow. |
| **docs/sprints.md** | Task plan: Sprint 1 done; Sprint 2 in progress (2.1–2.3 done: session store, token API, useSession hook); Sprints 2–5 otherwise planned (Stream SDK, AI, reels, polish). |

---

## Important details

- **Session limits (planned):** One game at a time, up to 5 minutes; highlight reel about 30–60 seconds, 3–5 clips; share link expires in 48 hours.
- **No login:** No accounts. You open the link and go.
- **Same URL for both devices:** One link works on phone and laptop; the app picks camera vs spectator from screen size or the `role` query param.

---

Built for **Vision Possible: Agent Protocol** (WeMakeDevs). Uses [Vision Agents](https://visionagents.ai) by Stream.
