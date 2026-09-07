from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.async_api import async_playwright

from xbot.browser.actions.x_actions import ReplyToTweet


THREAD_WITH_MEDIA_AND_COMMENTS_HTML = """
<!DOCTYPE html>
<html>
<head><title>Tweet Thread</title></head>
<body>
    <!-- Root Target Tweet -->
    <div data-testid="tweet">
        <div data-testid="User-Name">
            <a href="/alice_tech">Alice Dev <span>@alice_tech</span></a>
        </div>
        <div data-testid="tweetText">
            Building the future of AI agents with Python! Check this architecture breakdown.
        </div>
        <!-- Media Images & Video -->
        <div data-testid="tweetPhoto">
            <img src="https://pbs.twimg.com/media/arch_diagram123.jpg" alt="Architecture diagram showing async agent loop" />
        </div>
        <div data-testid="videoPlayer">
            <video src="https://video.twimg.com/demo_preview.mp4"></video>
        </div>
        <!-- Profile / emoji images to be ignored -->
        <img src="https://pbs.twimg.com/profile_images/alice_avatar.jpg" alt="Profile image" />
        <img src="https://abs.twimg.com/emoji/v2/svg/1f525.svg" alt="🔥" />

        <!-- Metrics -->
        <a href="/alice_tech/status/100/analytics" aria-label="12.5K Views. View Tweet analytics">
            <span data-testid="app-text-transition-container">12.5K</span>
        </a>
        <button data-testid="like" aria-label="1,200 Likes. Like">
            <span>1.2K</span>
        </button>
        <button data-testid="reply" aria-label="45 Replies. Reply">
            <span>45</span>
        </button>
        <button data-testid="retweet" aria-label="88 Reposts. Repost">
            <span>88</span>
        </button>
    </div>

    <!-- Comment 1: Moderate likes -->
    <div data-testid="tweet">
        <div data-testid="User-Name">
            <a href="/bob_dev">Bob <span>@bob_dev</span></a>
        </div>
        <div data-testid="tweetText">
            Super clean architecture! How do you handle failure states?
        </div>
        <button data-testid="like" aria-label="150 Likes. Like">
            <span>150</span>
        </button>
    </div>

    <!-- Comment 2: Highest likes (should be sorted first) -->
    <div data-testid="tweet">
        <div data-testid="User-Name">
            <a href="/carol_ai">Carol AI <span>@carol_ai</span></a>
        </div>
        <div data-testid="tweetText">
            This pattern reduces token latency by at least 40% in production.
        </div>
        <button data-testid="like" aria-label="3.5K Likes. Like">
            <span>3.5K</span>
        </button>
    </div>

    <!-- Comment 3: Low likes -->
    <div data-testid="tweet">
        <div data-testid="User-Name">
            <a href="/dave_coder">Dave <span>@dave_coder</span></a>
        </div>
        <div data-testid="tweetText">
            Bookmarked for later reading.
        </div>
        <button data-testid="like" aria-label="5 Likes. Like">
            <span>5</span>
        </button>
    </div>
</body>
</html>
"""

MINIMAL_TWEET_HTML = """
<!DOCTYPE html>
<html>
<head><title>Minimal Tweet</title></head>
<body>
    <div data-testid="tweet">
        <div data-testid="User-Name">
            <span>@minimal_user</span>
        </div>
        <div data-testid="tweetText">
            Just a simple text post without metrics or comments.
        </div>
    </div>
</body>
</html>
"""

MILLIONS_METRICS_HTML = """
<!DOCTYPE html>
<html>
<head><title>Viral Tweet</title></head>
<body>
    <div data-testid="tweet">
        <div data-testid="User-Name">
            <a href="/tech_giant">Tech Giant <span>@tech_giant</span></a>
        </div>
        <div data-testid="tweetText">
            Announcing our new open-weights reasoning model.
        </div>
        <div data-testid="tweetPhoto">
            <img src="https://pbs.twimg.com/media/benchmark_chart.png" alt="Benchmark chart against frontier models" />
            <img src="https://pbs.twimg.com/media/generic_img.png" alt="Image" />
            <img src="https://pbs.twimg.com/media/generic_img2.png" alt="" />
        </div>
        <a href="/analytics" aria-label="2.4M Views">
            <span>2.4M</span>
        </a>
        <button data-testid="like" aria-label="48.5K Likes">
            <span>48.5K</span>
        </button>
        <button data-testid="reply" aria-label="1.8K Replies">
            <span>1.8K</span>
        </button>
        <button data-testid="retweet" aria-label="12.3K Reposts">
            <span>12.3K</span>
        </button>
    </div>

    <!-- Duplicate comment test -->
    <div data-testid="tweet">
        <div data-testid="User-Name"><span>@user1</span></div>
        <div data-testid="tweetText">First identical comment</div>
        <button data-testid="like"><span>10</span></button>
    </div>
    <div data-testid="tweet">
        <div data-testid="User-Name"><span>@user2</span></div>
        <div data-testid="tweetText">First identical comment</div>
        <button data-testid="like"><span>20</span></button>
    </div>
</body>
</html>
"""

EMPTY_HTML = """
<!DOCTYPE html>
<html>
<head><title>Empty Page</title></head>
<body>
    <p>Nothing here</p>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_scrape_target_tweet_context_full(tmp_path: Path) -> None:
    """Tests comprehensive scraping of root tweet text, author, metrics, media alts, and sorted top comments."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(THREAD_WITH_MEDIA_AND_COMMENTS_HTML)

        action = ReplyToTweet(screenshot_dir=str(tmp_path))
        result = await action.scrape_target_tweet_context(page, target_idx=0)

        assert result is not None
        assert isinstance(result, dict)

        # 1. Author and Text
        assert result["author"] == "alice_tech"
        assert "Building the future of AI agents" in result["text"]

        # 2. Metrics
        assert result["views"] == 12500
        assert result["impressions"] == 12500
        assert result["likes"] == 1200
        assert result["replies"] == 45
        assert result["retweets"] == 88

        # 3. Media URLs & Alts
        assert any("arch_diagram123.jpg" in u for u in result["media_urls"])
        assert any("demo_preview.mp4" in u for u in result["media_urls"])
        assert "Architecture diagram showing async agent loop" in result["media_alts"]
        assert not any("alice_avatar" in u for u in result["media_urls"])
        assert not any("1f525.svg" in u for u in result["media_urls"])

        # 4. Top Comments (structured dicts, sorted by likes descending)
        top_comments = result["top_comments"]
        assert isinstance(top_comments, list)
        assert len(top_comments) == 3

        # Carol (3.5K likes) should be 1st
        assert top_comments[0]["author"] == "carol_ai"
        assert "reduces token latency" in top_comments[0]["text"]
        assert top_comments[0]["likes"] == 3500

        # Bob (150 likes) should be 2nd
        assert top_comments[1]["author"] == "bob_dev"
        assert "Super clean architecture" in top_comments[1]["text"]
        assert top_comments[1]["likes"] == 150

        # Dave (5 likes) should be 3rd
        assert top_comments[2]["author"] == "dave_coder"
        assert "Bookmarked" in top_comments[2]["text"]
        assert top_comments[2]["likes"] == 5

        await browser.close()


@pytest.mark.asyncio
async def test_scrape_target_tweet_context_minimal(tmp_path: Path) -> None:
    """Tests scraping when root tweet has no metrics, no media, and no comments."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(MINIMAL_TWEET_HTML)

        action = ReplyToTweet(screenshot_dir=str(tmp_path))
        result = await action.scrape_target_tweet_context(page, target_idx=0)

        assert result["author"] == "minimal_user"
        assert result["text"] == "Just a simple text post without metrics or comments."
        assert result["views"] == 0
        assert result["impressions"] == 0
        assert result["likes"] == 0
        assert result["replies"] == 0
        assert result["retweets"] == 0
        assert result["top_comments"] == []
        assert result["media_urls"] == []
        assert result["media_alts"] == []

        await browser.close()


@pytest.mark.asyncio
async def test_scrape_target_tweet_context_viral_metrics_and_dedup(tmp_path: Path) -> None:
    """Tests parsing of M/K scale metrics, alt text filtering, and comment deduplication."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(MILLIONS_METRICS_HTML)

        action = ReplyToTweet(screenshot_dir=str(tmp_path))
        result = await action.scrape_target_tweet_context(page, target_idx=0)

        assert result["author"] == "tech_giant"
        assert result["views"] == 2_400_000
        assert result["impressions"] == 2_400_000
        assert result["likes"] == 48_500
        assert result["replies"] == 1_800
        assert result["retweets"] == 12_300

        # Alts: only the genuine alt should be kept, 'Image' or empty filtered out
        assert result["media_alts"] == ["Benchmark chart against frontier models"]
        assert any("benchmark_chart.png" in u for u in result["media_urls"])

        # Top comments: deduplicated identical text
        assert len(result["top_comments"]) == 1
        assert result["top_comments"][0]["author"] == "user1"

        await browser.close()


@pytest.mark.asyncio
async def test_scrape_target_tweet_context_empty_and_out_of_bounds(tmp_path: Path) -> None:
    """Tests robustness on empty page or invalid target_idx."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(EMPTY_HTML)

        action = ReplyToTweet(screenshot_dir=str(tmp_path))
        result_empty = await action.scrape_target_tweet_context(page, target_idx=0)
        assert result_empty == {}

        # Out of bounds on minimal page
        await page.set_content(MINIMAL_TWEET_HTML)
        result_oob = await action.scrape_target_tweet_context(page, target_idx=10)
        assert result_oob == {}

        await browser.close()
