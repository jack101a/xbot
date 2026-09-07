"""
Unit tests for xbot.container and xbot.infra adapters.
"""
import pytest
from unittest.mock import AsyncMock, patch

from xbot.container import Container, get_container, reset_container
from xbot.contracts.browser import (
    BrowserActionType,
    BrowserRequest,
    BrowserResponse,
)
from xbot.contracts.ports import BrowserPort, LLMPort, GuardPort
from xbot.infra.browser.adapter import PlaywrightBrowserAdapter, _normalize_browser_output


def test_normalize_browser_output_scrape():
    req = BrowserRequest(
        profile_slug="profile_1",
        action=BrowserActionType.SCRAPE_FEED,
    )
    raw = {
        "status": "success",
        "tweets": [
            {"tweet_id": "111", "url": "https://x.com/post/111", "handle": "alex", "text": "Post text"}
        ],
        "trends": [{"topic": "#AI", "tweet_count": "10K"}],
        "notifications": [
            {"kind": "like", "actor_handle": "sam", "text": "Liked your post"}
        ]
    }
    resp = _normalize_browser_output(req, raw)
    assert resp.status == "success"
    assert resp.action == BrowserActionType.SCRAPE_FEED
    assert resp.scrape is not None
    assert len(resp.scrape.tweets) == 1
    assert resp.scrape.tweets[0].tweet_id == "111"
    assert len(resp.scrape.trends) == 1
    assert len(resp.scrape.notifications) == 1


def test_normalize_browser_output_action():
    req = BrowserRequest(
        profile_slug="profile_1",
        action=BrowserActionType.LIKE,
        params={"tweet_url": "https://x.com/post/123"}
    )
    raw = {
        "status": "success",
        "detail": "Liked tweet 123",
        "tweet_id": "123"
    }
    resp = _normalize_browser_output(req, raw)
    assert resp.status == "success"
    assert resp.action == BrowserActionType.LIKE
    assert resp.action_result is not None
    assert resp.action_result.detail == "Liked tweet 123"
    assert resp.action_result.target_id == "123"


def test_container_injection():
    reset_container()
    mock_browser = AsyncMock(spec=BrowserPort)
    mock_llm = AsyncMock(spec=LLMPort)
    mock_guard = AsyncMock(spec=GuardPort)

    c = get_container(browser=mock_browser, llm=mock_llm, guard=mock_guard)
    assert c.browser is mock_browser
    assert c.llm is mock_llm
    assert c.guard is mock_guard

    # Verify singleton
    c2 = get_container()
    assert c2 is c
    reset_container()
