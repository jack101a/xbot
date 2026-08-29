import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.pipelines.post_pruner_pipeline import (
    PrunerFilterCriteria,
    ScrapedProfileTweet,
    evaluate_tweet_for_pruning,
    run_post_pruner_for_profile,
)
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus
from xbot.models.session import ActionType

def test_evaluate_tweet_skips_replies_retweets_pinned():
    criteria = PrunerFilterCriteria(min_views=500, min_likes=10, min_comments=2)

    # 1. Reply
    tw_reply = ScrapedProfileTweet(
        tweet_id="1", tweet_url="https://x.com/user/status/1", is_reply=True, views=10, likes=0, comments=0, age_hours=48.0
    )
    should_del, reason = evaluate_tweet_for_pruning(tw_reply, criteria)
    assert should_del is False
    assert reason == "skipped_reply"

    # 2. Retweet
    tw_rt = ScrapedProfileTweet(
        tweet_id="2", tweet_url="https://x.com/user/status/2", is_retweet=True, views=10, likes=0, comments=0, age_hours=48.0
    )
    should_del, reason = evaluate_tweet_for_pruning(tw_rt, criteria)
    assert should_del is False
    assert reason == "skipped_retweet"

    # 3. Pinned
    tw_pin = ScrapedProfileTweet(
        tweet_id="3", tweet_url="https://x.com/user/status/3", is_pinned=True, views=10, likes=0, comments=0, age_hours=48.0
    )
    should_del, reason = evaluate_tweet_for_pruning(tw_pin, criteria)
    assert should_del is False
    assert reason == "skipped_pinned_post"

def test_evaluate_tweet_respects_grace_period():
    criteria = PrunerFilterCriteria(min_views=500, min_likes=10, min_comments=2, min_age_hours=24)

    # Tweet is only 12 hours old
    tw_young = ScrapedProfileTweet(
        tweet_id="4", tweet_url="https://x.com/user/status/4", views=10, likes=0, comments=0, age_hours=12.0
    )
    should_del, reason = evaluate_tweet_for_pruning(tw_young, criteria)
    assert should_del is False
    assert "skipped_too_recent" in reason

def test_evaluate_tweet_match_mode_all_strict():
    criteria = PrunerFilterCriteria(min_views=500, min_likes=10, min_comments=2, min_age_hours=24, match_mode="all")

    # Case A: All 3 metrics fail -> should delete
    tw_all_fail = ScrapedProfileTweet(
        tweet_id="5", tweet_url="https://x.com/user/status/5", views=100, likes=2, comments=0, age_hours=48.0
    )
    should_del, reason = evaluate_tweet_for_pruning(tw_all_fail, criteria)
    assert should_del is True
    assert "all_active_metrics_below" in reason or "all_metrics_below" in reason

    # Case A2: Zero threshold criteria (min_comments = 0, min_likes = 1, min_views = 50)
    criteria_zero_comments = PrunerFilterCriteria(min_views=50, min_likes=1, min_comments=0, min_age_hours=0, match_mode="all")
    tw_zero_comments_match = ScrapedProfileTweet(
        tweet_id="5b", tweet_url="https://x.com/user/status/5b", views=10, likes=0, comments=0, age_hours=2.0
    )
    should_del_zero, _ = evaluate_tweet_for_pruning(tw_zero_comments_match, criteria_zero_comments)
    assert should_del_zero is True

    # Case B: Views passed (600 >= 500), but likes failed -> should NOT delete in strict mode
    tw_one_passed = ScrapedProfileTweet(
        tweet_id="6", tweet_url="https://x.com/user/status/6", views=600, likes=2, comments=0, age_hours=48.0
    )
    should_del, reason = evaluate_tweet_for_pruning(tw_one_passed, criteria)
    assert should_del is False

def test_evaluate_tweet_match_mode_any_aggressive():
    criteria = PrunerFilterCriteria(min_views=500, min_likes=10, min_comments=2, min_age_hours=24, match_mode="any")

    # Views passed, but likes failed -> should delete in aggressive mode
    tw_one_failed = ScrapedProfileTweet(
        tweet_id="7", tweet_url="https://x.com/user/status/7", views=600, likes=2, comments=5, age_hours=48.0
    )
    should_del, reason = evaluate_tweet_for_pruning(tw_one_failed, criteria)
    assert should_del is True
    assert "metric_below_threshold" in reason

@pytest.mark.asyncio
async def test_run_post_pruner_for_profile_flow():
    db = AsyncMock()
    profile_id = uuid.uuid4()

    mock_profile = Profile(
        id=profile_id,
        profile_slug="test_profile",
        x_handle="@test_handle",
        display_name="Test Display",
        status=ProfileStatus.ACTIVE,
    )
    mock_exec_res = MagicMock()
    mock_exec_res.scalar_one_or_none.side_effect = [mock_profile, None, None]
    db.execute.return_value = mock_exec_res

    mock_redis = MagicMock()

    criteria = PrunerFilterCriteria(min_views=100, min_likes=5, min_comments=2, max_posts_to_delete=2, match_mode="all")

    scraped_data = [
        {"tweet_id": "101", "views": 20, "likes": 0, "comments": 0, "age_hours": 30.0, "text": "Underperforming post 1"},
        {"tweet_id": "102", "views": 15, "likes": 1, "comments": 0, "age_hours": 36.0, "text": "Underperforming post 2"},
        {"tweet_id": "103", "views": 500, "likes": 50, "comments": 10, "age_hours": 40.0, "text": "Viral post"},
    ]

    result = await run_post_pruner_for_profile(
        profile_id=profile_id,
        criteria=criteria,
        db=db,
        r=mock_redis,
        custom_scraped_tweets=scraped_data,
    )

    assert result["status"] == "success"
    assert result["scanned_count"] == 3
    assert result["deleted_count"] == 2
    # 1 Session + 2 Actions added to db
    assert db.add.call_count >= 2
    db.commit.assert_called_once()
