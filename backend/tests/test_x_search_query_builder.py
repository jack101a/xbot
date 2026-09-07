import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from xbot.search import (
    SearchCategory,
    SearchFilters,
    SearchMatrixStrategy,
    SearchTarget,
    XSearchQueryBuilder,
)
from xbot.search.query_builder import _normalize_engagement_tier


def test_engagement_normalization():
    """Verify Earlybird engagement tier snapping to 50, 100, 500, 1000."""
    assert _normalize_engagement_tier(10) == 50
    assert _normalize_engagement_tier(25) == 50
    assert _normalize_engagement_tier(50) == 50
    assert _normalize_engagement_tier(51) == 100
    assert _normalize_engagement_tier(100) == 100
    assert _normalize_engagement_tier(250) == 500
    assert _normalize_engagement_tier(500) == 500
    assert _normalize_engagement_tier(900) == 1000
    assert _normalize_engagement_tier(5000) == 1000


def test_web_target_query_compilation():
    """Verify Web target uses empirically verified web operators and excludes API syntax."""
    builder = (
        XSearchQueryBuilder(target=SearchTarget.WEB)
        .exact_phrase("Harry Potter")
        .keyword("Hogwarts")
        .exclude("spoilers")
        .min_faves(50)
        .min_retweets(10)
        .exclude_retweets(True)
        .require_media(True)
        .require_verified(True)
        .since("2026-08-28")
        .until("2026-09-04")
    )

    query = builder.build_query_string()

    # Web operators
    assert '"Harry Potter"' in query
    assert "Hogwarts" in query
    assert "-spoilers" in query
    assert "min_faves:50" in query
    assert "min_retweets:10" in query
    assert "-filter:retweets" in query
    assert "filter:media" in query
    assert "filter:verified" in query
    assert "since:2026-08-28" in query
    assert "until:2026-09-04" in query

    # Must NOT contain API operators or broken legacy operators
    assert "min_likes:" not in query
    assert "-is:retweet" not in query
    assert "has:media" not in query
    assert "-filter:nativereposts" not in query
    assert "filter:images" not in query


def test_api_target_query_compilation():
    """Verify API target uses official Twitter API v2 operators."""
    builder = (
        XSearchQueryBuilder(target=SearchTarget.API)
        .keyword("OpenAI")
        .min_faves(100)
        .min_retweets(20)
        .exclude_retweets(True)
        .require_media(True)
        .require_verified(True)
    )

    query = builder.build_query_string()

    assert "OpenAI" in query
    assert "min_likes:100" in query
    assert "min_reposts:20" in query
    assert "-is:retweet" in query
    assert "has:media" in query
    assert "is:verified" in query

    # Must NOT contain Web operators
    assert "min_faves:" not in query
    assert "-filter:retweets" not in query
    assert "filter:media" not in query


def test_search_matrix_tier1_viral_anchor():
    """Verify SearchMatrixStrategy Tier 1 viral anchor query configuration."""
    builder = SearchMatrixStrategy.create_viral_anchor_query(
        topic="Dune Messiah",
        min_faves=100,
        max_age_days=7,
        require_media=True,
    )
    query = builder.build_query_string()

    assert '"Dune Messiah"' in query
    assert "min_faves:100" in query
    assert "-filter:retweets" in query
    assert "filter:media" in query
    assert "since:" in query
    assert builder.filters.category == SearchCategory.TOP


def test_search_matrix_tier2_realtime_buzz():
    """Verify SearchMatrixStrategy Tier 2 real-time buzz query with &f=live."""
    builder = SearchMatrixStrategy.create_realtime_buzz_query(
        topic="GTA 6",
        max_age_days=2,
    )
    query = builder.build_query_string()

    assert "GTA 6" in query
    assert "-filter:retweets" in query
    assert "min_faves:" not in query  # Realtime buzz avoids strict faves
    assert builder.filters.category == SearchCategory.LATEST

    url = builder.build_url()
    assert "&f=live" in url


def test_search_matrix_tier3_verified_creator():
    """Verify SearchMatrixStrategy Tier 3 verified creator discovery."""
    builder = SearchMatrixStrategy.create_verified_creator_query(
        niche="Artificial Intelligence",
        min_faves=50,
        max_age_days=14,
    )
    query = builder.build_query_string()

    assert "Artificial Intelligence" in query
    assert "filter:verified" in query
    assert "min_faves:50" in query
    assert "-filter:retweets" in query
    assert builder.filters.category == SearchCategory.TOP


def test_search_matrix_tier4_media_harvester():
    """Verify SearchMatrixStrategy Tier 4 media harvesting."""
    builder = SearchMatrixStrategy.create_media_harvester_query(
        topic="Cyberpunk 2077",
        max_age_days=10,
    )
    query = builder.build_query_string()

    assert "Cyberpunk 2077" in query
    assert "filter:media" in query
    assert "-filter:retweets" in query
    assert builder.filters.category == SearchCategory.MEDIA

    url = builder.build_url()
    assert "&f=media" in url


def test_adaptive_fallback_progression():
    """Verify fallback relaxation sequence drops constraints in a controlled order."""
    builder = (
        XSearchQueryBuilder(target=SearchTarget.WEB)
        .exact_phrase("Quantum Computing")
        .min_faves(500)
        .require_media(True)
        .exclude_retweets(True)
        .since("2026-08-01")
    )

    fallbacks = builder.get_adaptive_fallback_queries()

    # Should have progressive relaxation steps
    assert len(fallbacks) >= 3

    # Step 1: primary strict
    assert "min_faves:500" in fallbacks[0][0]
    assert "filter:media" in fallbacks[0][0]

    # Step 2: relaxed faves to 50
    assert "min_faves:50" in fallbacks[1][0]

    # Final step: live unranked buzz fallback
    last_q, last_cat = fallbacks[-1]
    assert "Quantum Computing" in last_q
    assert last_cat == SearchCategory.LATEST


@pytest.mark.asyncio
async def test_search_query_execution_with_filters():
    """Verify SearchQuery executes correct URL with filter tab & relaxation."""
    from xbot.browser.actions.feed_action import SearchQuery

    mock_page = AsyncMock()
    mock_page.url = "https://x.com/search?q=test"
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()

    action = SearchQuery(screenshot_dir="/tmp")

    # Patch BrowseFeed.execute to return dummy tweets
    with patch("xbot.browser.actions.feed_action.BrowseFeed.execute", new_callable=AsyncMock) as mock_feed:
        mock_feed.return_value = [{"text": "Found live tweet", "author": "dev"}]

        results = await action.execute(
            page=mock_page,
            query="Apple Vision Pro",
            search_filter="live",
            auto_relax=True,
        )

        assert len(results) == 1
        assert results[0]["text"] == "Found live tweet"
        mock_page.goto.assert_called_once()
        nav_url = mock_page.goto.call_args[0][0]
        assert "https://x.com/search?q=" in nav_url
        assert "&f=live" in nav_url
