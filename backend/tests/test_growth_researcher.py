import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from xbot.growth.growth_researcher import (
    is_growth_research_due,
    scrape_f4f_posts_from_x,
    synthesize_growth_ideas_with_chatgpt,
    save_growth_ideas,
    run_f4f_growth_research,
    RESEARCH_INTERVAL_SECONDS,
)
from xbot.container import Container
from xbot.contracts.browser import ActionResult, BrowserActionType, BrowserResponse, ScrapeResult, TweetData
from xbot.ai.growth_post_generator import get_active_archetypes, enforce_hashtag_count


def test_is_growth_research_due():
    mock_redis = MagicMock()
    now_ts = int(time.time())

    # 1. Recent timestamp -> Not due
    mock_redis.get.return_value = str(now_ts - 3600)  # 1 hour ago
    with patch("xbot.growth.growth_researcher.IDEAS_CACHE_FILE") as mock_file:
        mock_file.exists.return_value = True
        assert is_growth_research_due(mock_redis) is False

    # 2. Timestamp older than 3 days -> Due
    mock_redis.get.return_value = str(now_ts - (RESEARCH_INTERVAL_SECONDS + 100))
    assert is_growth_research_due(mock_redis) is True


@pytest.mark.asyncio
async def test_scrape_f4f_posts_from_x():
    mock_browser = AsyncMock()
    mock_browser.execute.return_value = BrowserResponse(
        status="success",
        action=BrowserActionType.SEARCH,
        scrape=ScrapeResult(
            tweets=[
                TweetData(
                    tweet_id="123",
                    url="https://x.com/user/status/123",
                    handle="growth_creator",
                    text="Connecting with all builders today! #F4F #500Followers follow back active",
                    hashtags=["#F4F", "#500Followers"],
                    media_urls=["https://pbs.twimg.com/media/test.jpg"],
                    metrics={"likes": 42, "retweets": 12},
                )
            ]
        ),
    )
    mock_container = Container(browser=mock_browser, llm=AsyncMock(), guard=MagicMock())

    posts = await scrape_f4f_posts_from_x(mock_container, profile_slug="test_profile1", max_posts=5)
    assert len(posts) == 1
    assert posts[0]["author"] == "growth_creator"
    assert "#F4F" in posts[0]["hashtags"]
    assert len(posts[0]["media_urls"]) == 1


@pytest.mark.asyncio
async def test_synthesize_growth_ideas_with_chatgpt():
    mock_posts = [
        {
            "text": "Building the future on X! Drop your handle below. #F4F #500Followers",
            "author": "tech_builder",
            "hashtags": ["#F4F", "#500Followers"],
            "media_urls": ["https://pbs.twimg.com/media/1.png"],
            "likes": 100,
            "retweets": 25,
            "replies": 50,
        }
    ]

    mock_json_response = {
        "analyzed_posts_count": 1,
        "winning_hashtags": ["#F4F", "#500Followers", "#FollowForFollow"],
        "discovered_archetypes": [
            {
                "name": "MUTUALS_DISCOVERY_LOUNGE",
                "description": "Interactive mutuals check",
                "directive": "Ask creators to connect as mutuals",
                "hook_example": "Looking for active mutuals building in public.",
            }
        ],
        "discovered_image_concepts": [
            {
                "title": "3D Glowing Mutuals Network",
                "prompt": "Modern 3D conceptual art of an expanding luminous creator network graph, glowing follow button, zero humans.",
            }
        ],
        "high_converting_ctas": ["Drop your handle below—connecting with all active accounts."],
        "key_insights": ["Posts with #F4F and interactive questions have 3x replies."],
    }

    mock_bridge = MagicMock()
    mock_bridge.ask = AsyncMock(return_value={"text": json.dumps(mock_json_response)})

    with patch("xbot.growth.growth_researcher.get_chatgpt_instance", return_value=mock_bridge):
        ideas = await synthesize_growth_ideas_with_chatgpt(mock_posts)
        assert ideas["analyzed_posts_count"] == 1
        assert "#F4F" in ideas["winning_hashtags"]
        assert len(ideas["discovered_archetypes"]) == 1
        assert ideas["discovered_archetypes"][0]["name"] == "MUTUALS_DISCOVERY_LOUNGE"


def test_save_and_load_discovered_ideas(tmp_path):
    mock_ideas = {
        "winning_hashtags": ["#F4F", "#FollowBack", "#500Followers"],
        "discovered_archetypes": [
            {
                "name": "TEST_GROWTH_RADAR",
                "directive": "Test directive for radar",
            }
        ],
        "discovered_image_concepts": [
            {
                "title": "Test 3D Node",
                "prompt": "Modern 3D glowing interaction node, zero humans.",
            }
        ],
    }

    target_file = tmp_path / "f4f_growth_ideas.json"
    save_growth_ideas(mock_ideas, output_path=target_file)

    with patch("xbot.ai.growth_post_generator.IDEAS_CACHE_FILE", target_file):
        archetypes, prompts = get_active_archetypes()
        assert "TEST_GROWTH_RADAR" in archetypes
        assert prompts["TEST_GROWTH_RADAR"] == "Test directive for radar"


@pytest.mark.asyncio
async def test_run_f4f_growth_research_flow(tmp_path):
    mock_browser = AsyncMock()
    mock_browser.execute.return_value = BrowserResponse(
        status="success",
        action=BrowserActionType.SEARCH,
        scrape=ScrapeResult(
            tweets=[
                TweetData(
                    tweet_id="123",
                    url="https://x.com/user/status/123",
                    handle="builder",
                    text="Follow for follow community thread! Let's reach 500 together! #F4F #500Followers",
                    hashtags=["#F4F", "#500Followers"],
                    media_urls=["https://pbs.twimg.com/media/test.jpg"],
                    metrics={"likes": 30, "retweets": 5},
                )
            ]
        ),
    )
    mock_guard = MagicMock()
    mock_guard.r = MagicMock()
    mock_guard.r.get.return_value = None

    mock_container = Container(browser=mock_browser, llm=AsyncMock(), guard=mock_guard)

    mock_ideas = {
        "winning_hashtags": ["#F4F", "#FollowForFollow", "#500Followers"],
        "discovered_archetypes": [{"name": "COMMUNITY_LADDER", "directive": "Grow together"}],
        "discovered_image_concepts": [{"title": "3D Node", "prompt": "3D follow node"}],
    }

    with patch("xbot.growth.growth_researcher.synthesize_growth_ideas_with_chatgpt", AsyncMock(return_value=mock_ideas)):
        target_file = tmp_path / "f4f_growth_ideas.json"
        with patch("xbot.growth.growth_researcher.IDEAS_CACHE_FILE", target_file):
            res = await run_f4f_growth_research(profile_slug="test_profile1", force=True, container=mock_container)
            assert res["status"] == "success"
            assert res["scraped_count"] == 1
            assert res["archetypes_count"] == 1
            assert target_file.exists()
