from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from xbot.browser.actions.x_actions import (
    BrowseFeed,
    ComposePost,
    FollowUser,
    LikeTweet,
    ReplyToTweet,
    Retweet,
    SearchQuery,
)
from xbot.browser.manager import BrowserManager

from .mock_x_server import ThreadedUvicorn


@pytest.fixture(scope="module")
def mock_x_server() -> Generator[str, None, None]:
    """Starts the mock X server on port 9999."""
    server = ThreadedUvicorn(host="127.0.0.1", port=9999)
    server.start()
    yield "http://127.0.0.1:9999"
    server.stop()


@pytest.mark.asyncio
async def test_x_actions_integration(
    mock_x_server: str, tmp_path: Path
) -> None:
    """
    Executes and validates the complete library of browser actions
    against the local mock X server.
    """
    manager = BrowserManager()
    await manager.start()

    profile_slug = "integration_test_profile"
    manager.release_lock(profile_slug)
    assert manager.acquire_lock(profile_slug) is True

    # 1. Spawn persistent context and create page
    context = await manager.get_context(profile_slug)
    
    import httpx
    async def route_x_to_mock(route: Any) -> None:
        url = route.request.url
        if url.startswith("https://x.com/"):
            mock_url = url.replace("https://x.com/", f"{mock_x_server}/")
            async with httpx.AsyncClient() as client:
                response = await client.get(mock_url)
                headers = {
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() not in ("transfer-encoding", "content-encoding")
                }
                await route.fulfill(
                    status=response.status_code,
                    headers=headers,
                    body=response.content,
                )
        else:
            await route.continue_()

    await context.route("https://x.com/**", route_x_to_mock)
    page = await context.new_page()

    try:
        # A. BrowseFeed Action
        await page.goto("https://x.com/home")
        browse = BrowseFeed(screenshot_dir=str(tmp_path))
        tweets = await browse.execute(page, max_scrolls=1)
        assert len(tweets) >= 2
        assert any("async Python" in t["text"] for t in tweets)

        # B. ComposePost Action
        compose = ComposePost(screenshot_dir=str(tmp_path))
        success = await compose.execute(page, text="Checking action library!")
        assert success is True

        # Verify new tweet was prepended to feed
        tweets_after = await page.evaluate(
            """() => {
                const els = document.querySelectorAll(
                    '[data-testid="tweet"] [data-testid="tweetText"]'
                );
                return Array.from(els).map(el => el.textContent);
            }"""
        )
        assert "Checking action library!" in tweets_after

        # C. LikeTweet Action
        like = LikeTweet(screenshot_dir=str(tmp_path))
        liked = await like.execute(page, tweet_index=0)
        assert liked is True

        # D. ReplyToTweet Action
        reply = ReplyToTweet(screenshot_dir=str(tmp_path))
        replied = await reply.execute(
            page, reply_text="Replying to post!", tweet_index=0
        )
        assert replied is True

        # E. Retweet Action
        retweet = Retweet(screenshot_dir=str(tmp_path))
        retweeted = await retweet.execute(page, tweet_index=0)
        assert retweeted is True

        # F. FollowUser Action
        follow = FollowUser(screenshot_dir=str(tmp_path))
        # Note: FollowUser navigates to f"https://x.com/{username}".
        # To make it hit our mock server, we override the URL formation.
        # But wait! Since FollowUser has:
        # profile_url = f"https://x.com/{clean_username}"
        # Let's call FollowUser which navigates to https://x.com/alice_dev
        followed = await follow.execute(page, username="alice_dev")
        assert followed is True

        # G. SearchQuery Action
        # SearchQuery has: search_url = f"https://x.com/search?q={query}&f=live"
        search = SearchQuery(screenshot_dir=str(tmp_path))
        results = await search.execute(page, query="rustlang")
        assert len(results) >= 2
        assert any("SearchResult" in r["text"] for r in results)

    finally:
        await context.close()
        manager.release_lock(profile_slug)
        await manager.stop()
