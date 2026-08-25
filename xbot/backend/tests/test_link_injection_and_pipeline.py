from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.ai.growth_scorer import OpportunityScore, score_tweet_opportunity
from xbot.ai.hook_optimizer import extract_links
from xbot.ai.sniper import SniperResult
from xbot.models.base import Base
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
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

TEST_DB_URL = "sqlite+aiosqlite:///test_temp_link_injection.db"
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
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        pass


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def sample_persona_with_kol() -> Persona:
    return Persona(
        id="test_growth_profile",
        display_name="Kaya Growth",
        x_handle="@kayagrowth",
        identity=Identity(background="AI researcher and creator"),
        personality=Personality(
            traits=["analytical", "witty"],
            values=["truth", "signal"],
            communication_style="Direct and sharp",
        ),
        interests=Interests(
            primary=["ai", "systems"],
            secondary=["memes"],
            will_not_discuss=["politics"],
        ),
        writing_style=WritingStyle(
            tone="sharp, direct",
            typical_length="concise",
            formatting=["clean_sentence_casing"],
            examples=["Systems win over willpower."],
        ),
        goals=Goals(
            content_pillars=["engineering", "ai"],
            short_term=[],
            long_term=[],
        ),
        rules=Rules(
            never=["delve", "testament"],
            always=["end_with_question_in_sniper"],
        ),
        target_kols=[
            TargetKOL(
                handle="@elite_engineer",
                niche="systems",
                importance=5,
                preferred_angle="contrarian",
            )
        ],
    )


def test_extract_links_helper():
    """Verify that extract_links strips markdown links and naked URLs cleanly."""
    text_with_link = "Check out this breakdown of Phoenix weights: https://x.com/algorithm/doc and save it."
    clean_body, extracted = extract_links(text_with_link)
    assert extracted == "https://x.com/algorithm/doc"
    assert "https://" not in clean_body
    assert "Check out this breakdown of Phoenix weights" in clean_body


@pytest.mark.asyncio
async def test_growth_scorer_integration_skips_low_quality_targets(db_session: AsyncSession, sample_persona_with_kol: Persona):
    """Verify that _sniper_check_targets_async evaluates opportunity score and skips stale/bot tweets."""
    from xbot.tasks import _sniper_check_targets_async

    profile = Profile(
        id=uuid.uuid4(),
        display_name="Kaya Growth",
        x_handle="@kayagrowth",
        profile_slug="test_growth_profile",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    # Stale tweet > 24 hours old with link penalty -> Phoenix score will be < 40 and recommend 'skip'
    stale_tweet_data = {
        "tweet_id": "999888777",
        "text": "Breaking news report at https://news.com/stale-link",
        "url": "https://x.com/elite_engineer/status/999888777",
        "handle": "elite_engineer",
        "created_at": "2d",
        "author_reply_rate": 0.01,
        "likes": 5,
        "replies": 0,
    }

    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    mock_redis.sismember.return_value = False

    with patch("xbot.tasks.redis.from_url", return_value=mock_redis), \
         patch("xbot.tasks.AsyncSessionLocal", TestSessionLocal), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kol), \
         patch("xbot.tasks.SafetyGuard.is_action_safe", AsyncMock(return_value=True)), \
         patch("xbot.tasks.SafetyGuard.record_action_success", AsyncMock()), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.release_lock", return_value=True), \
         patch("xbot.tasks.CheckUserLatestTweet.execute", AsyncMock(return_value=stale_tweet_data)), \
         patch("xbot.tasks.ReplyToTweet.execute", AsyncMock(return_value=True)) as mock_reply:

        res = await _sniper_check_targets_async()
        assert res["replies_posted"] == 0
        mock_reply.assert_not_called()


@pytest.mark.asyncio
async def test_growth_scorer_integration_executes_high_opportunity_target(db_session: AsyncSession, sample_persona_with_kol: Persona):
    """Verify that _sniper_check_targets_async proceeds with sniper reply on high opportunity score targets."""
    from xbot.tasks import _sniper_check_targets_async

    profile = Profile(
        id=uuid.uuid4(),
        display_name="Kaya Growth",
        x_handle="@kayagrowth",
        profile_slug="test_growth_profile",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    # Fresh, high-velocity conversation tweet with active author
    fresh_tweet_data = {
        "tweet_id": "1122334455",
        "text": "What is the single most underrated architecture choice in modern AI recommender systems?",
        "url": "https://x.com/elite_engineer/status/1122334455",
        "handle": "elite_engineer",
        "created_at": "5m",
        "author_reply_rate": 0.85,
        "likes": 120,
        "replies": 45,
        "is_verified": True,
    }

    mock_redis = MagicMock()
    mock_redis.exists.return_value = False
    mock_redis.sismember.return_value = False

    mock_sniper_res = SniperResult(
        reply_text="Most teams over-index on model size when embedding cache locality yields 10x lower latency. Are you optimizing weights or memory bandwidth?",
        debate_catalyst="Are you optimizing weights or memory bandwidth?",
        angle_used="contrarian",
        confidence=0.95,
        reasoning="High opportunity target with strong author reply probability.",
    )

    with patch("xbot.tasks.redis.from_url", return_value=mock_redis), \
         patch("xbot.tasks.AsyncSessionLocal", TestSessionLocal), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kol), \
         patch("xbot.tasks.SafetyGuard.is_action_safe", AsyncMock(return_value=True)), \
         patch("xbot.tasks.SafetyGuard.record_action_success", AsyncMock()), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.release_lock", return_value=True), \
         patch("xbot.tasks.CheckUserLatestTweet.execute", AsyncMock(return_value=fresh_tweet_data)), \
         patch("xbot.tasks.generate_sniper_reply", AsyncMock(return_value=mock_sniper_res)), \
         patch("xbot.tasks.ReplyToTweet.execute", AsyncMock(return_value=True)) as mock_reply, \
         patch("xbot.tasks.sleep_with_jitter", AsyncMock()):

        res = await _sniper_check_targets_async()
        assert res["status"] == "success"
        assert res["replies_posted"] == 1
        mock_reply.assert_called_once()


@pytest.mark.asyncio
async def test_session_post_link_extraction_and_1st_reply_staging(db_session: AsyncSession, sample_persona_with_kol: Persona):
    """Verify that standalone posts with external links extract the link and stage 1st-reply metadata."""
    from xbot.tasks import _run_session_async
    from xbot.ai.planner import PlannedAction, SessionPlan

    profile = Profile(
        id=uuid.uuid4(),
        display_name="Kaya Growth",
        x_handle="@kayagrowth",
        profile_slug="test_growth_profile",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    plan = SessionPlan(
        mood="analytical",
        reasoning="High-value system architecture breakdown",
        actions=[
            PlannedAction(
                type="post",
                target="feed",
                content="3 Redis optimizations that reduced P99 latency by 70%:\n1. Pipeline commands\n2. Use hashes\n3. Client-side caching\n\nFull deep dive at https://engineering.dev/redis-perf",
                reasoning="High bookmark framework breakdown with extracted link",
                priority=1,
            )
        ],
    )

    mock_config = MagicMock()
    mock_config.mock_mode = False
    mock_config.require_post_approval = True
    mock_config.schedule.timezone = "Asia/Kolkata"
    mock_config.proxy_url = None

    with patch("xbot.tasks.AsyncSessionLocal", TestSessionLocal), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kol), \
         patch("xbot.tasks.load_config", return_value=mock_config), \
         patch("xbot.tasks.plan_session", AsyncMock(return_value=plan)), \
         patch("xbot.tasks.SafetyGuard.is_action_safe", AsyncMock(return_value=True)), \
         patch("xbot.tasks.SafetyGuard.record_action_success", AsyncMock()), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.release_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.get_context", AsyncMock()):

        session_res = await _run_session_async(str(profile.id))
        assert session_res is not None

        # Verify Content draft created in DB
        stmt = select(Content).where(Content.profile_id == profile.id)
        res = await db_session.execute(stmt)
        drafts = res.scalars().all()
        assert len(drafts) == 1
        draft = drafts[0]
        assert draft.status == ContentStatus.DRAFT
        assert "https://" not in draft.body  # Body stripped of link
        assert "3 Redis optimizations" in draft.body
        assert draft.ai_metadata.get("extracted_link") == "https://engineering.dev/redis-perf"
        assert draft.ai_metadata.get("first_reply_text") == "Link / source breakdown: https://engineering.dev/redis-perf"


@pytest.mark.asyncio
async def test_session_post_link_extraction_and_direct_publishing_1st_reply(db_session: AsyncSession, sample_persona_with_kol: Persona):
    """Verify that when require_post_approval is False, ComposePost and ReplyToTweet are executed sequentially."""
    from xbot.tasks import _run_session_async
    from xbot.ai.planner import PlannedAction, SessionPlan

    profile = Profile(
        id=uuid.uuid4(),
        display_name="Kaya Growth",
        x_handle="@kayagrowth",
        profile_slug="test_growth_profile",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    plan = SessionPlan(
        mood="curious",
        reasoning="Visual technical breakdown",
        actions=[
            PlannedAction(
                type="post",
                target="feed",
                content="Distributed state machines explained in 3 visual diagrams.\n\nRead diagram breakdowns at https://diagrams.dev/state-machines",
                reasoning="Visual breakdown",
                priority=1,
            )
        ],
    )

    mock_config = MagicMock()
    mock_config.mock_mode = False
    mock_config.require_post_approval = False
    mock_config.schedule.timezone = "Asia/Kolkata"
    mock_config.proxy_url = None

    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("xbot.tasks.AsyncSessionLocal", TestSessionLocal), \
         patch("xbot.tasks.load_persona", return_value=sample_persona_with_kol), \
         patch("xbot.tasks.load_config", return_value=mock_config), \
         patch("xbot.tasks.plan_session", AsyncMock(return_value=plan)), \
         patch("xbot.tasks.SafetyGuard.is_action_safe", AsyncMock(return_value=True)), \
         patch("xbot.tasks.SafetyGuard.record_action_success", AsyncMock()), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.release_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.get_context", AsyncMock(return_value=mock_context)), \
         patch("xbot.tasks.ComposePost.execute", AsyncMock(return_value=True)) as mock_compose, \
         patch("xbot.tasks.ReplyToTweet.execute", AsyncMock(return_value=True)) as mock_reply, \
         patch("xbot.tasks.sleep_with_jitter", AsyncMock()):

        session_res = await _run_session_async(str(profile.id))
        assert session_res is not None

        # Verify ComposePost was called with clean link-free text
        mock_compose.assert_called_once()
        args, kwargs = mock_compose.call_args
        clean_text_posted = args[1]
        assert "https://" not in clean_text_posted
        assert "Distributed state machines explained" in clean_text_posted

        # Verify ReplyToTweet was executed with 1st reply link injection
        mock_reply.assert_called_once()
        r_args, r_kwargs = mock_reply.call_args
        first_reply_text = r_args[1]
        assert first_reply_text == "Link / source breakdown: https://diagrams.dev/state-machines"
