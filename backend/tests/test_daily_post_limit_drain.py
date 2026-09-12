import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from xbot.safety.guard.drain_lock import (
    clear_daily_post_limit_drained,
    get_daily_post_limit_status,
    is_daily_post_limit_drained,
    set_daily_post_limit_drained,
)
from xbot.browser.actions.utils import check_daily_post_limit
from xbot.safety.guard.guard import SafetyGuard
from xbot.pipelines.central_guard import CentralGuard


class MockRedis:
    def __init__(self):
        self.store = {}
        self.ttls = {}

    def exists(self, key):
        return 1 if key in self.store else 0

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value
        self.ttls[key] = ex or 86400
        return True

    def ttl(self, key):
        return self.ttls.get(key, -2)

    def delete(self, key):
        if key in self.store:
            del self.store[key]
            self.ttls.pop(key, None)
            return 1
        return 0


def test_drain_lock_lifecycle():
    fake_r = MockRedis()
    slug = "test_profile_drain"

    # Initially false
    assert not is_daily_post_limit_drained(fake_r, slug)
    status = get_daily_post_limit_status(fake_r, slug)
    assert not status["drained"]

    # Set drain lock
    ttl = set_daily_post_limit_drained(fake_r, slug, reason="You've hit the daily post limit")
    assert ttl >= 21600
    assert is_daily_post_limit_drained(fake_r, slug)

    status = get_daily_post_limit_status(fake_r, slug)
    assert status["drained"]
    assert "daily post limit" in status["reason"]
    assert status["resets_in_seconds"] > 0

    # Clear drain lock
    assert clear_daily_post_limit_drained(fake_r, slug)
    assert not is_daily_post_limit_drained(fake_r, slug)


@pytest.mark.asyncio
async def test_safety_guard_blocks_when_drained():
    fake_r = MockRedis()
    slug = "test_guard_drain"

    guard = SafetyGuard(redis_url="redis://localhost:6379/0")
    guard.r = fake_r

    # Set drain lock
    set_daily_post_limit_drained(fake_r, slug, reason="Daily post limit reached")

    # Mock DB profile
    db_mock = AsyncMock()
    profile_mock = MagicMock()
    profile_mock.profile_slug = slug
    profile_mock.status = "active"
    profile_mock.created_at = datetime.datetime.utcnow() - datetime.timedelta(days=100)

    db_res = MagicMock()
    db_res.scalar_one_or_none.return_value = profile_mock
    db_mock.execute.return_value = db_res

    # Should reject post, quote, thread, growth_post
    for act in ["post", "quote", "thread", "growth_post"]:
        is_safe = await guard.is_action_safe(db_mock, slug, act)
        assert not is_safe, f"Action {act} should be blocked when daily limit drained"


@pytest.mark.asyncio
async def test_central_guard_blocks_when_drained():
    fake_r = MockRedis()
    slug = "test_cg_drain"

    cg = CentralGuard()
    cg.r = fake_r
    set_daily_post_limit_drained(fake_r, slug, reason="Daily post limit reached")

    db_mock = AsyncMock()
    assert not await cg.can_act(db_mock, slug, "post")
    assert not await cg.can_act(db_mock, slug, "growth_post")


@pytest.mark.asyncio
async def test_check_daily_post_limit_detection():
    # Mock page with dialog containing daily limit text
    mock_page = MagicMock()
    mock_el = AsyncMock()
    mock_el.is_visible.return_value = True
    mock_el.inner_text.return_value = "You've hit the daily post limit. Subscribe to Premium for higher limits."

    mock_page.query_selector_all = AsyncMock(return_value=[mock_el])
    mock_page.evaluate = AsyncMock(return_value="")

    detected = await check_daily_post_limit(mock_page)
    assert detected is not None
    assert "daily post limit" in detected
