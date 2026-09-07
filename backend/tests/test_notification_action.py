from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from xbot.browser.actions.notification_action import ScrapeNotifications, NotificationItem


@pytest.mark.asyncio
async def test_scrape_notifications_follow_event():
    mock_page = AsyncMock()
    mock_cell = AsyncMock()
    mock_cell.inner_text.return_value = "TechBuilder followed you"
    
    # Mock links
    mock_link = AsyncMock()
    mock_link.get_attribute.return_value = "/TechBuilder"
    mock_cell.query_selector_all.return_value = [mock_link]
    mock_cell.query_selector.return_value = MagicMock()  # Verified icon

    mock_page.query_selector_all.return_value = [mock_cell]
    mock_page.wait_for_selector.return_value = True

    action = ScrapeNotifications()
    notifications = await action.execute(mock_page, limit=5)

    assert len(notifications) == 1
    assert notifications[0]["notification_type"] == "follow"
    assert notifications[0]["author_handle"] == "TechBuilder"
    assert notifications[0]["is_verified"] is True


@pytest.mark.asyncio
async def test_scrape_notifications_reply_event():
    mock_page = AsyncMock()
    mock_cell = AsyncMock()
    mock_cell.inner_text.return_value = "Great breakdown! Would love to see benchmarks."

    # Mock tweet container
    mock_article = AsyncMock()
    mock_cell.query_selector.side_effect = lambda sel: mock_article if "article" in sel else None

    # Mock time element for tweet URL
    mock_time = MagicMock()
    mock_parent_link = AsyncMock()
    mock_parent_link.get_attribute.return_value = "/sama/status/1892837461928374"
    mock_time.evaluate_handle = AsyncMock(return_value=mock_parent_link)
    mock_article.query_selector.side_effect = lambda sel: mock_time if "time" in sel else None

    # Mock author link
    mock_author_link = AsyncMock()
    mock_author_link.get_attribute.return_value = "/sama"
    mock_article.query_selector_all.return_value = [mock_author_link]

    mock_page.query_selector_all.return_value = [mock_cell]
    mock_page.wait_for_selector.return_value = True

    action = ScrapeNotifications()
    notifications = await action.execute(mock_page, limit=5)

    assert len(notifications) == 1
    assert notifications[0]["notification_type"] == "reply"
    assert notifications[0]["author_handle"] == "sama"
    assert "1892837461928374" in notifications[0]["tweet_url"]
