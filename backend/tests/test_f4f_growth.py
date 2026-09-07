import pytest
import uuid
from xbot.growth.community_harvester import (
    calculate_reciprocity_score,
    harvest_community_candidates,
)
from xbot.growth.f4f_engine import (
    populate_f4f_candidates,
    record_follow_action,
    get_f4f_milestone_analytics,
)
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.models.profile import Profile, ProfileStatus

def test_calculate_reciprocity_score():
    # Peer Blue Tick user with 1,500 followers and 800 following -> high score
    score_peer = calculate_reciprocity_score(
        is_blue_tick=True,
        follower_count=1500,
        following_count=800,
        is_active=True,
    )
    assert score_peer >= 80.0

    # Non-blue tick user with 500 followers
    score_non_bt = calculate_reciprocity_score(
        is_blue_tick=False,
        follower_count=500,
        following_count=200,
        is_active=True,
    )
    assert score_non_bt < score_peer

    # Mega account (>50k followers) penalty
    score_mega = calculate_reciprocity_score(
        is_blue_tick=True,
        follower_count=500000,
        following_count=50,
        is_active=True,
    )
    assert score_mega < 50.0

def test_harvest_community_candidates():
    candidates = harvest_community_candidates(niche="anime", limit=5)
    assert len(candidates) > 0
    for c in candidates:
        assert c.niche == "anime"
        assert c.is_blue_tick is True
        assert c.reciprocity_score > 60.0

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from xbot.models.base import Base

@pytest.mark.asyncio
async def test_f4f_db_lifecycle():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # Create test profile
        profile = Profile(
            id=uuid.uuid4(),
            profile_slug="test_f4f_user",
            x_handle="@test_f4f",
            display_name="Test F4F User",
            status=ProfileStatus.ACTIVE,
        )
        session.add(profile)
        await session.commit()

        # Populate candidates
        candidates = await populate_f4f_candidates(profile.id, session, niche="ai", limit=4)
        assert len(candidates) == 4

        # Record follow action
        first_cand = candidates[0]
        rel = await record_follow_action(
            profile_id=profile.id,
            target_handle=first_cand.handle,
            db=session,
            is_blue_tick=True,
            niche="ai",
        )
        assert rel.status == "following"
        assert rel.target_handle == first_cand.handle
        assert rel.is_blue_tick is True

        # Milestone stats (500 goal)
        stats = await get_f4f_milestone_analytics(profile.id, session)
        assert stats["goal_target"] == 500
        assert stats["total_followed_all_time"] >= 1
        assert stats["blue_tick_followed_count"] >= 1


def test_indian_demographic_reciprocity_boost():
    """Tests that Indian creator community accounts receive higher reciprocity priority."""
    score_indian = calculate_reciprocity_score(
        is_blue_tick=True,
        follower_count=2500,
        following_count=1200,
        is_indian_demographic=True,
    )
    score_general = calculate_reciprocity_score(
        is_blue_tick=True,
        follower_count=2500,
        following_count=1200,
        is_indian_demographic=False,
    )
    assert score_indian > score_general
    assert (score_indian - score_general) == 15.0


def test_non_target_demographic_filtering():
    """Tests that non-target demographic accounts are penalized unless they have a massive follower base (>50k)."""
    # Low follower non-target account -> heavily penalized
    score_low = calculate_reciprocity_score(
        is_blue_tick=True,
        follower_count=1500,
        following_count=800,
        is_non_target_demographic=True,
    )
    assert score_low <= 65.0

    # Massive authority account (>50k followers) -> prioritized
    score_high = calculate_reciprocity_score(
        is_blue_tick=True,
        follower_count=120000,
        following_count=1500,
        is_non_target_demographic=True,
    )
    assert score_high >= 80.0


def test_is_f4f_or_engagement_growth_post_detection():
    """Tests detection of F4F trains and ensuring quote_tweet recommendation is blocked on them."""
    from xbot.ai.growth_scorer import is_f4f_or_engagement_growth_post, score_tweet_opportunity
    from datetime import datetime, timezone, timedelta

    f4f_text = "Verified Blue Tick mutuals thread! Drop your handle below, follow 3 people and follow back everyone who interacts!"
    assert is_f4f_or_engagement_growth_post(f4f_text) is True

    normal_text = "Here is a breakdown of how modern memory bandwidth impacts large language model inference latency."
    assert is_f4f_or_engagement_growth_post(normal_text) is False

    ref_time = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
    viral_f4f_tweet = {
        "tweet_id": "190011223399",
        "author": "growth_train",
        "text": f4f_text,
        "is_verified": True,
        "likes": 5000,
        "replies": 1200,
        "impressions": 250000,
        "created_at_utc": ref_time - timedelta(hours=1),
    }

    score_res = score_tweet_opportunity(viral_f4f_tweet, reference_time=ref_time)
    # Even though impressions >= 100k, recommended_action must NOT be quote_tweet because it's an F4F post
    assert score_res.recommended_action != "quote_tweet"
    assert score_res.recommended_action == "sniper_reply"
