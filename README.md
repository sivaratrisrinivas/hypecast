# Hypecast

Turn a casual sports game into an ESPN-style broadcast. Point your phone at the game, tap **START** — an AI commentator watches the stream and speaks play-by-play on your laptop. When you’re done, get a short highlight reel with commentary and a shareable link.

**Two devices, one URL:** phone = camera, laptop = spectator. Role is picked from screen size or `?role=camera` / `?role=spectator`.

---

## Tech stack

| Part      | Stack |
| --------- | ----- |
| Frontend  | Next.js 16, React 19, Tailwind CSS 4, TypeScript, pnpm |
| Backend   | Python 3.11+, FastAPI, uv |
| (Planned) | Stream Video (WebRTC), Vision Agents SDK, Gemini, ElevenLabs, GCS, FFmpeg |

---

## Quick start

**Frontend (app + game UI)**

```bash
cd frontend
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). Use `?role=camera` for the phone view (START button) or `?role=spectator` for the laptop view.

**Backend (API; health only for now)**

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

API: [http://localhost:8000](http://localhost:8000). Health: [http://localhost:8000/health](http://localhost:8000/health).

**Lint & test**

```bash
# Frontend
cd frontend && pnpm lint && pnpm test

# Backend
cd backend && uv run pytest -v
```

---

## Repo layout

```
hypecast/
├── README.md           # this file
├── docs/
│   ├── spec.md         # architecture, data models, APIs
│   └── sprints.md      # sprint plan and task checklist
├── frontend/           # Next.js app (see frontend/package.json)
└── backend/            # FastAPI app (see backend/README.md)
```

---

## Docs

- **[docs/spec.md](docs/spec.md)** — System design, APIs, data models, env vars.
- **[docs/sprints.md](docs/sprints.md)** — Sprints and tasks (Sprint 1 done; 2–5 planned).
- **[backend/README.md](backend/README.md)** — What the backend does and how to run it.

---

Built for **Vision Possible: Agent Protocol** (WeMakeDevs, Feb–Mar 2026). Uses [Vision Agents SDK](https://visionagents.ai) by Stream.
