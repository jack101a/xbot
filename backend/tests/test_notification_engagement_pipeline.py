from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.container import Container
from xbot.contracts.browser import (
    ActionResult,
    BrowserActionType,
    BrowserResponse,
    NotificationData,
    ScrapeResult,
)
from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.notification_engagement_pipeline import run_notification_engagement_for_profile


@pytest.mark.asyncio
async def test_notification_engagement_likes_incoming_posts():
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

    mock_browser = AsyncMock()
    scrape_res = BrowserResponse(
        status="success",
        action=BrowserActionType.SCRAPE_NOTIFICATIONS,
        scrape=ScrapeResult(
            notifications=[
                NotificationData(
                    kind="reply",
                    actor_handle="TechCommenter",
                    text="Incredible post! What stack are you using?",
                    tweet_url="https://x.com/TechCommenter/status/987654321",
                )
            ]
        )
    )
    like_res = BrowserResponse(
        status="success",
        action=BrowserActionType.LIKE,
        action_result=ActionResult(status="success", detail="Liked notification tweet")
    )
    mock_browser.execute.side_effect = [scrape_res, like_res]

    container = Container(browser=mock_browser, llm=AsyncMock(), guard=AsyncMock())

    res = await run_notification_engagement_for_profile(
        db=mock_db,
        profile=mock_profile,
        guard=mock_guard,
        container=container,
    )

    assert res["status"] == "success"
    assert res["likes_count"] == 1
    mock_guard.record_action.assert_called_once()
    assert mock_browser.execute.call_count == 2
