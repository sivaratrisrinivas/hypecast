from fastapi import FastAPI

app = FastAPI(
    title="Hypecast API",
    description="AI-powered sports commentary backend",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
