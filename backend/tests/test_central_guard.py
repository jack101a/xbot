import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.pipelines.central_guard import (
    CentralGuard,
    get_current_ist_time,
    is_within_active_hours,
)


def test_ist_time_conversion():
    # 2026-08-27 12:00:00 UTC = 17:30:00 IST (+5:30)
    utc_time = datetime.datetime(2026, 8, 27, 12, 0, 0, tzinfo=datetime.timezone.utc)
    ist_time = get_current_ist_time(utc_time)
    assert ist_time.hour == 17
    assert ist_time.minute == 30


def test_is_within_active_hours():
    # 08:00 IST (UTC 02:30) -> active
    utc_morning = datetime.datetime(2026, 8, 27, 2, 30, 0, tzinfo=datetime.timezone.utc)
    assert is_within_active_hours(utc_morning) is True

    # 03:00 IST (UTC 21:30 previous day) -> sleep window (not active)
    utc_sleep = datetime.datetime(2026, 8, 26, 21, 30, 0, tzinfo=datetime.timezone.utc)
    assert is_within_active_hours(utc_sleep) is False

    # 01:30 IST (UTC 20:00 previous day) -> active (before 02:00 IST)
    utc_late = datetime.datetime(2026, 8, 26, 20, 0, 0, tzinfo=datetime.timezone.utc)
    assert is_within_active_hours(utc_late) is True


def test_is_action_24_7():
    guard = CentralGuard(redis_url="redis://localhost:6379/0")
    assert guard.is_action_24_7("trend_researcher") is True
    assert guard.is_action_24_7("trend_generator") is True
    assert guard.is_action_24_7("research") is True
    assert guard.is_action_24_7("like") is False
    assert guard.is_action_24_7("reply") is False
    assert guard.is_action_24_7("quote") is False
    assert guard.is_action_24_7("follow") is False


@pytest.mark.asyncio
async def test_target_deduplication():
    mock_redis = MagicMock()
    mock_redis.exists.return_value = 1
    mock_redis.set.return_value = True

    guard = CentralGuard(redis_url="redis://localhost:6379/0")
    guard.r = mock_redis

    assert guard.is_target_acted_upon("test_slug", "like", "tweet_123") is True
    mock_redis.exists.assert_called_with("xbot:action_done:test_slug:like:tweet_123")

    guard.mark_target_acted("test_slug", "like", "tweet_456")
    mock_redis.set.assert_called_with("xbot:action_done:test_slug:like:tweet_456", "1", ex=172800)


@pytest.mark.asyncio
async def test_can_act_active_hours_and_safety_guard():
    mock_redis = MagicMock()
    mock_redis.exists.return_value = 0

    mock_safety_guard = MagicMock()
    mock_safety_guard.is_action_safe = AsyncMock(return_value=True)

    guard = CentralGuard(redis_url="redis://localhost:6379/0", safety_guard=mock_safety_guard)
    guard.r = mock_redis

    mock_db = AsyncMock()

    # Active hour (12:00 UTC = 17:30 IST)
    utc_active = datetime.datetime(2026, 8, 27, 12, 0, 0, tzinfo=datetime.timezone.utc)
    res = await guard.can_act(mock_db, "test_slug", "like", target_id="tweet_999", now_utc=utc_active)
    assert res is True
    mock_safety_guard.is_action_safe.assert_called_once()

    # Sleep hour (21:30 UTC = 03:00 IST) -> rejected for live interaction
    mock_safety_guard.is_action_safe.reset_mock()
    utc_sleep = datetime.datetime(2026, 8, 26, 21, 30, 0, tzinfo=datetime.timezone.utc)
    res_sleep = await guard.can_act(mock_db, "test_slug", "like", now_utc=utc_sleep)
    assert res_sleep is False
    mock_safety_guard.is_action_safe.assert_not_called()

    # Sleep hour for 24/7 action (trend_researcher) -> allowed
    res_research = await guard.can_act(mock_db, "test_slug", "trend_researcher", now_utc=utc_sleep)
    assert res_research is True


@pytest.mark.asyncio
async def test_record_action_and_daily_stats():
    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda k: "15" if "like" in k else "5" if "reply" in k else None

    mock_safety_guard = MagicMock()
    mock_safety_guard.record_action_success = AsyncMock(return_value=True)

    guard = CentralGuard(redis_url="redis://localhost:6379/0", safety_guard=mock_safety_guard)
    guard.r = mock_redis

    mock_db = AsyncMock()
    utc_time = datetime.datetime(2026, 8, 27, 12, 0, 0, tzinfo=datetime.timezone.utc)
    await guard.record_action(mock_db, "test_slug", "like", target_id="t_1", now_utc=utc_time)

    mock_safety_guard.record_action_success.assert_called_once()
    mock_redis.incr.assert_called_once()

    stats = guard.get_daily_stats("test_slug", date_str="2026-08-27")
    assert stats["likes"] == 15
    assert stats["replies"] == 5
    assert stats["posts"] == 0
