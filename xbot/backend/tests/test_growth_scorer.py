from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from xbot.ai.growth_scorer import (
    OpportunityScore,
    calculate_engagement_velocity,
    score_tweet_opportunity,
)


def test_opportunity_score_schema_validation() -> None:
    """Tests OpportunityScore Pydantic model structure and validation."""
    score_obj = OpportunityScore(
        score=85.5,
        reply_loop_multiplier=120.0,
        bookmark_potential=35.0,
        velocity=150.2,
        has_link_penalty=False,
        author_is_verified=True,
        recommended_action="sniper_reply",
        reasoning="High reply velocity from verified creator.",
    )
    assert score_obj.score == 85.5
    assert score_obj.reply_loop_multiplier == 120.0
    assert score_obj.bookmark_potential == 35.0
    assert score_obj.velocity == 150.2
    assert score_obj.has_link_penalty is False
    assert score_obj.author_is_verified is True
    assert score_obj.recommended_action == "sniper_reply"
    assert "verified creator" in score_obj.reasoning


def test_calculate_engagement_velocity_fresh_tweet() -> None:
    """Tests engagement velocity calculation for a fresh tweet with active engagement."""
    ref_time = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
    created_at = ref_time - timedelta(minutes=15)

    velocity = calculate_engagement_velocity(
        impressions=3000,
        likes=45,
        replies=12,
        created_at_utc=created_at,
        reference_time=ref_time,
    )

    # 15 mins (0.25h) with 45 likes, 12 replies, 3000 imp should yield high velocity
    assert velocity > 50.0


def test_calculate_engagement_velocity_half_life_decay() -> None:
    """Tests 6-hour half-life exponential decay in velocity calculation."""
    ref_time = datetime(2026, 8, 25, 18, 0, 0, tzinfo=timezone.utc)

    # Tweet created 1 hour ago vs 7 hours ago (delta of 6 hours = 1 half-life)
    t_1h = ref_time - timedelta(hours=1)
    t_7h = ref_time - timedelta(hours=7)

    # Using fixed engagement totals to evaluate the decay factor alone
    # At 7h vs 1h: raw rate differs by 1/7, decay differs by factor of 0.5
    v_1h = calculate_engagement_velocity(
        impressions=6000, likes=100, replies=20, created_at_utc=t_1h, reference_time=ref_time
    )
    v_7h = calculate_engagement_velocity(
        impressions=6000, likes=100, replies=20, created_at_utc=t_7h, reference_time=ref_time
    )

    assert v_1h > v_7h
    # v_7h should be decayed significantly due to 6h half-life + elapsed time
    assert v_7h < (v_1h * 0.25)


def test_score_tweet_opportunity_verified_active_creator() -> None:
    """Tests that a verified active creator with high reply probability achieves a score > 70."""
    ref_time = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
    tweet_data = {
        "tweet_id": "190011223344",
        "author": "tech_lead_alex",
        "text": "What is the single biggest bottleneck you encounter when scaling Python backend services?",
        "is_verified": True,
        "likes": 65,
        "replies": 18,
        "impressions": 4200,
        "created_at_utc": ref_time - timedelta(minutes=20),
    }
    author_history = {
        "reply_rate": 0.85,  # 85% reply-back rate
        "is_broadcast_bot": False,
    }

    result = score_tweet_opportunity(
        tweet_data=tweet_data,
        author_history=author_history,
        reference_time=ref_time,
    )

    assert isinstance(result, OpportunityScore)
    assert result.score > 70.0
    assert result.author_is_verified is True
    assert result.reply_loop_multiplier > 100.0
    assert result.has_link_penalty is False
    assert result.recommended_action == "sniper_reply"
    assert "verified" in result.reasoning.lower() or "reply" in result.reasoning.lower()


def test_score_tweet_opportunity_external_link_penalty() -> None:
    """Tests that tweets containing external links receive a 70% penalty (0.3x multiplier)."""
    ref_time = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
    clean_tweet = {
        "tweet_id": "190011223345",
        "author": "dev_guru",
        "text": "Here is why Rust memory management changes how you design async runtimes.",
        "is_verified": True,
        "likes": 50,
        "replies": 10,
        "impressions": 3000,
        "created_at_utc": ref_time - timedelta(minutes=15),
    }
    link_tweet = {
        "tweet_id": "190011223346",
        "author": "dev_guru",
        "text": "Here is why Rust memory management changes how you design async runtimes. Read more: https://myblog.com/rust-async",
        "is_verified": True,
        "likes": 50,
        "replies": 10,
        "impressions": 3000,
        "created_at_utc": ref_time - timedelta(minutes=15),
    }
    author_history = {"reply_rate": 0.5, "is_broadcast_bot": False}

    clean_score = score_tweet_opportunity(clean_tweet, author_history, reference_time=ref_time)
    link_score = score_tweet_opportunity(link_tweet, author_history, reference_time=ref_time)

    assert clean_score.has_link_penalty is False
    assert link_score.has_link_penalty is True
    assert link_score.score <= (clean_score.score * 0.35)


def test_score_tweet_opportunity_aged_tweet_decay() -> None:
    """Tests that tweets older than 12 hours receive heavily decayed scores and skip recommendation."""
    ref_time = datetime(2026, 8, 25, 18, 0, 0, tzinfo=timezone.utc)
    aged_tweet = {
        "tweet_id": "190011223347",
        "author": "tech_lead_alex",
        "text": "What database architecture do you use for high-throughput write workloads?",
        "is_verified": True,
        "likes": 200,
        "replies": 40,
        "impressions": 15000,
        "created_at_utc": ref_time - timedelta(hours=14),
    }
    author_history = {"reply_rate": 0.8, "is_broadcast_bot": False}

    result = score_tweet_opportunity(aged_tweet, author_history, reference_time=ref_time)

    assert result.score < 40.0
    assert result.recommended_action == "skip"


def test_score_tweet_opportunity_bookmark_potential_detection() -> None:
    """Tests detection of bookmarkable framework/cheatsheet/checklist patterns (+50x potential)."""
    ref_time = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
    bookmark_tweet = {
        "tweet_id": "190011223348",
        "author": "architect_jane",
        "text": (
            "Distributed Systems Architecture Framework:\n"
            "1. Event-driven choreography for loose coupling\n"
            "2. Read-side CQRS projections for p99 query latency\n"
            "3. Outbox pattern with Debezium CDC for transactional consistency\n"
            "4. Token bucket rate limiters at API gateway\n"
            "Save this cheatsheet for system design interviews."
        ),
        "is_verified": True,
        "likes": 80,
        "replies": 15,
        "impressions": 5000,
        "created_at_utc": ref_time - timedelta(minutes=25),
    }

    result = score_tweet_opportunity(bookmark_tweet, reference_time=ref_time)

    assert result.bookmark_potential >= 30.0
    assert result.score >= 70.0
    assert result.recommended_action in ("bookmark_reference", "sniper_reply")


def test_score_tweet_opportunity_broadcast_bot_penalty() -> None:
    """Tests that broadcast-only accounts (0% reply rate or bot flag) are severely penalized."""
    ref_time = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
    news_tweet = {
        "tweet_id": "190011223349",
        "author": "tech_news_247",
        "text": "Breaking: Cloud provider announces new datacenter region in Zurich.",
        "is_verified": False,
        "likes": 30,
        "replies": 2,
        "impressions": 1500,
        "created_at_utc": ref_time - timedelta(minutes=10),
    }
    author_history = {
        "reply_rate": 0.0,
        "is_broadcast_bot": True,
    }

    result = score_tweet_opportunity(news_tweet, author_history, reference_time=ref_time)

    assert result.reply_loop_multiplier <= 1.0
    assert result.score < 40.0
    assert result.recommended_action == "skip"
