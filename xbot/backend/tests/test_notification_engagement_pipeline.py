from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.notification_engagement_pipeline import run_notification_engagement_for_profile


@pytest.mark.asyncio
async def test_notification_engagement_processes_follows_and_replies():
    mock_db = AsyncMock()
    mock_profile = Profile(
        id=1,
        profile_slug="test_creator",
        x_handle="@test_creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=True)
    mock_guard.is_target_acted_upon = MagicMock(return_value=False)
    mock_guard.record_action = MagicMock()

    mock_manager = MagicMock()
    mock_manager.acquire_lock = MagicMock(return_value=True)
    mock_manager.release_lock = MagicMock()

    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_manager.get_context = AsyncMock(return_value=mock_context)

    # Mock ScrapeNotifications output: 1 follow, 1 reply
    mock_notifications = [
        {
            "notification_type": "follow",
            "author_handle": "NewFollower123",
            "is_verified": True,
            "text": "NewFollower123 followed you",
        },
        {
            "notification_type": "reply",
            "author_handle": "TechCommenter",
            "tweet_url": "https://x.com/TechCommenter/status/987654321",
            "text": "Incredible post! What stack are you using?",
            "is_verified": True,
        }
    ]

    # Mock ScrapeFollowList output: 1 reciprocal follower
    mock_followers = ["ReciprocalPeer456"]

    with patch("xbot.pipelines.notification_engagement_pipeline.ScrapeNotifications.execute", AsyncMock(return_value=mock_notifications)), \
         patch("xbot.pipelines.notification_engagement_pipeline.ScrapeFollowList.execute", AsyncMock(return_value=mock_followers)), \
         patch("xbot.pipelines.notification_engagement_pipeline.LikeTweet.execute", AsyncMock(return_value=True)), \
         patch("xbot.pipelines.notification_engagement_pipeline.ReplyToTweet.execute", AsyncMock(return_value=True)), \
         patch("xbot.pipelines.notification_engagement_pipeline.FollowUser.execute", AsyncMock(return_value=True)), \
         patch("xbot.pipelines.notification_engagement_pipeline.generate_sniper_reply", AsyncMock(return_value=MagicMock(reply_text="FastAPI + PostgreSQL!"))):

        res = await run_notification_engagement_for_profile(
            db=mock_db,
            profile=mock_profile,
            guard=mock_guard,
            manager=mock_manager,
        )

        assert res["status"] == "success"
        assert res["likes_count"] == 1
        assert res["replies_count"] == 1
        assert res["follows_count"] == 2  # 1 from notification, 1 from follower list
