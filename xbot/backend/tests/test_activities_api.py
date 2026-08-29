from __future__ import annotations

import datetime
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from xbot.main import app
from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus


@pytest_asyncio.fixture
async def sample_profile_with_actions():
    async with AsyncSessionLocal() as db:
        profile_id = uuid.uuid4()
        prof = Profile(
            id=profile_id,
            display_name="Test Creator",
            profile_slug="test_creator",
            x_handle="@testcreator",
            status=ProfileStatus.ACTIVE,
        )
        db.add(prof)

        sess_id = uuid.uuid4()
        sess = Session(
            id=sess_id,
            profile_id=profile_id,
            status=SessionStatus.COMPLETED,
            started_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2),
            actions_completed=3,
        )
        db.add(sess)

        now = datetime.datetime.utcnow()

        # Action 1: Reply 1h ago
        a1 = Action(
            profile_id=profile_id,
            session_id=sess_id,
            action_type=ActionType.REPLY,
            target_url="https://x.com/pewpiece/status/123456789",
            content="This chapter animation looks incredible!",
            status=ActionStatus.COMPLETED,
            executed_at=now - datetime.timedelta(hours=1),
            duration_ms=2500,
        )

        # Action 2: Like 5h ago
        a2 = Action(
            profile_id=profile_id,
            session_id=sess_id,
            action_type=ActionType.LIKE,
            target_url="https://x.com/sandman_AP/status/987654321",
            status=ActionStatus.COMPLETED,
            executed_at=now - datetime.timedelta(hours=5),
            duration_ms=1200,
        )

        # Action 3: Post 18h ago
        a3 = Action(
            profile_id=profile_id,
            session_id=sess_id,
            action_type=ActionType.POST,
            content="Testing M4 Max efficiency benchmarks in production workloads.",
            status=ActionStatus.COMPLETED,
            executed_at=now - datetime.timedelta(hours=18),
            duration_ms=4500,
        )

        # Action 4: Follow 2d ago
        a4 = Action(
            profile_id=profile_id,
            session_id=sess_id,
            action_type=ActionType.FOLLOW,
            target_url="https://x.com/techinsider",
            status=ActionStatus.COMPLETED,
            executed_at=now - datetime.timedelta(days=2),
            duration_ms=1800,
        )

        # Action 5: Skipped Like 2h ago
        a5 = Action(
            profile_id=profile_id,
            session_id=sess_id,
            action_type=ActionType.LIKE,
            target_url="https://x.com/DiscussingFilm/status/555555555",
            status=ActionStatus.SKIPPED,
            error="Already liked in last 48 hours.",
            executed_at=now - datetime.timedelta(hours=2),
            duration_ms=500,
        )

        db.add_all([a1, a2, a3, a4, a5])
        await db.commit()

        yield str(profile_id)

        # Cleanup
        await db.delete(prof)
        await db.commit()


@pytest.mark.asyncio
async def test_get_profile_activities_time_filters(sample_profile_with_actions: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test 3h filter: should return a1 (1h ago) and a5 (2h ago)
        res_3h = await client.get(f"/api/profiles/{sample_profile_with_actions}/activities?time_range=3h")
        assert res_3h.status_code == 200
        data_3h = res_3h.json()
        assert data_3h["total"] == 2
        assert data_3h["summary_counts"]["total"] == 2
        reply_item = next((it for it in data_3h["items"] if it["action_type"] == "reply"), None)
        assert reply_item is not None
        assert reply_item["target_author"] == "@pewpiece"
        assert reply_item["target_tweet_id"] == "123456789"
        assert "chapter animation" in reply_item["content"]

        # 2. Test 6h filter: should include a1, a5, and a2 (5h ago)
        res_6h = await client.get(f"/api/profiles/{sample_profile_with_actions}/activities?time_range=6h")
        assert res_6h.status_code == 200
        data_6h = res_6h.json()
        assert data_6h["total"] == 3

        # 3. Test 24h filter: should include a1, a2, a3 (18h ago), a5
        res_24h = await client.get(f"/api/profiles/{sample_profile_with_actions}/activities?time_range=24h")
        assert res_24h.status_code == 200
        data_24h = res_24h.json()
        assert data_24h["total"] == 4

        # 4. Test 7d filter: should include all 5 actions
        res_7d = await client.get(f"/api/profiles/{sample_profile_with_actions}/activities?time_range=7d")
        assert res_7d.status_code == 200
        data_7d = res_7d.json()
        assert data_7d["total"] == 5


@pytest.mark.asyncio
async def test_get_profile_activities_type_and_search_filters(sample_profile_with_actions: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Filter by action_type=reply
        res_rep = await client.get(f"/api/profiles/{sample_profile_with_actions}/activities?time_range=7d&action_type=reply")
        assert res_rep.status_code == 200
        data_rep = res_rep.json()
        assert data_rep["total"] == 1
        assert data_rep["items"][0]["action_type"] == "reply"

        # 2. Filter by status=skipped
        res_skip = await client.get(f"/api/profiles/{sample_profile_with_actions}/activities?time_range=7d&status=skipped")
        assert res_skip.status_code == 200
        data_skip = res_skip.json()
        assert data_skip["total"] == 1
        assert "Already liked" in data_skip["items"][0]["error"]

        # 3. Filter by search="benchmarks"
        res_search = await client.get(f"/api/profiles/{sample_profile_with_actions}/activities?time_range=7d&search=benchmarks")
        assert res_search.status_code == 200
        data_search = res_search.json()
        assert data_search["total"] == 1
        assert "M4 Max" in data_search["items"][0]["content"]
