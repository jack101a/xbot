import asyncio
import os
import sys
import uuid
from pathlib import Path

# Ensure backend directory is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile
from xbot.models.pipeline import Campaign
from xbot.models.content import Content
from sqlalchemy import select
from xbot.ai.campaign_planner import plan_campaign_from_prompt, DeliverableType
from xbot.pipelines.on_demand_campaign_pipeline import (
    execute_on_demand_campaign,
    get_campaign_status,
)
from xbot.persona.loader import load_persona
from xbot.config import settings

TEST_TOPICS = [
    "one piece god valley film",
    "harry potter series 2026",
    "nolan Odyssey box office collection",
    "spider man 2026 box office collection",
]

async def test_planner_for_topics():
    print("\n" + "="*60)
    print("PHASE 1: Testing Campaign Planner Decomposition for 4 Topics")
    print("="*60)
    
    persona_path = Path(settings.BASE_PROFILE_DIR) / "test_profile1"
    persona = load_persona(persona_path) if persona_path.exists() else None
    
    for topic in TEST_TOPICS:
        print(f"\n[Testing Topic]: {topic}")
        try:
            plan = await plan_campaign_from_prompt(prompt=topic, persona=persona)
            print(f"  Title: {plan.campaign_title}")
            print(f"  Strategy: {plan.overall_strategy[:80]}...")
            print(f"  Deliverables Count: {len(plan.deliverables)}")
            for d in plan.deliverables:
                print(f"    - [{d.type.value.upper()}] {d.topic[:50]} (Search: '{d.search_query}', Media Target: {d.target_media_count})")
        except Exception as e:
            print(f"  FAILED to plan for '{topic}': {e}")
            raise e

async def test_full_execution_for_topic(topic: str):
    print("\n" + "="*60)
    print(f"PHASE 2: Testing Full End-to-End Campaign Generation for: '{topic}'")
    print("="*60)

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Profile).where(Profile.profile_slug == "test_profile1"))
        profile = res.scalar_one_or_none()
        if not profile:
            res_any = await db.execute(select(Profile))
            profile = res_any.scalars().first()
        
        assert profile is not None, "Profile must exist in DB"
        profile_id = str(profile.id)
        campaign_id = f"test_{uuid.uuid4().hex[:8]}"

        print(f"Executing campaign {campaign_id} for profile {profile.x_handle}...")
        result = await execute_on_demand_campaign(
            profile_id=profile_id,
            prompt=topic,
            campaign_id=campaign_id,
            db=db,
            duration_hours=24,
            interval_minutes=30,
            source_type="on_demand",
            media_preference="x_official",
        )

        assert result["status"] == "ready", f"Expected ready, got {result.get('status')}"
        delivs = result.get("deliverables", [])
        print(f"✅ Generated {len(delivs)} deliverables successfully!")

        for idx, d in enumerate(delivs):
            d_type = d.get("type", "unknown")
            d_topic = d.get("topic", "")
            d_media = d.get("media_paths", [])
            print(f"\n  Deliverable #{idx+1}: [{d_type.upper()}] {d_topic}")
            if d_type == "thread":
                tweets = d.get("thread_tweets", [])
                print(f"    Tweets ({len(tweets)}):")
                for tidx, tw in enumerate(tweets):
                    print(f"      [{tidx+1}] {tw[:90]}...")
            elif d_type == "poll":
                print(f"    Question: {d.get('question')}")
                print(f"    Options: {d.get('options')}")
            elif d_type == "visual":
                print(f"    Caption Hook: {d.get('text')}")
                print(f"    Image Spec: {d.get('visual_spec', {}).get('image_prompt', '')[:80]}...")
            else:
                print(f"    Post Copy: {d.get('text', '')[:100]}...")
            print(f"    Attached Media: {d_media}")

        # Check persistence in DB
        c_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, campaign_id)
        camp_in_db = await db.get(Campaign, c_uuid)
        assert camp_in_db is not None, "Campaign record must be saved in SQLite"
        print(f"\n✅ Verified Campaign {camp_in_db.id} persisted in SQLite: status='{camp_in_db.status}', deliverables={len(camp_in_db.deliverables or [])}")

async def main():
    await test_planner_for_topics()
    for topic in TEST_TOPICS:
        await test_full_execution_for_topic(topic)

if __name__ == "__main__":
    asyncio.run(main())
