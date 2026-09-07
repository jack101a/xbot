import datetime
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.container import Container
from xbot.contracts.browser import (
    ActionResult,
    BrowserActionType,
    BrowserResponse,
    ScrapeResult,
    TweetData,
)
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

    mock_browser = AsyncMock()
    # 1. Scrape response
    scrape_response = BrowserResponse(
        status="success",
        action=BrowserActionType.SCRAPE_FEED,
        scrape=ScrapeResult(
            tweets=[
                TweetData(tweet_id="t1", url="https://x.com/u1/1", handle="u1", text="Post 1"),
                TweetData(tweet_id="t2", url="https://x.com/u2/2", handle="u2", text="Post 2"),
            ]
        )
    )
    # 2. Like responses
    like_response_1 = BrowserResponse(
        status="success",
        action=BrowserActionType.LIKE,
        action_result=ActionResult(status="success", detail="Liked t1", target_id="t1")
    )
    like_response_2 = BrowserResponse(
        status="success",
        action=BrowserActionType.LIKE,
        action_result=ActionResult(status="success", detail="Liked t2", target_id="t2")
    )

    mock_browser.execute.side_effect = [scrape_response, like_response_1, like_response_2]
    container = Container(browser=mock_browser, llm=AsyncMock(), guard=AsyncMock())

    res = await run_like_pipeline_for_profile(mock_db, profile, mock_guard, container=container, max_likes=5)
    assert res["status"] == "success"
    assert res["likes_executed"] == 2
    assert mock_guard.record_action.call_count == 2
    assert mock_browser.execute.call_count == 3


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
