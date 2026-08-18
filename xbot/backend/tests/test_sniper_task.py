from __future__ import annotations

import datetime
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
import pytest_asyncio
import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.ai.sniper import SniperReplyResult
from xbot.celery_app import celery_app
from xbot.config import settings
from xbot.models.base import Base
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType
from xbot.persona.loader import (
    Goals,
    Identity,
    Interests,
    Personality,
    Persona,
    Rules,
    TargetKOL,
    WritingStyle,
)

TEST_DB_URL = "sqlite+aiosqlite:///test_temp_sniper_task.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
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
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
def clean_redis() -> None:
    r = redis.from_url(settings.REDIS_URL)
    keys = r.keys("xbot:seen_tweets:*") + r.keys("lock:browser:*") + r.keys("rate:*") + r.keys("cooldown:*")
    if keys:
        r.delete(*keys)
    yield
    keys = r.keys("xbot:seen_tweets:*") + r.keys("lock:browser:*") + r.keys("rate:*") + r.keys("cooldown:*")
    if keys:
        r.delete(*keys)


@pytest.fixture
def sample_persona_with_kols() -> Persona:
    return Persona(
        id="sniper_persona",
        display_name="Market Analyst",
        x_handle="@marketanalyst",
        identity=Identity(
            background="Veteran macro trader and market structure researcher.",
            occupation="Portfolio Manager",
        ),
        personality=Personality(
            traits=["concise", "analytical", "witty"],
            values=["truth", "clarity"],
            communication_style="Direct and data-grounded",
        ),
        interests=Interests(
            primary=["Macroeconomics", "AI Infrastructure", "Venture Capital"],
            secondary=["Energy Markets"],
            will_not_discuss=["speculative memecoins"],
        ),
        writing_style=WritingStyle(
            tone="sharp, analytical, witty",
            typical_length="short",
            formatting=["no emojis", "no hashtags"],
            examples=["Liquidity drives narratives, not fundamentals."],
        ),
        goals=Goals(
            short_term=["build audience among domain leaders"],
            long_term=["top tier authority"],
            content_pillars=["Macro breakdown", "Infra costs"],
        ),
        rules=Rules(
            always=["provide concrete insight", "stay under 240 chars"],
            never=["use generic praise", "use hashtags", "say 'Great post!'"],
        ),
        target_kols=[
            TargetKOL(
                handle="sama",
                category="ai",
                priority="high",
                preferred_angle="framework",
            ),
            TargetKOL(
                handle="paulg",
                category="startups",
                priority="high",
                preferred_angle="contrarian",
            ),
        ],
    )


@pytest.fixture
def sample_persona_no_kols() -> Persona:
    return Persona(
        id="quiet_persona",
        display_name="Quiet Persona",
        x_handle="@quiet",
        identity=Identity(background="Lurker"),
        personality=Personality(traits=["quiet"], communication_style="Minimal"),
        interests=Interests(primary=["Tech"]),
        writing_style=WritingStyle(tone="neutral", typical_length="short"),
        goals=Goals(),
        rules=Rules(),
        target_kols=[],
    )


def test_celery_schedule_registered() -> None:
    """Verifies that the periodic schedule for sniper_check_targets is registered in celery_app."""
    schedule = celery_app.conf.beat_schedule.get("sniper-check-targets-every-120-seconds")
    assert schedule is not None, "Schedule 'sniper-check-targets-every-120-seconds' not found in beat_schedule"
    assert schedule["task"] == "xbot.tasks.sniper_check_targets"
    assert schedule["schedule"] == 120.0


@pytest.mark.asyncio
async def test_sniper_check_targets_executes_reply_and_records_db(
    db_session: AsyncSession,
    sample_persona_with_kols: Persona,
    tmp_path: Path,
) -> None:
    """Tests that active profile with target KOLs fetches latest tweet, generates sniper reply, executes, and records DB Action."""
    from xbot.tasks import _sniper_check_targets_async

    # 1. Create active profile in DB
    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@marketanalyst",
        display_name="Market Analyst",
        profile_slug="test_sniper_profile",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    # 2. Mock latest tweet from CheckUserLatestTweet
    tweet_data_sama = {
        "tweet_id": "998877665544",
        "author": "sama",
        "text": "Compute efficiency is doubling every 6 months across our infrastructure.",
        "url": "https://x.com/sama/status/998877665544",
        "created_at": "3m",
        "is_pinned": False,
    }

    mock_sniper_result = SniperReplyResult(
        reply_text="Compute efficiency doubles, but interconnect latency remains bound by physics.",
        angle_used="framework",
        confidence=0.92,
        reasoning="Framing compute gains vs physical latency bottleneck.",
    )

    mock_browser_context = AsyncMock()
    mock_page = AsyncMock()
    mock_browser_context.new_page.return_value = mock_page

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kols), \
         patch("xbot.tasks.CheckUserLatestTweet.execute", AsyncMock(return_value=tweet_data_sama)) as mock_check_tweet, \
         patch("xbot.tasks.generate_sniper_reply", AsyncMock(return_value=mock_sniper_result)) as mock_gen_reply, \
         patch("xbot.tasks.ReplyToTweet.execute", AsyncMock(return_value=True)) as mock_reply_action, \
         patch("xbot.tasks.BrowserManager.get_context", AsyncMock(return_value=mock_browser_context)), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True) as mock_lock, \
         patch("xbot.tasks.BrowserManager.release_lock", return_value=True) as mock_unlock, \
         patch("xbot.tasks.sleep_with_jitter", AsyncMock()):

        result = await _sniper_check_targets_async()

        assert result["status"] == "success"
        assert result["profiles_processed"] >= 1
        assert result["replies_posted"] >= 1

        # Verify CheckUserLatestTweet was called with KOL handle
        mock_check_tweet.assert_called()

        # Verify generate_sniper_reply was invoked with sample persona and target tweet
        mock_gen_reply.assert_called()

        # Verify ReplyToTweet was executed with the generated reply text and tweet URL
        mock_reply_action.assert_called()

        # Verify Action recorded in DB
        stmt = select(Action).where(
            Action.profile_id == profile_id,
            Action.action_type == ActionType.REPLY,
        )
        res = await db_session.execute(stmt)
        actions = res.scalars().all()
        assert len(actions) >= 1
        action = actions[0]
        assert action.status == ActionStatus.COMPLETED
        assert action.content == mock_sniper_result.reply_text
        assert action.target_url == tweet_data_sama["url"]
        assert action.result is not None
        assert action.result.get("sniper") is True
        assert action.result.get("target_kol") in ("sama", "paulg")
        assert action.result.get("angle") == "framework"


@pytest.mark.asyncio
async def test_sniper_check_targets_redis_deduplication(
    db_session: AsyncSession,
    sample_persona_with_kols: Persona,
) -> None:
    """Tests that already-seen tweets are skipped via Redis deduplication."""
    from xbot.tasks import _sniper_check_targets_async

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@marketanalyst",
        display_name="Market Analyst",
        profile_slug="test_sniper_dedup",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    seen_tweet_id = "112233445566"
    # Pre-mark tweet as seen in Redis
    r = redis.from_url(settings.REDIS_URL)
    r.set(f"xbot:seen_tweets:{profile_id}:{seen_tweet_id}", "1")

    tweet_data = {
        "tweet_id": seen_tweet_id,
        "author": "sama",
        "text": "Already seen post.",
        "url": f"https://x.com/sama/status/{seen_tweet_id}",
        "created_at": "10m",
        "is_pinned": False,
    }

    mock_browser_context = AsyncMock()
    mock_page = AsyncMock()
    mock_browser_context.new_page.return_value = mock_page

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kols), \
         patch("xbot.tasks.CheckUserLatestTweet.execute", AsyncMock(return_value=tweet_data)), \
         patch("xbot.tasks.generate_sniper_reply", AsyncMock()) as mock_gen_reply, \
         patch("xbot.tasks.ReplyToTweet.execute", AsyncMock()) as mock_reply_action, \
         patch("xbot.tasks.BrowserManager.get_context", AsyncMock(return_value=mock_browser_context)), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.release_lock", return_value=True):

        result = await _sniper_check_targets_async()

        assert result["status"] == "success"
        # Since tweet is already seen, reply generation and action execution should NOT be triggered
        mock_gen_reply.assert_not_called()
        mock_reply_action.assert_not_called()
        assert result["replies_posted"] == 0


@pytest.mark.asyncio
async def test_sniper_check_targets_safety_guard_rate_limit(
    db_session: AsyncSession,
    sample_persona_with_kols: Persona,
) -> None:
    """Tests that when SafetyGuard indicates rate limit or cooldown, sniper reply is skipped."""
    from xbot.tasks import _sniper_check_targets_async

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@marketanalyst",
        display_name="Market Analyst",
        profile_slug="test_sniper_safeguard",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kols), \
         patch("xbot.safety.guard.SafetyGuard.is_action_safe", AsyncMock(return_value=False)), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True) as mock_lock, \
         patch("xbot.tasks.CheckUserLatestTweet.execute", AsyncMock()) as mock_check_tweet:

        result = await _sniper_check_targets_async()

        assert result["status"] == "success"
        assert result["replies_posted"] == 0
        # Check that browser was not locked or tweet check was not performed because safety guard failed
        mock_check_tweet.assert_not_called()


@pytest.mark.asyncio
async def test_sniper_check_targets_skips_profiles_without_target_kols(
    db_session: AsyncSession,
    sample_persona_no_kols: Persona,
) -> None:
    """Tests that profiles with no configured target KOLs are skipped without acquiring browser lock."""
    from xbot.tasks import _sniper_check_targets_async

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@quiet",
        display_name="Quiet Persona",
        profile_slug="test_quiet_profile",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_no_kols), \
         patch("xbot.tasks.BrowserManager.acquire_lock") as mock_lock:

        result = await _sniper_check_targets_async()

        assert result["status"] == "success"
        assert result["replies_posted"] == 0
        mock_lock.assert_not_called()


@pytest.mark.asyncio
async def test_sniper_check_targets_lock_collision_and_release_on_error(
    db_session: AsyncSession,
    sample_persona_with_kols: Persona,
) -> None:
    """Tests lock collision handling and guaranteed lock release when exceptions occur."""
    from xbot.tasks import _sniper_check_targets_async

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@marketanalyst",
        display_name="Market Analyst",
        profile_slug="test_sniper_lock",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    # 1. Lock collision: acquire_lock returns False
    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kols), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=False) as mock_lock, \
         patch("xbot.tasks.CheckUserLatestTweet.execute", AsyncMock()) as mock_check_tweet:

        result = await _sniper_check_targets_async()
        assert result["replies_posted"] == 0
        mock_check_tweet.assert_not_called()

    # 2. Exception inside task loop: release_lock must still be called in finally
    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kols), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.release_lock", return_value=True) as mock_release_lock, \
         patch("xbot.tasks.BrowserManager.get_context", AsyncMock(side_effect=RuntimeError("Browser crash"))):

        result = await _sniper_check_targets_async()
        # Lock should be cleanly released
        mock_release_lock.assert_called_with("test_sniper_lock")


def test_celery_task_wrapper() -> None:
    """Tests calling the synchronous Celery task wrapper sniper_check_targets."""
    from xbot.tasks import sniper_check_targets

    with patch("xbot.tasks._sniper_check_targets_async", AsyncMock(return_value={"status": "success", "replies_posted": 2})):
        res = sniper_check_targets()
        assert res == {"status": "success", "replies_posted": 2}
