import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.ai.campaign_planner import CampaignPlan, DeliverableSpec, DeliverableType
from xbot.models.base import Base
from xbot.models import Profile, Content, ContentType, ContentStatus
import xbot.models  # Register all models on Base.metadata
from xbot.pipelines.on_demand_campaign_pipeline import (
    execute_on_demand_campaign,
    get_campaign_status,
    publish_campaign_deliverables,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def _reset_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_execute_on_demand_campaign_flow(tmp_path):
    """Verifies that an on-demand campaign executes research, synthesis, and DB staging in isolated DB."""
    await _reset_db()
    async with TestingSessionLocal() as db:
        profile = Profile(
            id=uuid.uuid4(),
            profile_slug="testcreator",
            x_handle="testcreator",
            display_name="Test Creator",
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
        prompt = "build a thread on giva jewellery controversy with media, and a poll on upcoming apple launch event"

        mock_plan = CampaignPlan(
            campaign_title="GIVA Backlash & Apple Hype",
            theme="Controversies and Tech Launches",
            overall_strategy="Deliverable combo",
            deliverables=[
                DeliverableSpec(
                    id="deliv_1",
                    type=DeliverableType.THREAD,
                    topic="GIVA Jewellery Ad Controversy",
                    search_query="giva jewellery controversy",
                    target_media_count=2,
                    instructions="Focus on the marketing misstep",
                ),
                DeliverableSpec(
                    id="deliv_2",
                    type=DeliverableType.POLL,
                    topic="Apple Launch Event Purchase Decision",
                    search_query="apple event upgrade",
                    target_media_count=0,
                    instructions="A/B choice",
                ),
            ],
        )

        # Mock X search results
        mock_search_results = [
            {
                "text": "The GIVA jewellery ad sparked massive debate online today.",
                "author": "ad_watch",
                "media_urls": ["https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=300"],
            },
            {
                "text": "Marketing teams need to understand audience sensibilities better.",
                "author": "brand_expert",
                "media_urls": ["https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=300"],
            },
        ]

        with patch("xbot.pipelines.on_demand_campaign_pipeline.plan_campaign_from_prompt", AsyncMock(return_value=mock_plan)), \
             patch("xbot.pipelines.on_demand_campaign_pipeline._search_and_scrape_x", AsyncMock(return_value=mock_search_results)), \
             patch("xbot.pipelines.on_demand_campaign_pipeline._download_media_urls", AsyncMock(return_value=["/tmp/img1.jpg", "/tmp/img2.jpg"])), \
             patch("xbot.pipelines.on_demand_campaign_pipeline.get_ai_client"):

            res = await execute_on_demand_campaign(
                profile_id=profile.id,
                prompt=prompt,
                campaign_id=campaign_id,
                db=db,
            )

            assert res["status"] == "ready"
            assert res["campaign_id"] == campaign_id
            assert len(res["deliverables"]) == 2

            # Check status tracking
            status_info = get_campaign_status(campaign_id)
            assert status_info["status"] == "ready"
            assert len(status_info["deliverables"]) == 2

            # Verify Content staged in DB
            stmt = select(Content).where(Content.ai_metadata["campaign_id"].as_string() == campaign_id)
            staged_records = (await db.execute(stmt)).scalars().all()
            assert len(staged_records) == 2


@pytest.mark.asyncio
async def test_publish_campaign_deliverables():
    """Verifies publishing deliverables either instantly or via scheduled queue in isolated test DB."""
    await _reset_db()
    async with TestingSessionLocal() as db:
        profile = Profile(
            id=uuid.uuid4(),
            profile_slug="testcreator2",
            x_handle="testcreator2",
            display_name="Test Creator 2",
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        campaign_id = f"camp_{uuid.uuid4().hex[:8]}"

        # Create staged content
        c1 = Content(
            profile_id=profile.id,
            content_type=ContentType.ORIGINAL,
            status=ContentStatus.DRAFT,
            body="Standalone campaign post take.",
            ai_metadata={"campaign_id": campaign_id, "deliverable_id": "deliv_1"},
        )
        c2 = Content(
            profile_id=profile.id,
            content_type=ContentType.POLL,
            status=ContentStatus.DRAFT,
            body="Campaign poll question.",
            ai_metadata={"campaign_id": campaign_id, "deliverable_id": "deliv_2", "poll": {"options": ["A", "B"]}},
        )
        db.add_all([c1, c2])
        await db.commit()
        await db.refresh(c1)
        await db.refresh(c2)

        # 1. Schedule mode (sets status to APPROVED)
        res_sched = await publish_campaign_deliverables(
            campaign_id=campaign_id,
            content_ids=[str(c1.id), str(c2.id)],
            mode="schedule",
            interval_minutes=60,
            db=db,
        )
        assert res_sched["status"] == "success"
        assert res_sched["mode"] == "schedule"

        await db.refresh(c1)
        await db.refresh(c2)
        assert c1.status == ContentStatus.APPROVED
        assert c2.status == ContentStatus.APPROVED
