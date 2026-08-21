from __future__ import annotations

import asyncio
import datetime
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from ruamel.yaml import YAML
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.database import get_db
from xbot.main import app
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.base import Base
from xbot.models.content import Content, ContentStatus
from xbot.models.profile import Profile, ProfileStatus, RateLimit
from xbot.models.session import Action, ActionStatus, ActionType, Session

yaml = YAML(typ="safe")
yaml.default_flow_style = False

# Setup test DB
TEST_DATABASE_URL = "sqlite+aiosqlite:///test_temp_api.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


import xbot.models  # Ensure all models are registered on Base.metadata


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


# Create synchronous client for FastAPI
client = TestClient(app)


@pytest.fixture(autouse=True)
def configure_db_override() -> Generator[None, None, None]:
    """Configure dependency override for the duration of the test module."""
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> Generator[None, None, None]:
    asyncio.run(create_tables())
    yield
    asyncio.run(drop_tables())


async def create_tables() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def populate_profile_files(profile_dir: Path) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    # Persona
    persona_data = {
        "id": "api_test_slug",
        "display_name": "API Test Slug",
        "x_handle": "@apitest",
        "identity": {"background": "Background"},
        "personality": {"traits": ["funny"], "values": ["truth"], "communication_style": "humorous"},
        "interests": {"primary": ["QA"], "secondary": [], "will_not_discuss": []},
        "writing_style": {"tone": "casual", "typical_length": "short", "formatting": [], "examples": []},
        "goals": {"short_term": [], "long_term": [], "content_pillars": []},
        "rules": {"always": [], "never": []},
    }
    with (profile_dir / "persona.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(persona_data, f)

    # Strategy
    strategy_data = {
        "last_updated": "2026-06-18",
        "current_focus": {"primary": "Testing API"},
        "content_strategy": {"posting_frequency": "1 per day", "best_times": [], "top_performing_topics": [], "underperforming_topics": []},
        "engagement_strategy": {"daily_targets": {"likes": "10", "replies": "5", "follows": "2"}, "priority_accounts": []},
    }
    with (profile_dir / "strategy.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(strategy_data, f)


@pytest.mark.asyncio
async def test_rest_endpoints(tmp_path: Path) -> None:
    profile_slug = "api_test_slug"
    profile_dir = tmp_path / profile_slug
    populate_profile_files(profile_dir)

    # Patch profiles module BASE_PROFILE_DIR to use our temp path
    import xbot.api.profiles
    xbot.api.profiles.BASE_PROFILE_DIR = str(tmp_path)

    # Create session to populate DB
    async with TestingSessionLocal() as session:
        db_profile = Profile(
            profile_slug=profile_slug,
            x_handle="@apitest",
            display_name="API Test",
            status=ProfileStatus.ACTIVE,
        )
        session.add(db_profile)
        await session.commit()
        await session.refresh(db_profile)
        profile_id = db_profile.id

        # Add session
        db_session = Session(
            profile_id=profile_id,
            status="completed",
            started_at=datetime.datetime.utcnow(),
            ended_at=datetime.datetime.utcnow(),
            actions_planned=2,
            actions_completed=2,
        )
        session.add(db_session)
        await session.commit()
        await session.refresh(db_session)
        session_id = db_session.id

        # Add Action
        db_action = Action(
            profile_id=profile_id,
            session_id=session_id,
            action_type=ActionType.LIKE,
            target_url="https://x.com/tweet1",
            status=ActionStatus.COMPLETED,
            executed_at=datetime.datetime.utcnow(),
        )
        session.add(db_action)

        # Add Content
        db_content = Content(
            profile_id=profile_id,
            body="Tweet content text",
            status=ContentStatus.POSTED,
            posted_at=datetime.datetime.utcnow(),
        )
        session.add(db_content)

        # Add snapshot
        db_snapshot = AnalyticsSnapshot(
            profile_id=profile_id,
            snapshot_date=datetime.date.today(),
            followers=250,
            following=100,
        )
        session.add(db_snapshot)

        # Add Rate Limit
        db_lim = RateLimit(
            profile_id=profile_id,
            action_type="like",
            count_today=3,
        )
        session.add(db_lim)
        await session.commit()

    # 1. Test GET /api/profiles/{id}/sessions
    res = client.get(f"/api/profiles/{profile_id}/sessions")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["id"] == str(session_id)

    # 2. Test GET /api/sessions/{id}
    res = client.get(f"/api/sessions/{session_id}")
    assert res.status_code == 200
    assert res.json()["id"] == str(session_id)
    assert res.json()["status"] == "completed"

    # 3. Test GET /api/sessions/{id}/actions
    res = client.get(f"/api/sessions/{session_id}/actions")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["action_type"] == "like"

    # 4. Test GET /api/profiles/{id}/content
    res = client.get(f"/api/profiles/{profile_id}/content")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["body"] == "Tweet content text"

    # 5. Test GET /api/profiles/{id}/analytics
    res = client.get(f"/api/profiles/{profile_id}/analytics")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["followers"] == 250

    # 6. Test GET /api/profiles/{id}/monetization
    res = client.get(f"/api/profiles/{profile_id}/monetization")
    assert res.status_code == 200
    assert "ads_revenue_sharing" in res.json()
    assert res.json()["ads_revenue_sharing"]["progress"]["followers"]["current"] == 250

    # 7. Test GET /api/profiles/{id}/persona
    res = client.get(f"/api/profiles/{profile_id}/persona")
    assert res.status_code == 200
    assert res.json()["id"] == "api_test_slug"

    # 8. Test PUT /api/profiles/{id}/persona
    updated_persona = {
        "id": "api_test_slug",
        "display_name": "Updated API Test Slug",
        "x_handle": "@apitest",
        "identity": {"background": "Background"},
        "personality": {"traits": ["funny"], "values": ["truth"], "communication_style": "humorous"},
        "interests": {"primary": ["QA"], "secondary": [], "will_not_discuss": []},
        "writing_style": {"tone": "casual", "typical_length": "short", "formatting": [], "examples": []},
        "goals": {"short_term": [], "long_term": [], "content_pillars": []},
        "rules": {"always": [], "never": []},
    }
    res = client.put(f"/api/profiles/{profile_id}/persona", json=updated_persona)
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Verify updated persona on disk
    res = client.get(f"/api/profiles/{profile_id}/persona")
    assert res.json()["display_name"] == "Updated API Test Slug"

    # 9. Test GET /api/profiles/{id}/strategy
    res = client.get(f"/api/profiles/{profile_id}/strategy")
    assert res.status_code == 200
    assert res.json()["current_focus"]["primary"] == "Testing API"

    # 10. Test GET /api/health
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["redis_connected"] is True or res.json()["redis_connected"] is False

    # 11. Test GET /api/rate-limits
    res = client.get("/api/rate-limits")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["profile_slug"] == "api_test_slug"

    # 12. Test POST /api/system/pause and POST /api/system/resume
    res = client.post("/api/system/pause")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    res = client.post("/api/system/resume")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # 13. Test GET /api/system/config
    res = client.get("/api/system/config")
    assert res.status_code == 200
    assert "LITELLM_PRIMARY_MODEL" in res.json()
