from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from xbot.browser.actions.tweet_context_scraper import (
    scrape_target_tweet_context,
    peek_tweet_context_via_worker,
)


@pytest.mark.asyncio
async def test_scrape_target_tweet_context_sorts_comments_by_likes():
    mock_page = MagicMock()
    mock_page.url = "https://x.com/tech_creator/status/987654"
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.evaluate = AsyncMock()

    # Root tweet element
    mock_root_tweet = MagicMock()
    mock_user = MagicMock()
    mock_user.inner_text = AsyncMock(return_value="Tech Creator @tech_creator")
    mock_root_tweet.query_selector = AsyncMock(side_effect=lambda sel: mock_user if "User-Name" in sel else None)
    mock_root_tweet.query_selector_all = AsyncMock(return_value=[])

    # Comment 1: 5 likes
    mock_c1 = MagicMock()
    mock_c1_user = MagicMock()
    mock_c1_user.inner_text = AsyncMock(return_value="User1 @user1")
    mock_c1_text = MagicMock()
    mock_c1_text.inner_text = AsyncMock(return_value="First comment")
    mock_c1_like = MagicMock()
    mock_c1_like.get_attribute = AsyncMock(return_value="5 Likes")
    mock_c1_like.inner_text = AsyncMock(return_value="5")

    async def c1_qs(sel):
        if "User-Name" in sel:
            return mock_c1_user
        if "tweetText" in sel:
            return mock_c1_text
        if "like" in sel:
            return mock_c1_like
        return None

    mock_c1.query_selector = AsyncMock(side_effect=c1_qs)

    # Comment 2: 120 likes (Higher popularity)
    mock_c2 = MagicMock()
    mock_c2_user = MagicMock()
    mock_c2_user.inner_text = AsyncMock(return_value="User2 @user2")
    mock_c2_text = MagicMock()
    mock_c2_text.inner_text = AsyncMock(return_value="Most viral rebuttal comment")
    mock_c2_like = MagicMock()
    mock_c2_like.get_attribute = AsyncMock(return_value="120 Likes")
    mock_c2_like.inner_text = AsyncMock(return_value="120")

    async def c2_qs(sel):
        if "User-Name" in sel:
            return mock_c2_user
        if "tweetText" in sel:
            return mock_c2_text
        if "like" in sel:
            return mock_c2_like
        return None

    mock_c2.query_selector = AsyncMock(side_effect=c2_qs)

    mock_page.query_selector_all = AsyncMock(return_value=[mock_root_tweet, mock_c1, mock_c2])

    result = await scrape_target_tweet_context(mock_page, target_idx=0)

    assert result["author"] == "tech_creator"
    assert len(result["top_comments"]) == 2
    # Ensure sorted by popularity (120 likes first, 5 likes second)
    assert result["top_comments"][0]["author"] == "user2"
    assert result["top_comments"][0]["likes"] == 120
    assert result["top_comments"][1]["author"] == "user1"
    assert result["top_comments"][1]["likes"] == 5


@pytest.mark.asyncio
async def test_peek_tweet_context_via_worker():
    mock_manager = MagicMock()
    mock_worker_page = MagicMock()
    mock_worker_page.url = "https://x.com/creator/status/112233"
    mock_worker_page.goto = AsyncMock()
    mock_worker_page.wait_for_selector = AsyncMock()
    mock_worker_page.evaluate = AsyncMock()
    mock_worker_page.query_selector_all = AsyncMock(return_value=[])

    class MockWorkerCtx:
        async def __aenter__(self):
            return mock_worker_page
        async def __aexit__(self, *args):
            pass

    mock_manager.acquire_worker.return_value = MockWorkerCtx()

    res = await peek_tweet_context_via_worker(mock_manager, "test_profile", "https://x.com/creator/status/112233")
    assert isinstance(res, dict)
