"""FastAPI application and CORS configuration for Hypecast."""

# ruff: noqa: I001

import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.commentary_ws import router as commentary_ws_router
from routes.detections_ws import router as detections_ws_router
from routes.sessions import router as sessions_router

load_dotenv()

# Sprint 1: shared types and backend models (GameSession, SessionStatus, CommentaryEntry) are loaded via imports above
logging.getLogger(__name__).info(
    "[SPRINT 1] Backend models and shared contracts loaded (Session, CommentaryEntry, GameSession)."
)

app = FastAPI(
    title="Hypecast API",
    description="AI-powered sports commentary backend",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(sessions_router, prefix="/api")
app.include_router(detections_ws_router, prefix="/api")
app.include_router(commentary_ws_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def _log_sprint1_ready() -> None:
    logging.getLogger(__name__).info("[SPRINT 1] Foundation ready (API + CORS + session/commentary routes).")
