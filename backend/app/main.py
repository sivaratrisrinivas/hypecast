from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from routes.sessions import router as sessions_router

app = FastAPI(
    title="Hypecast API",
    description="AI-powered sports commentary backend",
    version="0.1.0",
)
app.include_router(sessions_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
