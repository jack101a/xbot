import pytest
from httpx import AsyncClient, ASGITransport
from xbot.main import app
from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile
from xbot.models.content import Content, ContentType, ContentStatus


import uuid

@pytest.mark.asyncio
async def test_draft_staging_and_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            slug = f"test_draft_{uuid.uuid4().hex[:8]}"
            profile = Profile(
                profile_slug=slug,
                display_name="Draft Test User",
                x_handle=f"@{slug}",
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

            # Insert a staged draft
            draft_content = Content(
                profile_id=profile.id,
                content_type=ContentType.ORIGINAL,
                body="What is your most controversial AI agent architecture take?",
                status=ContentStatus.DRAFT,
                ai_metadata={"reasoning": "High-engagement debate hook"},
            )
            db.add(draft_content)
            await db.commit()
            await db.refresh(draft_content)

            p_id = str(profile.id)
            c_id = str(draft_content.id)

        # 1. Fetch drafts via API
        resp = await client.get(f"/api/profiles/{p_id}/drafts")
        assert resp.status_code == 200
        drafts = resp.json()
        assert len(drafts) >= 1
        assert any(d["id"] == c_id for d in drafts)

        # 2. Dismiss draft via API
        del_resp = await client.delete(f"/api/profiles/{p_id}/drafts/{c_id}")
        assert del_resp.status_code == 200

        # Verify draft is no longer in pending list
        resp2 = await client.get(f"/api/profiles/{p_id}/drafts")
        assert resp2.status_code == 200
        drafts2 = resp2.json()
        assert not any(d["id"] == c_id for d in drafts2)
