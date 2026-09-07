import asyncio
import os
import sys
import uuid
import datetime
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile
from xbot.models.content import Content, ContentType, ContentStatus
from xbot.ai.meme_renderer import render_dark_infographic
from sqlalchemy import select

async def test():
    print("1. Rendering 4:5 Dark Infographic image...")
    img_path = render_dark_infographic(
        title="Modern AI Recommendation Multipliers",
        bullet_points=[
            "Author Reply-Back: +150x rank multiplier",
            "Bookmark Potential: +50x discovery boost",
            "Reading Dwell (>2 min): +10x retention boost",
            "External URLs in Body: -70% suppression penalty"
        ],
        stat_badge="Phoenix / Grok Engine",
    )
    abs_img_path = os.path.abspath(img_path)
    print(f"Rendered image: {abs_img_path} (exists: {os.path.exists(abs_img_path)})")

    async with AsyncSessionLocal() as session:
        # Get profile
        res = await session.execute(select(Profile).limit(1))
        profile = res.scalar_one_or_none()
        if not profile:
            print("No profile found in DB!")
            return

        post_body = "The math behind modern algorithmic reach: why comments and bookmarks matter 10x more than likes. 📊"
        
        # Stage draft with media_paths
        draft = Content(
            profile_id=profile.id,
            content_type=ContentType.ORIGINAL,
            body=post_body,
            status=ContentStatus.DRAFT,
            ai_metadata={
                "require_approval": True,
                "staged_at": datetime.datetime.utcnow().isoformat(),
                "reasoning": "Algorithmic breakdown with 4:5 visual infographic attachment",
                "media_paths": [abs_img_path],
                "visual_spec": {
                    "format_type": "dark_infographic",
                    "aspect_ratio": "4:5",
                    "tweet_copy": post_body,
                }
            }
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        draft_id = draft.id
        profile_id = profile.id
        print(f"Staged draft in DB: id={draft_id}")

    # Now approve and execute draft via HTTP API (or directly in tasks)
    import httpx
    print(f"2. Calling approve API for draft {draft_id}...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"http://127.0.0.1:8200/api/profiles/{profile_id}/drafts/{draft_id}/approve")
        print(f"Approve response: status={resp.status_code}, json={resp.json()}")

    # Check updated status in DB
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Content).where(Content.id == draft_id))
        updated_draft = res.scalar_one_or_none()
        print(f"Updated draft status in DB: {updated_draft.status if updated_draft else 'not found'}")

if __name__ == "__main__":
    asyncio.run(test())
