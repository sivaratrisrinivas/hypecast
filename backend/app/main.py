from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.sessions import router as sessions_router

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
app.include_router(sessions_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
