import pytest
from xbot.ai.opportunity_radar import (
    CandidateOpportunity,
    OpportunityRadar,
    calculate_velocity_score,
    calculate_saturation_penalty,
    calculate_arbitrage_score,
)


def test_velocity_score_decay():
    # Fresh tweet (< 5m) has high velocity
    fresh_score = calculate_velocity_score(age_minutes=3.0, impressions=5000)
    assert fresh_score > 70.0

    # Old tweet (> 30m) decays significantly
    old_score = calculate_velocity_score(age_minutes=45.0, impressions=5000)
    assert old_score < 30.0


def test_saturation_penalty():
    # Low replies (< 5) has low penalty
    low_penalty = calculate_saturation_penalty(reply_count=3, saturation_threshold=20)
    assert low_penalty < 0.25

    # High replies (>= 20) has high penalty
    high_penalty = calculate_saturation_penalty(reply_count=25, saturation_threshold=20)
    assert high_penalty == 1.0


def test_arbitrage_score_calculation():
    # High-signal fresh opportunity
    score = calculate_arbitrage_score(
        velocity=90.0,
        relevance=85.0,
        author_factor=80.0,
        saturation_penalty=0.1,
    )
    # Score should be high (>= 75.0)
    assert score >= 75.0

    # Saturated / irrelevant opportunity
    low_score = calculate_arbitrage_score(
        velocity=20.0,
        relevance=30.0,
        author_factor=10.0,
        saturation_penalty=0.9,
    )
    assert low_score < 40.0


def test_opportunity_radar_ranking():
    radar = OpportunityRadar(min_arbitrage_threshold=65.0)

    candidates = [
        CandidateOpportunity(
            tweet_id="1",
            author="thetanmay",
            text="Every tech startup founder says we are revolutionizing productivity until they schedule a 90 minute call.",
            url="https://x.com/thetanmay/status/1",
            age_minutes=4.0,
            reply_count=5,
            likes=450,
            relevance_score=90.0,
        ),
        CandidateOpportunity(
            tweet_id="2",
            author="random_bot",
            text="Good morning world, drinking coffee and looking at the sky.",
            url="https://x.com/random_bot/status/2",
            age_minutes=120.0,
            reply_count=80,
            likes=2,
            relevance_score=10.0,
        ),
    ]

    ranked = radar.rank_opportunities(candidates)
    assert len(ranked) == 1
    assert ranked[0].tweet_id == "1"
    assert ranked[0].arbitrage_score >= 65.0
