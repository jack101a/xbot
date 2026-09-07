from __future__ import annotations

import datetime
from pathlib import Path

import pytest
import pytest_asyncio
import redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.config import settings
from xbot.models.base import Base
from xbot.models.profile import Profile, ProfileStatus
from xbot.scheduling.scheduler import check_and_trigger_schedules, generate_daily_schedule
from xbot.safety.guard import SafetyGuard
from xbot.safety.limiter import SlidingWindowLimiter

TEST_DB_URL = "sqlite+aiosqlite:///test_temp_safety.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
SessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
def clean_redis() -> None:
    r = redis.from_url(settings.REDIS_URL)
    # Clear test keys
    keys = r.keys("rate:test_slug:*") + r.keys("cooldown:test_slug:*") + r.keys("failures:test_slug*") + r.keys("backoff:test_slug*") + r.keys("schedule:test_slug:*")
    if keys:
        r.delete(*keys)
    yield
    if keys:
        r.delete(*keys)


def test_generate_daily_schedule() -> None:
    # 1. Standard schedule times within active hours (10:00 - 18:00)
    times = generate_daily_schedule(
        timezone_str="UTC",
        wake_hour=10,
        sleep_hour=18,
        sessions_per_day=4,
        min_gap_minutes=60,
        day_weights={0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0},
        target_date=datetime.date(2026, 6, 18),
    )
    
    assert len(times) > 0
    # Every time should be within 10:00 and 18:00 UTC
    for t in times:
        assert t.hour >= 10
        assert t.hour <= 18
        
    # Minimum gap check
    for i in range(1, len(times)):
        gap = (times[i] - times[i-1]).total_seconds() / 60
        assert gap >= 60


def test_sliding_window_rate_limiter() -> None:
    limiter = SlidingWindowLimiter()
    profile_slug = "test_slug"
    action_type = "like"

    now = datetime.datetime.utcnow()

    # 1. Assert not limited initially
    assert limiter.is_rate_limited(profile_slug, action_type, limit_hourly=3, limit_daily=5, now_utc=now) is False

    # 2. Record 3 actions
    limiter.record_action(profile_slug, action_type, now - datetime.timedelta(minutes=10))
    limiter.record_action(profile_slug, action_type, now - datetime.timedelta(minutes=5))
    limiter.record_action(profile_slug, action_type, now)

    # 3. Hourly limit is 3. It should be rate limited now!
    assert limiter.is_rate_limited(profile_slug, action_type, limit_hourly=3, limit_daily=5, now_utc=now) is True

    # 4. Hourly limit is 4. It should not be limited
    assert limiter.is_rate_limited(profile_slug, action_type, limit_hourly=4, limit_daily=5, now_utc=now) is False


def test_cooldown_tracking() -> None:
    limiter = SlidingWindowLimiter()
    profile_slug = "test_slug"
    action_type = "post"
    now = datetime.datetime.utcnow()

    assert limiter.is_cooldown_active(profile_slug, action_type, now) is False

    # Set 5 seconds cooldown
    limiter.set_cooldown(profile_slug, action_type, cooldown_seconds=5, now_utc=now)
    assert limiter.is_cooldown_active(profile_slug, action_type, now) is True

    # Check cooldown active after 6 seconds (should be False)
    assert limiter.is_cooldown_active(profile_slug, action_type, now + datetime.timedelta(seconds=6)) is False


@pytest.mark.asyncio
async def test_safety_guard_multiplier_and_backoff(db_session: AsyncSession) -> None:
    profile_slug = "test_slug"
    now = datetime.datetime.utcnow()

    # 1. Multiplier checks based on created_at age
    guard = SafetyGuard()
    
    # A. 3 days old (Multiplier = 0.25)
    multi_a = guard.get_warmup_multiplier(now - datetime.timedelta(days=3), now)
    assert multi_a == 0.25

    # B. 10 days old (Multiplier = 0.5)
    multi_b = guard.get_warmup_multiplier(now - datetime.timedelta(days=10), now)
    assert multi_b == 0.50

    # C. 40 days old (Multiplier = 0.75)
    multi_c = guard.get_warmup_multiplier(now - datetime.timedelta(days=40), now)
    assert multi_c == 0.75

    # D. 100 days old (Multiplier = 1.0)
    multi_d = guard.get_warmup_multiplier(now - datetime.timedelta(days=100), now)
    assert multi_d == 1.0

    # 2. Test get_adjusted_limits without backoff
    hourly, daily = guard.get_adjusted_limits(profile_slug, "post", now - datetime.timedelta(days=100), now)
    assert hourly == SafetyGuard.BASE_LIMITS["post"][0]
    assert daily == SafetyGuard.BASE_LIMITS["post"][1]

    # 3. Test get_adjusted_limits WITH backoff (50% reduction)
    # Set backoff key
    guard.r.set(f"backoff:{profile_slug}", "1", ex=10)
    hourly_b, daily_b = guard.get_adjusted_limits(profile_slug, "post", now - datetime.timedelta(days=100), now)
    assert hourly_b == round(SafetyGuard.BASE_LIMITS["post"][0] * 0.5)
    assert daily_b == round(SafetyGuard.BASE_LIMITS["post"][1] * 0.5)


@pytest.mark.asyncio
async def test_safety_guard_failures_and_signal(db_session: AsyncSession) -> None:
    profile_slug = "test_slug"
    profile = Profile(
        profile_slug=profile_slug,
        x_handle="@testslug",
        display_name="Test Slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    guard = SafetyGuard()

    # 1. Trigger Circuit Breaker: 3 consecutive generic failures
    await guard.record_action_failure(db_session, profile_slug, "Generic connection error")
    await guard.record_action_failure(db_session, profile_slug, "Generic connection error")
    await guard.record_action_failure(db_session, profile_slug, "Generic connection error")

    # Refresh profile status: must be PAUSED
    await db_session.refresh(profile)
    assert profile.status == ProfileStatus.PAUSED

    # Reset profile to active for next check
    profile.status = ProfileStatus.ACTIVE
    await db_session.commit()

    # 2. Trigger Health Signal: LOCKED error
    await guard.record_action_failure(db_session, profile_slug, "Your account has been locked due to security warning.")
    await db_session.refresh(profile)
    assert profile.status == ProfileStatus.LOCKED


@pytest.mark.asyncio
async def test_safety_guard_custom_limits_and_disabled_mode(db_session: AsyncSession, tmp_path: Path) -> None:
    profile_slug = "custom_slug"
    profile_dir = tmp_path / profile_slug
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    # Write custom config with high limits and disabled warmup
    with open(profile_dir / "config.yaml", "w") as f:
        f.write("""
limits:
  max_posts_per_day: 50
  max_replies_per_day: 100
  max_likes_per_day: 200
  max_follows_per_day: 80
  warmup_enabled: false
  cooldown_seconds: 0
  safety_mode: normal
""")

    profile = Profile(
        profile_slug=profile_slug,
        x_handle="@customslug",
        display_name="Custom Slug",
        status=ProfileStatus.ACTIVE,
        created_at=datetime.datetime.utcnow() - datetime.timedelta(days=1), # brand new account
    )
    db_session.add(profile)
    await db_session.commit()

    guard = SafetyGuard(base_profile_dir=str(tmp_path))

    # Should use the full custom daily limit (50 posts) and NOT be throttled to 25% by warmup
    hourly, daily = guard.get_adjusted_limits(profile_slug, "post", profile.created_at, datetime.datetime.utcnow())
    assert daily == 50
    assert hourly >= 8

    # Should be safe to execute
    is_safe = await guard.is_action_safe(db_session, profile_slug, "post")
    assert is_safe is True
