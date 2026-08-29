import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.database import init_db
from xbot.main import app


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    await init_db()


@pytest.mark.asyncio
async def test_get_pipeline_status_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch("xbot.api.pipeline_status.redis.from_url") as mock_redis_func:
            mock_redis = MagicMock()
            mock_redis.get.return_value = None
            mock_redis.zcard.return_value = 2
            mock_redis_func.return_value = mock_redis

            response = await ac.get("/pipelines/status")
            assert response.status_code == 200
            data = response.json()
            assert "pipelines" in data
            assert "browser_queue" in data["pipelines"]
            assert "like_pipeline" in data["pipelines"]
            assert "reply_pipeline" in data["pipelines"]
            assert "quote_pipeline" in data["pipelines"]
            assert "follow_pipeline" in data["pipelines"]
            assert "trend_researcher_pipeline" in data["pipelines"]
            assert "trend_generator_pipeline" in data["pipelines"]


@pytest.mark.asyncio
async def test_trigger_pipeline_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch("xbot.api.pipeline_status.run_like_pipeline", return_value={"status": "success", "total_likes": 5}):
            response = await ac.post("/pipelines/like/trigger")
            assert response.status_code == 200
            data = response.json()
            assert "triggered successfully" in data["message"]

