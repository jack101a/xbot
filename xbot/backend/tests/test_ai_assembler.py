from __future__ import annotations

import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from ruamel.yaml import YAML
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.ai.assembler import ContextAssembler
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.base import Base
from xbot.models.profile import Profile, ProfileStatus, RateLimit
from xbot.models.session import Action, ActionStatus, ActionType
from xbot.persona import DiaryManager, MemoryManager

yaml = YAML(typ="safe")
yaml.default_flow_style = False

# Setup test DB
TEST_DB_URL = "sqlite+aiosqlite:///test_temp_assembler.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
SessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db() -> None:
    """Creates and teardowns the test database structure."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Yields a clean database session."""
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_assembler_missing_db_profile(db_session: AsyncSession) -> None:
    assembler = ContextAssembler()
    with pytest.raises(ValueError, match="Profile with slug 'non_existent' not found"):
        await assembler.assemble(db_session, "non_existent")


@pytest.mark.asyncio
async def test_assembler_missing_directory(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    # 1. Add profile to DB
    profile = Profile(
        profile_slug="missing_dir_profile",
        x_handle="@missingdir",
        display_name="Missing Dir",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    # 2. Assemble context pointing to tmp_path where missingdir is absent
    assembler = ContextAssembler(base_profile_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Profile directory not found"):
        await assembler.assemble(db_session, "missing_dir_profile")


@pytest.mark.asyncio
async def test_assembler_success(db_session: AsyncSession, tmp_path: Path) -> None:
    profile_slug = "test_persona"
    profile_dir = tmp_path / profile_slug
    profile_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create YAML files
    persona_data = {
        "id": "test_persona",
        "display_name": "Test Persona",
        "x_handle": "@test_persona",
        "identity": {
            "age": 25,
            "location": "Seattle, WA",
            "occupation": "Automated Test Agent",
            "education": "Digital Sandbox",
            "background": "Designed to verify YAML parsing operations.",
        },
        "personality": {
            "traits": ["precise", "tireless"],
            "values": ["correctness"],
            "communication_style": "Clear, uppercase first letters.",
        },
        "interests": {
            "primary": ["pytests", "mocking"],
            "secondary": ["assertions"],
            "will_not_discuss": ["politics"],
        },
        "writing_style": {
            "tone": "objective",
            "typical_length": "1 sentence",
            "formatting": ["no emojis"],
            "examples": ["Testing is successful."],
        },
        "goals": {
            "short_term": ["Pass all tests"],
            "long_term": ["Achieve 100% test coverage"],
            "content_pillars": ["Quality Assurance (100%)"],
        },
        "rules": {
            "always": ["stay in sandbox"],
            "never": ["touch real web"],
        },
    }
    with (profile_dir / "persona.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(persona_data, f)

    config_data = {
        "schedule": {
            "timezone": "America/New_York",
            "active_hours": "09:00-17:00",
            "min_sessions_per_day": 3,
            "max_sessions_per_day": 5,
        },
        "limits": {
            "max_likes_per_day": 50,
            "max_replies_per_day": 15,
            "max_posts_per_day": 5,
            "max_follows_per_day": 10,
        },
    }
    with (profile_dir / "config.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    strategy_data = {
        "last_updated": "2026-06-18",
        "review_period": "weekly",
        "current_focus": {"primary": "Testing Persona Loader"},
        "content_strategy": {
            "posting_frequency": "1 per day",
            "best_times": ["12:00"],
            "top_performing_topics": ["Python"],
            "underperforming_topics": ["Bugs"],
        },
        "engagement_strategy": {
            "daily_targets": {"likes": "5", "replies": "2", "follows": "1"},
            "priority_accounts": ["@pytest_official"],
        },
        "growth_observations": ["More tests = more trust."],
        "adjustments": ["Keep testing."],
    }
    with (profile_dir / "strategy.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(strategy_data, f)

    rel_dir = profile_dir / "relationships"
    rel_dir.mkdir(parents=True, exist_ok=True)
    rel_data = {
        "accounts": {
            "tester_bob": {
                "display_name": "Bob the Tester",
                "first_seen": "2026-06-18",
                "relationship": "colleague",
                "sentiment": "highly positive",
                "interaction_count": 5,
                "last_interaction": "2026-06-18",
                "notes": "Great tester",
            }
        }
    }
    with (rel_dir / "known_accounts.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(rel_data, f)

    # Write diary and memory entries
    diary_mgr = DiaryManager(profile_dir)
    diary_mgr.append_entry(
        mood="focused",
        what_i_did="Coded context assembler tests",
        what_i_learned="Faking databases is fun",
        how_it_went="Smooth",
        thoughts_for_next_time="Refactor prompts",
        session_num=1,
        date_str="2026-06-18",
    )

    memory_mgr = MemoryManager(profile_dir)
    memory_mgr.append_important(
        content="ContextAssembler is implemented",
        evidence="Test coverage verify it",
        importance=0.95,
    )

    # 2. Add profile and database records
    # Account is 5 days old relative to test execution time
    created_at = datetime.datetime(2026, 6, 18, 15, 0, 0) - datetime.timedelta(days=5)
    db_profile = Profile(
        profile_slug=profile_slug,
        x_handle="@test_persona",
        display_name="Test Persona",
        status=ProfileStatus.ACTIVE,
        created_at=created_at,
    )
    db_session.add(db_profile)
    await db_session.commit()
    await db_session.refresh(db_profile)

    # Add snapshot
    snapshot = AnalyticsSnapshot(
        profile_id=db_profile.id,
        snapshot_date=datetime.date(2026, 6, 18),
        followers=120,
        following=80,
        total_tweets=45,
        impressions_24h=1500,
        engagements_24h=75,
        engagement_rate=0.05,
    )
    db_session.add(snapshot)

    # Add rate limits (used 10 likes and 2 replies)
    lim_like = RateLimit(
        profile_id=db_profile.id,
        action_type="like",
        count_today=10,
        count_this_hour=2,
    )
    lim_reply = RateLimit(
        profile_id=db_profile.id,
        action_type="reply",
        count_today=2,
        count_this_hour=1,
    )
    db_session.add_all([lim_like, lim_reply])

    # Add action today so far (e.g. at local 10:00 AM America/New_York)
    # America/New_York is UTC-4 (daylight saving time in June)
    # So 10:00 AM EDT is 14:00 (2:00 PM) UTC
    action_time = datetime.datetime(2026, 6, 18, 14, 0, 0)
    action = Action(
        profile_id=db_profile.id,
        session_id=db_profile.id,  # just mock ID
        action_type=ActionType.POST,
        content="Testing context assembler!",
        status=ActionStatus.COMPLETED,
        executed_at=action_time,
    )
    db_session.add(action)
    await db_session.commit()

    # 3. Assemble and Assert
    assembler = ContextAssembler(base_profile_dir=str(tmp_path))
    # We specify now_utc as 2026-06-18 15:00:00 UTC (11:00 AM EDT)
    now_utc = datetime.datetime(2026, 6, 18, 15, 0, 0)
    context = await assembler.assemble(db_session, profile_slug, now_utc=now_utc)

    # Verification
    assert context.persona.id == "test_persona"
    assert context.persona.identity.age == 25
    assert context.config.schedule.timezone == "America/New_York"
    assert context.strategy.review_period == "weekly"

    # Current state
    assert context.current_time == "2026-06-18 11:00 AM"  # 15:00 UTC -> 11:00 AM EDT
    assert context.account_age_days == 5
    assert context.followers_count == 120
    assert context.following_count == 80

    # Actions today
    assert "Testing context assembler!" in context.today_actions_summary
    assert "10:00 AM" in context.today_actions_summary  # local time for 14:00 UTC action

    # Rate limits remaining
    # Max likes = 50, used 10 -> remaining 40
    # Max replies = 15, used 2 -> remaining 13
    assert "LIKE: 40 remaining" in context.rate_budget_remaining
    assert "REPLY: 13 remaining" in context.rate_budget_remaining
    # Max posts = 5, default used 0 -> remaining 5
    assert "POST: 5 remaining" in context.rate_budget_remaining

    # Diary entries
    assert "Coded context assembler tests" in context.recent_diary_entries
    assert "focused" in context.recent_diary_entries

    # Active memories
    assert "ContextAssembler is implemented" in context.active_memories

    # Relationships
    assert "@tester_bob" in context.relationships_summary
    assert "colleague" in context.relationships_summary

    # Analytics summary (7 days)
    assert "120" in context.analytics_summary
    assert "5.00%" in context.analytics_summary

    # Render User Prompt
    rendered = context.render_user_prompt()
    assert "## Session Context" in rendered
    assert "## Active Creator Memories" in rendered
    assert "Testing context assembler!" in rendered
    assert "ContextAssembler is implemented" in rendered
