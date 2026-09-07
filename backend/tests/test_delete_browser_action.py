import pytest
from unittest.mock import AsyncMock, MagicMock
from xbot.browser.actions.delete_action import DeleteTweet

@pytest.mark.asyncio
async def test_delete_tweet_success():
    page = AsyncMock()
    page.url = "https://x.com/jackds1234/status/123456789"
    page.goto = AsyncMock()
    
    # Mock tweet element
    mock_tweet = AsyncMock()
    mock_caret = AsyncMock()
    mock_tweet.query_selector = AsyncMock(return_value=mock_caret)
    page.query_selector_all = AsyncMock(return_value=[mock_tweet])
    
    # Mock delete menu item and confirm button
    mock_delete_menu = AsyncMock()
    page.query_selector = AsyncMock(return_value=mock_delete_menu)
    mock_confirm_btn = AsyncMock()
    page.wait_for_selector = AsyncMock(return_value=mock_confirm_btn)
    
    action = DeleteTweet()
    result = await action.execute(page, tweet_url="https://x.com/jackds1234/status/123456789")
    
    assert result["status"] == "success"
    assert result["deleted"] is True
    assert result["tweet_id"] == "123456789"
    page.goto.assert_called_once_with("https://x.com/jackds1234/status/123456789", wait_until="domcontentloaded", timeout=20000)

@pytest.mark.asyncio
async def test_delete_tweet_missing_url_and_id():
    page = AsyncMock()
    action = DeleteTweet()
    result = await action.execute(page)
    
    assert result["status"] == "failed"
    assert result["deleted"] is False
    assert result["error"] == "missing_target_url"

@pytest.mark.asyncio
async def test_delete_tweet_article_not_found():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=[])
    page.wait_for_selector = AsyncMock(return_value=None)
    
    action = DeleteTweet()
    result = await action.execute(page, tweet_url="https://x.com/jackds1234/status/123456789")
    
    assert result["status"] == "failed"
    assert result["deleted"] is False
    assert result["error"] == "tweet_not_found"
