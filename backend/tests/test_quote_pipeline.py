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
from xbot.pipelines.quote_pipeline import run_quote_pipeline_for_profile


@pytest.mark.asyncio
async def test_run_quote_pipeline_for_profile():
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
    # 1. Scrape feed response
    scrape_res = BrowserResponse(
        status="success",
        action=BrowserActionType.SCRAPE_FEED,
        scrape=ScrapeResult(
            tweets=[
                TweetData(
                    tweet_id="viral-1",
                    url="https://x.com/tech_founder/status/viral-1",
                    handle="tech_founder",
                    text="Why AI agents will replace traditional SaaS in 24 months.",
                    metrics={"views": 75000}
                )
            ]
        )
    )
    # 2. Context scrape response
    ctx_res = BrowserResponse(
        status="success",
        action=BrowserActionType.SCRAPE_TWEET_CONTEXT,
        scrape=ScrapeResult(raw={
            "text": "Why AI agents will replace traditional SaaS in 24 months.",
            "top_comments": [{"author": "dev1", "text": "Already seeing this with cursor", "likes": 50}],
        })
    )
    # 3. Quote action response
    quote_res = BrowserResponse(
        status="success",
        action=BrowserActionType.QUOTE,
        action_result=ActionResult(status="success", detail="Quoted tweet")
    )
    # 4. Like response
    like_res = BrowserResponse(
        status="success",
        action=BrowserActionType.LIKE,
        action_result=ActionResult(status="success", detail="Liked tweet")
    )

    mock_browser.execute.side_effect = [scrape_res, ctx_res, quote_res, like_res]
    container = Container(browser=mock_browser, llm=AsyncMock(), guard=AsyncMock())

    with patch("xbot.ai.sniper.generate_quote_take", new_callable=AsyncMock) as mock_quote_gen:
        from xbot.ai.sniper.verifier import QuoteTakeResult
        mock_quote_gen.return_value = QuoteTakeResult(
            topic_understanding="Discussion on AI agents disrupting SaaS.",
            quote_text="Distribution beats models every single time. #AI",
            gif_query=None,
            reasoning="Strategic contrarian perspective.",
        )

        res = await run_quote_pipeline_for_profile(mock_db, profile, mock_guard, container=container, max_quotes=1)
        assert res["status"] == "success"
        assert res["quotes_executed"] == 1
        mock_guard.record_action.assert_called_once()
