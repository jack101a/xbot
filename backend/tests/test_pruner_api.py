import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.main import app
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionType, ActionStatus

@pytest.mark.asyncio
async def test_pruner_api_endpoints():
    profile_id = uuid.uuid4()
    mock_profile = Profile(
        id=profile_id,
        profile_slug="test_slug",
        x_handle="@test_handle",
        display_name="Test Handle",
        status=ProfileStatus.ACTIVE,
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_profile
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    mock_redis = MagicMock()

    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test 1: Run pruner
        with patch("xbot.api.profiles.pruner_routes.run_post_pruner_for_profile") as mock_run:
            mock_run.return_value = {
                "status": "success",
                "profile_id": str(profile_id),
                "deleted_count": 1,
                "deleted_posts": [{"tweet_id": "123", "reason": "low_views"}],
            }

            resp = await client.post(
                f"/api/profiles/{profile_id}/pruner/run",
                json={
                    "min_views": 150,
                    "min_likes": 3,
                    "min_comments": 1,
                    "min_age_hours": 24,
                    "max_posts_to_delete": 5,
                    "match_mode": "all",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["deleted_count"] == 1

        # Test 2: Get history
        resp_hist = await client.get(f"/api/profiles/{profile_id}/pruner/history")
        assert resp_hist.status_code == 200
        hist_data = resp_hist.json()
        assert hist_data["profile_id"] == str(profile_id)
        assert "history" in hist_data

    app.dependency_overrides.clear()
