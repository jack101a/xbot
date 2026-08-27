from collections.abc import Generator
import os
from pathlib import Path
from typing import Any

import pytest
from playwright.async_api import async_playwright

from xbot.browser.actions.x_actions import (
    BrowseFeed,
    ComposePost,
    FollowUser,
    LikeTweet,
    QuoteTweet,
    ReplyToTweet,
    Retweet,
    SearchQuery,
    _attach_gif_if_requested,
    _attach_media_files,
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
                return Array.from(els).map(el => el.textContent.trim());
            }"""
        )
        assert any("Checking action library!" in t for t in tweets_after)

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


HTML_COMPOSER_WITH_GIF = """
<!DOCTYPE html>
<html>
<head><title>Composer with GIF</title></head>
<body>
    <div id="home-composer">
        <div data-testid="tweetTextarea_0" role="textbox" contenteditable="true"></div>
        <button data-testid="gifSearchButton" aria-label="Add a GIF" id="gif-btn">Add a GIF</button>
        <input type="file" data-testid="fileInput" style="display:none;" />
        <button data-testid="tweetButton" id="post-btn">Post</button>
    </div>

    <!-- GIF Picker Modal (hidden initially) -->
    <div id="gif-modal" style="display:none;">
        <input data-testid="searchBox" placeholder="Search GIFs" id="gif-search" />
        <div data-testid="gifSearchResults" id="results">
            <div data-testid="gifItem" class="gif-item" id="gif-1">
                <img src="https://media.tenor.com/1.gif" alt="celebrate" />
            </div>
            <div data-testid="gifItem" class="gif-item" id="gif-2">
                <img src="https://media.tenor.com/2.gif" alt="excited" />
            </div>
        </div>
    </div>

    <script>
        document.getElementById('gif-btn').addEventListener('click', () => {
            document.getElementById('gif-modal').style.display = 'block';
        });
        document.querySelectorAll('.gif-item').forEach(el => {
            el.addEventListener('click', () => {
                document.getElementById('gif-modal').style.display = 'none';
                const attached = document.createElement('div');
                attached.setAttribute('data-testid', 'attachments');
                attached.innerText = 'GIF attached';
                document.getElementById('home-composer').appendChild(attached);
            });
        });
        document.getElementById('post-btn').addEventListener('click', () => {
            const status = document.createElement('div');
            status.id = 'post-success';
            document.body.appendChild(status);
        });
    </script>
</body>
</html>
"""

HTML_REPLY_WITH_GIF = """
<!DOCTYPE html>
<html>
<head><title>Reply with GIF</title></head>
<body>
    <div data-testid="tweet">
        <div data-testid="tweetText">Target post to reply to</div>
        <button data-testid="reply" id="reply-btn">Reply</button>
    </div>

    <div id="reply-modal" style="display:none;">
        <div data-testid="tweetTextarea_0" role="textbox" contenteditable="true"></div>
        <button data-testid="gifSearchButton" aria-label="Add a GIF" id="gif-btn">Add a GIF</button>
        <button data-testid="tweetButtonInline" id="inline-submit-btn">Reply</button>

        <div id="gif-modal" style="display:none;">
            <input data-testid="searchBox" placeholder="Search GIFs" id="gif-search" />
            <div data-testid="gifSearchResults">
                <div data-testid="gifItem" class="gif-item">
                    <img src="https://media.tenor.com/reply.gif" alt="reply gif" />
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('reply-btn').addEventListener('click', () => {
            document.getElementById('reply-modal').style.display = 'block';
        });
        document.getElementById('gif-btn').addEventListener('click', () => {
            document.getElementById('gif-modal').style.display = 'block';
        });
        document.querySelectorAll('.gif-item').forEach(el => {
            el.addEventListener('click', () => {
                document.getElementById('gif-modal').style.display = 'none';
            });
        });
    </script>
</body>
</html>
"""

HTML_QUOTE_WITH_GIF = """
<!DOCTYPE html>
<html>
<head><title>Quote Tweet with GIF</title></head>
<body>
    <div data-testid="tweet">
        <div data-testid="tweetText">Target Tweet for Quote</div>
        <button data-testid="retweet" id="rt-btn">Retweet</button>
    </div>

    <div data-testid="Dropdown" role="menu" style="display:none;" id="rt-menu">
        <div role="menuitem" id="quote-opt">Quote</div>
    </div>

    <div role="dialog" id="quote-modal" style="display:none;">
        <div data-testid="tweetTextarea_0" role="textbox" contenteditable="true"></div>
        <button data-testid="gifSearchButton" aria-label="Add a GIF" id="gif-btn">Add a GIF</button>
        <button data-testid="tweetButton" id="quote-submit-btn">Post</button>

        <div id="gif-modal" style="display:none;">
            <input data-testid="searchBox" placeholder="Search GIFs" id="gif-search" />
            <div data-testid="gifSearchResults">
                <div data-testid="gifItem" class="gif-item">
                    <img src="https://media.tenor.com/quote.gif" alt="quote gif" />
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('rt-btn').addEventListener('click', () => {
            document.getElementById('rt-menu').style.display = 'block';
        });
        document.getElementById('quote-opt').addEventListener('click', () => {
            document.getElementById('rt-menu').style.display = 'none';
            document.getElementById('quote-modal').style.display = 'block';
        });
        document.getElementById('gif-btn').addEventListener('click', () => {
            document.getElementById('gif-modal').style.display = 'block';
        });
        document.querySelectorAll('.gif-item').forEach(el => {
            el.addEventListener('click', () => {
                document.getElementById('gif-modal').style.display = 'none';
            });
        });
    </script>
</body>
</html>
"""

HTML_COMPOSER_NO_GIF = """
<!DOCTYPE html>
<html>
<head><title>Composer without GIF</title></head>
<body>
    <div id="home-composer">
        <div data-testid="tweetTextarea_0" role="textbox" contenteditable="true"></div>
        <!-- No GIF search button -->
        <button data-testid="tweetButton">Post</button>
    </div>
</body>
</html>
"""

HTML_REPLY_NO_GIF = """
<!DOCTYPE html>
<html>
<head><title>Reply without GIF</title></head>
<body>
    <div data-testid="tweet">
        <div data-testid="tweetText">Target post</div>
        <button data-testid="reply" id="reply-btn">Reply</button>
    </div>

    <div id="reply-modal" style="display:none;">
        <div data-testid="tweetTextarea_0" role="textbox" contenteditable="true"></div>
        <!-- No GIF button -->
        <button data-testid="tweetButtonInline">Reply</button>
    </div>

    <script>
        document.getElementById('reply-btn').addEventListener('click', () => {
            document.getElementById('reply-modal').style.display = 'block';
        });
    </script>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_attach_gif_direct_success() -> None:
    """Test _attach_gif_if_requested successfully opens picker, searches, and selects a GIF item."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(HTML_COMPOSER_WITH_GIF)

        attached = await _attach_gif_if_requested(page, "celebrate")
        assert attached is True

        await browser.close()


@pytest.mark.asyncio
async def test_attach_gif_empty_query() -> None:
    """Test _attach_gif_if_requested returns False immediately when query is None or empty."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(HTML_COMPOSER_WITH_GIF)

        assert await _attach_gif_if_requested(page, None) is False
        assert await _attach_gif_if_requested(page, "") is False

        await browser.close()


@pytest.mark.asyncio
async def test_attach_gif_fallback_missing_button() -> None:
    """Test _attach_gif_if_requested gracefully returns False when GIF search button does not exist."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(HTML_COMPOSER_NO_GIF)

        attached = await _attach_gif_if_requested(page, "party")
        assert attached is False

        await browser.close()


@pytest.mark.asyncio
async def test_attach_gif_fallback_missing_search_input() -> None:
    """Test _attach_gif_if_requested gracefully returns False when GIF search input cannot be found."""
    broken_modal_html = """
    <!DOCTYPE html>
    <html><body>
        <button data-testid="gifSearchButton" id="btn">GIF</button>
        <div id="modal" style="display:none;"></div>
        <script>
            document.getElementById('btn').addEventListener('click', () => {
                document.getElementById('modal').style.display = 'block';
            });
        </script>
    </body></html>
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(broken_modal_html)

        attached = await _attach_gif_if_requested(page, "fail")
        assert attached is False

        await browser.close()


@pytest.mark.asyncio
async def test_attach_gif_fallback_no_results() -> None:
    """Test _attach_gif_if_requested gracefully returns False when search box exists but results are empty."""
    empty_results_html = """
    <!DOCTYPE html>
    <html><body>
        <button data-testid="gifSearchButton" id="btn">GIF</button>
        <div id="modal" style="display:none;">
            <input data-testid="searchBox" />
            <div data-testid="gifSearchResults"></div>
        </div>
        <script>
            document.getElementById('btn').addEventListener('click', () => {
                document.getElementById('modal').style.display = 'block';
            });
        </script>
    </body></html>
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(empty_results_html)

        attached = await _attach_gif_if_requested(page, "empty")
        assert attached is False

        await browser.close()


@pytest.mark.asyncio
async def test_compose_post_with_gif(tmp_path: Path) -> None:
    """Test ComposePost successfully posts with attached GIF."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(HTML_COMPOSER_WITH_GIF)

        compose = ComposePost(screenshot_dir=str(tmp_path))
        success = await compose.execute(page, text="Celebration post!", gif_query="celebrate")
        assert success is True

        await browser.close()


@pytest.mark.asyncio
async def test_compose_post_with_gif_fallback_to_text(tmp_path: Path) -> None:
    """Test ComposePost falls back to text-only posting when GIF search fails without crashing."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(HTML_COMPOSER_NO_GIF)

        compose = ComposePost(screenshot_dir=str(tmp_path))
        success = await compose.execute(page, text="Fallback text post", gif_query="missing_gif")
        assert success is True

        await browser.close()


@pytest.mark.asyncio
async def test_reply_to_tweet_with_gif(tmp_path: Path) -> None:
    """Test ReplyToTweet successfully attaches GIF and submits reply."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(HTML_REPLY_WITH_GIF)

        reply = ReplyToTweet(screenshot_dir=str(tmp_path))
        success = await reply.execute(page, reply_text="Great point!", tweet_index=0, gif_query="agree")
        assert success is True

        await browser.close()


@pytest.mark.asyncio
async def test_reply_to_tweet_with_gif_fallback_to_text(tmp_path: Path) -> None:
    """Test ReplyToTweet falls back to text-only reply when GIF search fails."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(HTML_REPLY_NO_GIF)

        reply = ReplyToTweet(screenshot_dir=str(tmp_path))
        success = await reply.execute(page, reply_text="Fallback reply", tweet_index=0, gif_query="missing_gif")
        assert success is True

        await browser.close()


@pytest.mark.asyncio
async def test_quote_tweet_with_gif(tmp_path: Path) -> None:
    """Test QuoteTweet successfully searches GIF and quotes tweet."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(HTML_QUOTE_WITH_GIF)

        quote = QuoteTweet(screenshot_dir=str(tmp_path))
        success = await quote.execute(page, quote_text="Thought provoking!", tweet_index=0, gif_query="mind blown")
        assert success is True

        await browser.close()


@pytest.mark.asyncio
async def test_attach_media_files_and_fallback(tmp_path: Path) -> None:
    """Test _attach_media_files with existing and non-existing files."""
    test_img = tmp_path / "test.png"
    test_img.write_bytes(b"dummy image data")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(HTML_COMPOSER_WITH_GIF)

        # 1. Non-existent path returns False
        assert await _attach_media_files(page, ["/tmp/non_existent_file_xyz123.jpg"]) is False
        assert await _attach_media_files(page, None) is False

        # 2. Existing path attaches file
        attached = await _attach_media_files(page, [str(test_img)])
        assert attached is True

        await browser.close()

