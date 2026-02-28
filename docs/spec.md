# HypeCast Spec (MVP)

## Product goal

- Phone opens camera mode and streams live view.
- Spectator opens session link and listens to/generated commentary.
- Backend manages sessions and commentary websocket.
- Vision Agents + Gemini generate play-by-play when configured.

## Architecture

- Frontend: Next.js app router, responsive role switch (`camera`/`spectator`).
- Backend: FastAPI with in-memory session store.
- AI runner: `agent.py` wraps FastAPI inside Vision Agents `Runner`.

## Deployment

- Frontend: Vercel (or any Next.js host)
- Backend: Railway
