"""
End-to-End Verification Script: Anti-AI Typography & Multi-Tweet Threading Engine.
Tests gatekeeper validation, AI thread synthesis, database persistence, and API endpoints.
"""

import asyncio
import sys
import uuid
import httpx
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from xbot.ai.anti_ai_gatekeeper import AntiAIGatekeeper, ANTI_AI_TYPOGRAPHY_DIRECTIVE
from xbot.ai.thread_generator import generate_thread, _build_fallback_thread
from xbot.database import AsyncSessionLocal
from xbot.models.content import Content, ContentStatus, ContentType, ThreadItem
from xbot.models.profile import Profile
from sqlalchemy import select


async def run_verification() -> None:
    print("=" * 70)
    print("🚀 STARTING ANTI-AI TYPOGRAPHY & THREADING ENGINE VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------
    # STEP 1: Test AntiAIGatekeeper
    # -------------------------------------------------------------
    print("\n[STEP 1] Testing Anti-AI Gatekeeper rules...")
    gatekeeper = AntiAIGatekeeper()

    # Good creator post
    good_text = (
        "Most developer tool benchmarks are pure marketing theater.\n\n"
        "If an agent runtime cannot maintain deterministic state across a 15-minute retry loop, "
        "zero-shot code generation is completely useless in production.\n\n"
        "Deterministic state beats clever prompting every single time."
    )
    val_good = gatekeeper.validate(good_text)
    assert val_good.is_valid is True, f"Good post failed: {val_good.errors}"
    print("  ✅ Authentic creator post accepted cleanly.")

    # Lazy uncapitalized chat
    lazy_text = "tbh the problem with ai agents is state management nobody talks about it but if your context drops you are cooked fr"
    val_lazy = gatekeeper.validate(lazy_text)
    assert val_lazy.is_valid is False
    print("  ✅ Extreme A (Lazy uncapitalized WhatsApp chat) rejected.")

    # Corporate buzzword slop
    buzzword_text = (
        "Let us supercharge developer workflows and delve into the tapestry of autonomous systems.\n\n"
        "This is a true game-changer. Let that sink in! Agree or disagree?"
    )
    val_buzz = gatekeeper.validate(buzzword_text)
    assert val_buzz.is_valid is False
    print("  ✅ Extreme B (Corporate AI buzzword slop) rejected.")

    # Emoji bullet slop
    emoji_bullet_text = "Modern tech stack:\n\n🚀 FastAPI\n💡 Redis\n🔥 PostgreSQL"
    val_emoji = gatekeeper.validate(emoji_bullet_text)
    assert val_emoji.is_valid is False
    print("  ✅ Emoji bullet list vomit (🚀 💡 🔥) rejected.")

    # -------------------------------------------------------------
    # STEP 2: Test AI Thread Generator
    # -------------------------------------------------------------
    print("\n[STEP 2] Testing 3-Tier Multi-Tweet Thread Generator...")
    topic = "Why 90% of Autonomous AI Agents Fail in Production"
    thread_resp = await generate_thread(topic=topic, num_tweets=4, archetype="Framework")
    
    assert len(thread_resp.tweets) >= 3, "Thread must have at least 3 tweets"
    assert thread_resp.hook_score >= 80, "Hook score should be high"
    assert thread_resp.items[0].item_type == "hook"
    assert thread_resp.items[-1].item_type == "closer"

    print(f"  ✅ Generated {len(thread_resp.tweets)}-tweet thread on '{thread_resp.topic}'")
    print(f"  ✅ Hook Score: {thread_resp.hook_score}/100 | Archetype: {thread_resp.archetype}")
    for idx, t in enumerate(thread_resp.tweets, 1):
        print(f"     Tweet {idx} ({len(t)}c): {t[:65]}...")

    # -------------------------------------------------------------
    # STEP 3: Test Database Persistence & ThreadItem Child Model
    # -------------------------------------------------------------
    print("\n[STEP 3] Testing SQLite ThreadItem Model Persistence...")
    from xbot.database import init_db
    await init_db()

    async with AsyncSessionLocal() as db:
        # Find test profile
        prof_res = await db.execute(select(Profile).limit(1))
        profile = prof_res.scalar_one_or_none()
        assert profile is not None, "Profile not found in database"

        # Create Thread Content with ThreadItems
        thread_content = Content(
            profile_id=profile.id,
            content_type=ContentType.THREAD,
            body=thread_resp.tweets[0],
            status=ContentStatus.DRAFT,
            ai_metadata={"topic": topic, "tweets": thread_resp.tweets},
        )
        db.add(thread_content)
        await db.flush()

        for idx, t_text in enumerate(thread_resp.tweets):
            t_item = ThreadItem(
                content_id=thread_content.id,
                position=idx,
                item_type="hook" if idx == 0 else "closer" if idx == len(thread_resp.tweets) - 1 else "body",
                text=t_text,
            )
            db.add(t_item)
        await db.commit()

    async with AsyncSessionLocal() as db2:
        q_res = await db2.execute(select(Content).where(Content.id == thread_content.id))
        saved_thread = q_res.scalar_one()
        assert len(saved_thread.thread_items) == len(thread_resp.tweets)
        print(f"  ✅ Stored draft thread {saved_thread.id} with {len(saved_thread.thread_items)} child ThreadItems.")

    # -------------------------------------------------------------
    # STEP 4: Test FastAPI Endpoints (Port 8200)
    # -------------------------------------------------------------
    print("\n[STEP 4] Testing FastAPI Endpoints on http://127.0.0.1:8200...")
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8200", timeout=30.0) as client:
        # Test generate-thread tool endpoint
        tool_resp = await client.post(
            "/api/tools/generate-thread",
            json={
                "profile_slug": "test_profile1",
                "topic": "Deterministic Systems vs Scaled Models",
                "num_tweets": 3,
                "archetype": "Contrarian Breakdown",
            }
        )
        assert tool_resp.status_code == 200, f"Tool endpoint failed: {tool_resp.text}"
        data = tool_resp.json()
        assert "tweets" in data and len(data["tweets"]) >= 3
        print("  ✅ POST /api/tools/generate-thread returned valid 3-tier thread.")

        # Test drafts retrieval endpoint
        drafts_resp = await client.get(f"/api/profiles/{profile.id}/drafts")
        assert drafts_resp.status_code == 200
        drafts_data = drafts_resp.json()
        has_thread_draft = any(d.get("content_type") == "thread" for d in drafts_data)
        assert has_thread_draft is True, "Drafts list must contain the staged thread"
        print(f"  ✅ GET /api/profiles/{profile.id}/drafts returned staged thread draft.")

    print("\n" + "=" * 70)
    print("🎉 ALL VERIFICATION TESTS PASSED 100%!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_verification())
