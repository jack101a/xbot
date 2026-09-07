import datetime
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.container import Container
from xbot.contracts.browser import (
    ActionResult,
    BrowserActionType,
    BrowserResponse,
    FollowListResult,
    ScrapeResult,
)
from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.follow_pipeline import run_follow_pipeline_for_profile


@pytest.mark.asyncio
async def test_run_follow_pipeline_for_profile_skipped_by_guard():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=False)

    res = await run_follow_pipeline_for_profile(mock_db, profile, mock_guard)
    assert res["status"] == "skipped"
    assert res["actions_executed"] == 0


@pytest.mark.asyncio
async def test_run_follow_pipeline_reciprocal_success():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=True)
    mock_guard.record_action = AsyncMock()

    mock_browser = AsyncMock()
    # 1. Scrape verified followers: returns ['verified_fan']
    vf_res = BrowserResponse(
        status="success",
        action=BrowserActionType.SCRAPE_FOLLOW_LIST,
        scrape=ScrapeResult(follow_list=FollowListResult(list_type="verified_followers", handles=["verified_fan"]))
    )
    # 2. Scrape regular followers: returns ['verified_fan', 'regular_fan']
    rf_res = BrowserResponse(
        status="success",
        action=BrowserActionType.SCRAPE_FOLLOW_LIST,
        scrape=ScrapeResult(follow_list=FollowListResult(list_type="followers", handles=["verified_fan", "regular_fan"]))
    )
    # 3. Scrape following: returns [] (we follow neither)
    following_res = BrowserResponse(
        status="success",
        action=BrowserActionType.SCRAPE_FOLLOW_LIST,
        scrape=ScrapeResult(follow_list=FollowListResult(list_type="following", handles=[]))
    )
    # 4. Scrape notifications: empty
    notif_res = BrowserResponse(
        status="success",
        action=BrowserActionType.SCRAPE_NOTIFICATIONS,
        scrape=ScrapeResult(notifications=[])
    )
    # 5. Follow execution response
    follow_res = BrowserResponse(
        status="success",
        action=BrowserActionType.FOLLOW,
        action_result=ActionResult(status="success", detail="Followed user")
    )

    mock_browser.execute.side_effect = [vf_res, rf_res, following_res, notif_res, follow_res, follow_res]
    container = Container(browser=mock_browser, llm=AsyncMock(), guard=AsyncMock())

    with patch("xbot.pipelines.follow_pipeline.record_follow_action", new_callable=AsyncMock), \
         patch("xbot.pipelines.follow_pipeline.populate_f4f_candidates", new_callable=AsyncMock):
        res = await run_follow_pipeline_for_profile(mock_db, profile, mock_guard, container=container)
        assert res["status"] == "success"
        assert res["followed_back"] == 2
