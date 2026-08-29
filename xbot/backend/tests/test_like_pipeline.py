import datetime
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.like_pipeline import (
    run_like_pipeline_for_profile,
)


@pytest.mark.asyncio
async def test_run_like_pipeline_for_profile_success():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=True)
    mock_guard.is_target_acted_upon = MagicMock(return_value=False)
    mock_guard.record_action = AsyncMock()

    with patch("xbot.pipelines.like_pipeline.enqueue_browser_job", return_value="job-123"):
        with patch("xbot.pipelines.like_pipeline.get_browser_job_result") as mock_get_result:
            # First call: scrape feed -> returns 3 tweets
            # Subsequent calls: like results
            mock_get_result.side_effect = [
                {
                    "status": "success",
                    "tweets": [
                        {"id": "t1", "text": "Post 1", "author": "user1"},
                        {"id": "t2", "text": "Post 2", "author": "user2"},
                    ],
                },
                {"status": "liked", "tweet_id": "t1"},
                {"status": "liked", "tweet_id": "t2"},
            ]

            res = await run_like_pipeline_for_profile(mock_db, profile, mock_guard, max_likes=5)
            assert res["status"] == "success"
            assert res["likes_executed"] == 2
            assert mock_guard.record_action.call_count == 2


@pytest.mark.asyncio
async def test_run_like_pipeline_for_profile_skipped_by_guard():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=False)

    res = await run_like_pipeline_for_profile(mock_db, profile, mock_guard)
    assert res["status"] == "skipped"
    assert res["likes_executed"] == 0
