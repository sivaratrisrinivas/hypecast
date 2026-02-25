import httpx
import pytest

from agent import runner


@pytest.mark.anyio
async def test_runner_health_uses_existing_app() -> None:
    """
    Sprint 3.1 validation: the Vision Agents runner starts with the
    existing FastAPI app mounted, and /health responds with 200.
    """
    transport = httpx.ASGITransport(app=runner.fast_api)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200

