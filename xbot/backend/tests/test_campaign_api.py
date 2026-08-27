"""API Tests for Campaign Studio Endpoints."""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from xbot.main import app
from xbot.database import AsyncSessionLocal
from xbot.models import Profile, Content, ContentType, ContentStatus
from sqlalchemy import select


@pytest.mark.asyncio
async def test_campaign_api_full_cycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with AsyncSessionLocal() as db:
            profile_res = await db.execute(select(Profile))
            profile = profile_res.scalars().first()
            if not profile:
                pytest.skip("No profile in DB")

        # 1. Trigger generate
        with patch("xbot.api.campaigns.execute_on_demand_campaign", AsyncMock()) as mock_exec:
            gen_resp = await ac.post(
                "/api/campaigns/generate",
                json={
                    "profile_id": str(profile.id),
                    "prompt": "build a thread on giva jewellery controversy with media, and a poll on apple event",
                },
            )
            assert gen_resp.status_code == 200
            data = gen_resp.json()
            assert "campaign_id" in data
            campaign_id = data["campaign_id"]

        # 2. Get status
        status_resp = await ac.get(f"/api/campaigns/{campaign_id}/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["campaign_id"] == campaign_id

        # 3. Publish deliverables
        c1 = Content(
            profile_id=profile.id,
            content_type=ContentType.ORIGINAL,
            status=ContentStatus.DRAFT,
            body="Campaign take text",
            ai_metadata={"campaign_id": campaign_id},
        )
        async with AsyncSessionLocal() as db:
            db.add(c1)
            await db.commit()
            await db.refresh(c1)

        pub_resp = await ac.post(
            f"/api/campaigns/{campaign_id}/publish",
            json={
                "content_ids": [str(c1.id)],
                "mode": "schedule",
                "interval_minutes": 30,
            },
        )
        assert pub_resp.status_code == 200
        pub_data = pub_resp.json()
        assert pub_data["status"] == "success"
