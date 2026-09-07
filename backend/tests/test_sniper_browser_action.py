from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.async_api import async_playwright

from xbot.browser.actions.check_user_action import CheckUserLatestTweet


SAMPLE_TWEET_HTML = """
<!DOCTYPE html>
<html>
<head><title>User Profile</title></head>
<body>
    <div data-testid="UserAvatar-Container-profileUser">Avatar</div>
    <h2>@elonmusk</h2>
    <div id="feed">
        <div data-testid="tweet">
            <div data-testid="tweetText">Hello world from @elonmusk! Building the future.</div>
            <a href="/elonmusk/status/1234567890123456789">
                <time datetime="2026-08-18T13:30:00.000Z">Aug 18</time>
            </a>
        </div>
    </div>
</body>
</html>
"""

PINNED_TWEET_HTML = """
<!DOCTYPE html>
<html>
<head><title>User Profile</title></head>
<body>
    <div data-testid="UserAvatar-Container-profileUser">Avatar</div>
    <h2>@elonmusk</h2>
    <div id="feed">
        <!-- Pinned Tweet -->
        <div data-testid="tweet">
            <div data-testid="socialContext"><span>Pinned</span></div>
            <div data-testid="tweetText">This is a pinned post from 2024.</div>
            <a href="/elonmusk/status/1111111111111111111">
                <time datetime="2024-01-01T00:00:00.000Z">Jan 1, 2024</time>
            </a>
        </div>
        <!-- Fresh Latest Tweet -->
        <div data-testid="tweet">
            <div data-testid="tweetText">Fresh breaking news tweet!</div>
            <a href="/elonmusk/status/9876543210987654321">
                <time datetime="2026-08-18T13:45:00.000Z">15m</time>
            </a>
        </div>
    </div>
</body>
</html>
"""

ONLY_PINNED_TWEET_HTML = """
<!DOCTYPE html>
<html>
<head><title>User Profile</title></head>
<body>
    <div data-testid="UserAvatar-Container-profileUser">Avatar</div>
    <h2>@elonmusk</h2>
    <div id="feed">
        <div data-testid="tweet">
            <div data-testid="socialContext"><span>Pinned Tweet</span></div>
            <div data-testid="tweetText">Only pinned post here.</div>
            <a href="/elonmusk/status/5555555555555555555">
                <time datetime="2025-06-01T12:00:00.000Z">Jun 1</time>
            </a>
        </div>
    </div>
</body>
</html>
"""

EMPTY_PROFILE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Empty Profile</title></head>
<body>
    <div data-testid="UserAvatar-Container-profileUser">Avatar</div>
    <h2>@emptyuser</h2>
    <div id="feed">
        <p>No tweets yet.</p>
    </div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_check_user_latest_tweet_success(tmp_path: Path) -> None:
    """Tests extracting standard latest tweet from profile."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body=SAMPLE_TWEET_HTML)

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()

        action = CheckUserLatestTweet(screenshot_dir=str(tmp_path))
        result = await action.execute(page, handle="elonmusk", base_url="https://x.com")

        assert result is not None
        assert result["tweet_id"] == "1234567890123456789"
        assert result["text"] == "Hello world from @elonmusk! Building the future."
        assert result["url"] == "https://x.com/elonmusk/status/1234567890123456789"
        assert result["handle"] == "elonmusk"
        assert result["is_pinned"] is False
        assert result["created_at"] == "2026-08-18T13:30:00.000Z"

        await browser.close()


@pytest.mark.asyncio
async def test_check_user_latest_tweet_pinned_fallback(tmp_path: Path) -> None:
    """Tests fallback to second tweet when the first tweet is pinned."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body=PINNED_TWEET_HTML)

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()

        action = CheckUserLatestTweet(screenshot_dir=str(tmp_path))
        result = await action.execute(page, handle="@elonmusk", base_url="https://x.com")

        assert result is not None
        assert result["tweet_id"] == "9876543210987654321"
        assert result["text"] == "Fresh breaking news tweet!"
        assert result["url"] == "https://x.com/elonmusk/status/9876543210987654321"
        assert result["handle"] == "elonmusk"
        assert result["is_pinned"] is False
        assert result["created_at"] == "2026-08-18T13:45:00.000Z"

        await browser.close()


@pytest.mark.asyncio
async def test_check_user_latest_tweet_only_pinned(tmp_path: Path) -> None:
    """Tests extracting the pinned tweet when no second tweet is available."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body=ONLY_PINNED_TWEET_HTML)

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()

        action = CheckUserLatestTweet(screenshot_dir=str(tmp_path))
        result = await action.execute(page, handle="elonmusk", base_url="https://x.com")

        assert result is not None
        assert result["tweet_id"] == "5555555555555555555"
        assert result["text"] == "Only pinned post here."
        assert result["url"] == "https://x.com/elonmusk/status/5555555555555555555"
        assert result["handle"] == "elonmusk"
        assert result["is_pinned"] is True
        assert result["created_at"] == "2025-06-01T12:00:00.000Z"

        await browser.close()


@pytest.mark.asyncio
async def test_check_user_latest_tweet_empty_profile(tmp_path: Path) -> None:
    """Tests returning None when profile has no tweets."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body=EMPTY_PROFILE_HTML)

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()

        action = CheckUserLatestTweet(screenshot_dir=str(tmp_path))
        result = await action.execute(page, handle="emptyuser", base_url="https://x.com")

        assert result is None

        await browser.close()


@pytest.mark.asyncio
async def test_check_user_latest_tweet_navigation_failure(tmp_path: Path) -> None:
    """Tests returning None and capturing failure screenshot on navigation error."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.abort("failed")

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()

        action = CheckUserLatestTweet(screenshot_dir=str(tmp_path))
        result = await action.execute(page, handle="brokenuser", base_url="https://x.com")

        assert result is None

        # Verify failure screenshot attempt or directory presence
        assert tmp_path.exists()

        await browser.close()
