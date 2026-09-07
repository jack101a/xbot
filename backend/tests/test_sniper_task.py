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
from xbot.contracts.browser import ActionResult, BrowserActionType, BrowserRequest, BrowserResponse
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
        identity=Identity(background="Quiet observer", occupation="Observer"),
        personality=Personality(traits=["silent"], values=["peace"], communication_style="Minimal"),
        interests=Interests(primary=["Observing"], secondary=[], will_not_discuss=[]),
        writing_style=WritingStyle(tone="quiet", typical_length="short", formatting=[], examples=[]),
        goals=Goals(short_term=[], long_term=[], content_pillars=[]),
        rules=Rules(always=[], never=[]),
        target_kols=[],
    )


def test_sniper_beat_schedule_registration() -> None:
    """Verifies that Celery Beat schedule contains sniper_check_targets with a 120-second interval."""
    beat_schedule = celery_app.conf.beat_schedule
    assert "sniper-check-targets-every-120-seconds" in beat_schedule
    schedule = beat_schedule["sniper-check-targets-every-120-seconds"]
    assert schedule["task"] == "xbot.tasks.sniper_check_targets"
    assert schedule["schedule"] == 120.0


@pytest.mark.asyncio
async def test_sniper_check_targets_executes_reply_and_records_db(
    db_session: AsyncSession,
    sample_persona_with_kols: Persona,
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

    # 2. Mock latest tweet
    tweet_data_sama = {
        "tweet_id": "998877665544",
        "author": "sama",
        "text": "Compute efficiency is doubling every 6 months across our infrastructure.",
        "url": "https://x.com/sama/status/998877665544",
        "created_at": "3m",
        "is_pinned": False,
    }

    mock_sniper_result = SniperReplyResult(
        reply_text="Compute efficiency doubles, but interconnect latency remains bound by physics. How are you routing around the latency bottleneck?",
        angle_used="framework",
        confidence=0.92,
        reasoning="Framing compute gains vs physical latency bottleneck.",
    )

    # Mock container browser
    async def mock_browser_execute(req: BrowserRequest) -> BrowserResponse:
        if req.action == BrowserActionType.CHECK_USER_LATEST:
            return BrowserResponse(
                status="success",
                action=req.action,
                action_result=ActionResult(status="success", target_id="998877665544", raw=tweet_data_sama),
            )
        elif req.action == BrowserActionType.REPLY:
            return BrowserResponse(
                status="success",
                action=req.action,
                action_result=ActionResult(status="success", target_id="reply_123"),
            )
        return BrowserResponse(status="failed", action=req.action, error="Unknown action")

    mock_container = MagicMock()
    mock_container.browser.execute = AsyncMock(side_effect=mock_browser_execute)

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kols), \
         patch("xbot.tasks.generate_sniper_reply", AsyncMock(return_value=mock_sniper_result)) as mock_gen_reply, \
         patch("xbot.container.get_container", return_value=mock_container), \
         patch("xbot.tasks.sleep_with_jitter", AsyncMock()):

        result = await _sniper_check_targets_async()

        assert result["status"] == "success"
        assert result["profiles_processed"] >= 1
        assert result["replies_posted"] >= 1

        # Verify container.browser.execute was called
        assert mock_container.browser.execute.call_count >= 2

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

    mock_container = MagicMock()
    mock_container.browser.execute = AsyncMock(return_value=BrowserResponse(
        status="success",
        action=BrowserActionType.CHECK_USER_LATEST,
        action_result=ActionResult(status="success", target_id=seen_tweet_id, raw=tweet_data),
    ))

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kols), \
         patch("xbot.tasks.generate_sniper_reply", AsyncMock()) as mock_gen_reply, \
         patch("xbot.container.get_container", return_value=mock_container):

        result = await _sniper_check_targets_async()

        assert result["status"] == "success"
        # Since tweet is already seen, reply generation should NOT be triggered
        mock_gen_reply.assert_not_called()
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

    mock_container = MagicMock()

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kols), \
         patch("xbot.safety.guard.SafetyGuard.is_action_safe", AsyncMock(return_value=False)), \
         patch("xbot.container.get_container", return_value=mock_container):

        result = await _sniper_check_targets_async()

        assert result["status"] == "success"
        assert result["replies_posted"] == 0
        mock_container.browser.execute.assert_not_called()


@pytest.mark.asyncio
async def test_sniper_check_targets_skips_profiles_without_target_kols(
    db_session: AsyncSession,
    sample_persona_no_kols: Persona,
) -> None:
    """Tests that profiles with no configured target KOLs are skipped."""
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

    mock_container = MagicMock()

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_no_kols), \
         patch("xbot.container.get_container", return_value=mock_container):

        result = await _sniper_check_targets_async()

        assert result["status"] == "success"
        assert result["replies_posted"] == 0
        mock_container.browser.execute.assert_not_called()


def test_celery_task_wrapper() -> None:
    """Tests calling the synchronous Celery task wrapper sniper_check_targets."""
    from xbot.tasks import sniper_check_targets

    with patch("xbot.tasks._sniper_check_targets_async", AsyncMock(return_value={"status": "success", "replies_posted": 2})):
        res = sniper_check_targets()
        assert res == {"status": "success", "replies_posted": 2}
