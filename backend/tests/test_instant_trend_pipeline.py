from datetime import datetime, timedelta
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from xbot.contracts.browser import ActionResult, BrowserActionType, BrowserResponse
from xbot.database import AsyncSessionLocal
from xbot.main import app
from xbot.models.pipeline import InstantTrendCampaign
from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.instant_trend.evaluator import evaluate_trend_candidates
from xbot.pipelines.instant_trend.generator import generate_trend_commentary
from xbot.pipelines.instant_trend.pipeline import run_instant_trend_cycle
from xbot.pipelines.instant_trend.types import TrendCandidateTweet
from xbot.pipelines.instant_trend.x_searcher import search_x_for_trending_topic


def test_evaluator_deduplication_and_scoring():
    """Verify evaluator filters previously seen tweets and prioritizes media/engagement."""
    candidates = [
        TrendCandidateTweet(
            tweet_id="111",
            text="Old seen tweet about Harry Potter trailer",
            url="https://x.com/user/status/111",
        ),
        TrendCandidateTweet(
            tweet_id="222",
            text="F4F follow train drop your handle connect",
            url="https://x.com/user/status/222",
            is_growth_thread=True,
        ),
        TrendCandidateTweet(
            tweet_id="333",
            text="The cinematography in this new teaser clip is stunning.",
            url="https://x.com/user/status/333",
            author="cinephile",
            media_urls=["https://pbs.twimg.com/media/clip.jpg"],
            is_blue_tick=True,
        ),
    ]

    seen = ["111"]
    action_type, selected = evaluate_trend_candidates(candidates, seen, quote_percentage=100)

    assert action_type == "quote"
    assert selected is not None
    assert selected.tweet_id == "333"
    assert selected.author == "cinephile"


def test_evaluator_fallback_to_post_when_no_candidates():
    """Verify evaluator defaults to standalone post if all tweets are seen."""
    candidates = [
        TrendCandidateTweet(
            tweet_id="111",
            text="Already posted this one",
            url="https://x.com/user/status/111",
        )
    ]
    action_type, selected = evaluate_trend_candidates(candidates, seen_tweet_ids=["111"], quote_percentage=70)
    assert action_type == "post"
    assert selected is None


@pytest.mark.asyncio
async def test_generator_anti_ai_gatekeeper():
    """Verify generated commentary adheres to clean length and anti-AI rules."""
    with patch("xbot.pipelines.instant_trend.generator.RoutingClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Unbelievable look at the new Hogwarts atmosphere. Truly impressive."
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        text = await generate_trend_commentary(
            topic="Harry Potter series trailer",
            action_type="quote",
            target_tweet=TrendCandidateTweet(tweet_id="999", text="Official teaser", url="https://x.com/hp/999"),
        )

        assert len(text) <= 260
        assert "#HarryPotter" in text
        assert "—" not in text
        assert "Hogwarts" in text


@pytest.mark.asyncio
async def test_searcher_x_only_dispatch():
    """Verify searcher uses SEARCH action through container."""
    mock_container = MagicMock()
    mock_container.browser.execute = AsyncMock(return_value=BrowserResponse(
        status="success",
        action=BrowserActionType.SEARCH,
        action_result=ActionResult(
            status="success",
            raw={
                "results": [
                    {
                        "tweet_id": "888",
                        "text": "First look at Harry Potter series!",
                        "url": "https://x.com/hbo/status/888",
                        "author": "HBO",
                        "is_blue_tick": True,
                        "media_urls": ["https://pbs.twimg.com/trailer.jpg"],
                    }
                ]
            }
        )
    ))

    results = await search_x_for_trending_topic(
        container=mock_container,
        profile_slug="test_profile1",
        topic="Harry Potter series trailer",
    )

    assert len(results) == 1
    assert results[0].tweet_id == "888"
    assert results[0].author == "HBO"
    mock_container.browser.execute.assert_called_once()
    call_req = mock_container.browser.execute.call_args[0][0]
    assert call_req.action == BrowserActionType.SEARCH
    assert "Harry Potter series trailer" in call_req.params["query"]
    assert "min_faves:50" in call_req.params["query"]
    assert call_req.params.get("search_filter") == "top"
    assert call_req.params.get("auto_relax") is True


@pytest.mark.asyncio
async def test_pipeline_48h_expiration():
    """Verify campaign automatically marks completed when past expires_at."""
    async with AsyncSessionLocal() as db:
        profile_id = uuid.uuid4()
        profile = Profile(
            id=profile_id,
            profile_slug=f"hp_fan_{profile_id.hex[:6]}",
            x_handle=f"hp_{profile_id.hex[:6]}",
            display_name="HP Fan",
            status=ProfileStatus.ACTIVE,
        )
        db.add(profile)
        await db.commit()

        past_time = datetime.utcnow() - timedelta(hours=50)
        campaign = InstantTrendCampaign(
            id=uuid.uuid4(),
            profile_id=profile.id,
            topic="Harry Potter series trailer",
            status="active",
            duration_hours=48,
            interval_minutes=20,
            started_at=past_time,
            expires_at=past_time + timedelta(hours=48),  # already expired
        )
        db.add(campaign)
        await db.commit()

        res = await run_instant_trend_cycle(campaign.id, db)
        assert res.status == "completed"

        await db.refresh(campaign)
        assert campaign.status == "completed"


@pytest.mark.asyncio
async def test_instant_trend_api_lifecycle():
    """Test full start, active list, and stop API lifecycle."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Start Campaign
        start_res = await ac.post("/api/trends/instant/start", json={
            "topic": "Harry Potter series trailer",
            "profile_slug": "test_profile1",
            "duration_hours": 48,
            "interval_minutes": 15,
            "quote_percentage": 80,
        })
        assert start_res.status_code == 200
        data = start_res.json()
        assert data["status"] == "success"
        campaign_id = data["campaign_id"]

        # 2. Check Active List
        active_res = await ac.get("/api/trends/instant/active")
        assert active_res.status_code == 200
        active_list = active_res.json()
        assert any(c["id"] == campaign_id for c in active_list)

        # 3. Check Status Endpoint
        status_res = await ac.get(f"/api/trends/instant/{campaign_id}/status")
        assert status_res.status_code == 200
        c_data = status_res.json()
        assert c_data["status"] == "active"
        assert c_data["topic"] == "Harry Potter series trailer"

        # 4. Stop Campaign
        stop_res = await ac.post(f"/api/trends/instant/{campaign_id}/stop")
        assert stop_res.status_code == 200
        assert stop_res.json()["status"] == "success"

        # Verify no longer active
        active_after = await ac.get("/api/trends/instant/active")
        assert not any(c["id"] == campaign_id for c in active_after.json())
