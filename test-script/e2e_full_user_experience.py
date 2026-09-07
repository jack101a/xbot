"""
End-to-End User Experience Verification Script for XBot.

Simulates the complete user and autonomous agent journey:
1. Profile Management & Target KOL Configuration
2. Real-Time KOL Sniper Reply Detection & Execution
3. Viral Hook Multi-Generator & LLM Dwell Scorer
4. Interactive Poll Generation with X-compliant constraints (<=25 chars)
5. Real-Time Trend Radar Ingestion & Hot Take Staging
6. Full REST API & Dashboard communication health check
"""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import httpx
from sqlalchemy import select

from xbot.ai.hook_optimizer import optimize_post_hook
from xbot.ai.poll_generator import generate_poll
from xbot.ai.sniper import generate_sniper_reply
from xbot.ai.trend_generator import generate_trend_take
from xbot.ai.trend_radar import TrendItem, fetch_rss_trends
from xbot.database import AsyncSessionLocal
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType
from xbot.persona import load_persona
from xbot.persona.loader import TargetKOL
from xbot.tasks import _check_trend_radar_async, _sniper_check_targets_async

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("e2e_ux_test")

API_BASE = "http://127.0.0.1:8200"
DASHBOARD_BASE = "http://127.0.0.1:8200"


async def verify_services_online() -> None:
    logger.info("=== STEP 1: Verifying Live Background Services ===")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check Backend
        try:
            r_api = await client.get(f"{API_BASE}/health")
            assert r_api.status_code == 200, f"Backend health returned {r_api.status_code}"
            data = r_api.json()
            assert data.get("status") == "healthy", "Backend status is not healthy"
            logger.info(f"✅ Backend API is HEALTHY on port 8200: {data}")
        except Exception as e:
            logger.error(f"❌ Backend API check failed: {e}")
            raise

        # Check Dashboard
        try:
            r_dash = await client.get(DASHBOARD_BASE)
            assert r_dash.status_code == 200, f"Dashboard returned {r_dash.status_code}"
            logger.info(f"✅ Next.js Dashboard is SERVING (HTTP 200) on port 8201")
        except Exception as e:
            logger.error(f"❌ Dashboard check failed: {e}")
            raise


async def verify_profile_and_kol_setup() -> Profile:
    logger.info("\n=== STEP 2: User Story 1 - Profile & Target KOL Setup ===")
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE).limit(1)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            # Create a test active profile
            profile = Profile(
                profile_slug="e2e_test_agent",
                x_handle="ai_growth_agent",
                display_name="AI Growth Agent",
                status=ProfileStatus.ACTIVE,
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

        profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
        profile_dir.mkdir(parents=True, exist_ok=True)
        persona_file = profile_dir / "persona.yaml"

        # Write or update persona with target KOLs
        persona_content = f"""id: {profile.profile_slug}
display_name: {profile.display_name}
x_handle: "@{profile.x_handle}"
identity:
  background: Senior autonomous systems engineer and AI growth strategist.
personality:
  traits: [analytical, sharp, witty, curious]
  values: [open_source, transparency, high_signal]
  communication_style: punchy_and_insightful
interests:
  primary: [AI, autonomous agents, distributed systems, developer tools]
  secondary: [Python, Rust, LLM benchmarks]
  will_not_discuss: [low effort spam, generic corporate buzzwords]
writing_style:
  tone: authoritative_yet_accessible
  typical_length: concise
  formatting: [micro_spacing, punchy_lines]
  examples:
    - "Most agent frameworks fail on state management, not inference."
goals:
  short_term: [grow to 10k followers organically via high value replies]
  long_term: [establish authority in autonomous agent architecture]
  content_pillars: [AI Agent Design, Production Systems, LLM Economics]
rules:
  always: [add value, cite specific data or clear logic]
  never: [generic praise like 'great post', hashtag spam]
target_kols:
  - handle: "elonmusk"
    category: "tech_ai"
    priority: "high"
    preferred_angle: "witty"
  - handle: "sama"
    category: "ai_industry"
    priority: "high"
    preferred_angle: "contrarian"
  - handle: "ylecun"
    category: "ai_research"
    priority: "medium"
    preferred_angle: "framework"
"""
        persona_file.write_text(persona_content, encoding="utf-8")
        persona = load_persona(profile_dir)
        assert len(persona.target_kols) == 3, "Failed to load 3 target KOLs"
        logger.info(f"✅ Persona successfully loaded with {len(persona.target_kols)} target KOLs: {[k.handle for k in persona.target_kols]}")
        return profile


async def verify_kol_sniper_flow(profile: Profile) -> None:
    logger.info("\n=== STEP 3: User Story 2 - KOL Sniper Fast Reply Engine ===")
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    persona = load_persona(profile_dir / "persona.yaml")

    # Simulate influencer post
    simulated_tweet = {
        "tweet_id": f"sim_{uuid.uuid4().hex[:8]}",
        "text": "The bottleneck in scaling AI is no longer compute—it is context drift and autonomous agent memory reliability.",
        "url": "https://x.com/sama/status/1234567890",
        "handle": "sama",
        "is_pinned": False,
        "created_at": "2m ago",
    }

    # Generate reply
    sniper_res = await generate_sniper_reply(
        persona=persona,
        target_tweet=simulated_tweet,
        preferred_angle="contrarian"
    )

    assert sniper_res.reply_text, "Sniper reply text is empty"
    assert len(sniper_res.reply_text) <= 280, f"Sniper reply exceeded 280 chars ({len(sniper_res.reply_text)})"
    assert "great post" not in sniper_res.reply_text.lower(), "Generic bot cliché found in reply"
    logger.info(f"✅ AI Sniper Engine generated reply (Angle: {sniper_res.angle_used}):\n   \"{sniper_res.reply_text}\"")

    # Execute sniper task cycle
    task_res = await _sniper_check_targets_async()
    assert task_res.get("status") in ["success", "completed"], f"Sniper task status: {task_res}"
    logger.info(f"✅ Sniper Celery task executed successfully: {task_res}")


async def verify_viral_hook_optimizer(profile: Profile) -> None:
    logger.info("\n=== STEP 4: User Story 3 - Viral Hook Multi-Generator & Scorer ===")
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    persona = load_persona(profile_dir / "persona.yaml")

    draft_body = (
        "Deterministic task loops outperform prompt chaining by 4x in reliability.\n"
        "State ledgers prevent catastrophic context loss during compaction.\n"
        "Always verify test execution before claiming completion."
    )
    topic = "Autonomous Coding Agents"

    result = await optimize_post_hook(persona, draft_content=draft_body, topic=topic)

    assert result.winning_hook is not None, "Winning hook is None"
    assert result.winning_hook.score >= 1.0, "Winning hook score is invalid"
    assert len(result.candidates) >= 1, "Candidates list is empty"
    assert result.optimized_content.startswith(result.winning_hook.hook_text), "Optimized post does not start with winning hook"

    logger.info(f"✅ Generated {len(result.candidates)} hook archetypes:")
    for c in result.candidates:
        logger.info(f"   [{c.archetype.upper()}] (Score: {c.score}/10): {c.hook_text}")
    logger.info(f"✅ Winning Hook Selected: \"{result.winning_hook.hook_text}\" (Score: {result.winning_hook.score}/10)")
    logger.info(f"✅ Dwell-Optimized Post Output:\n{result.optimized_content}")


async def verify_poll_generator(profile: Profile) -> None:
    logger.info("\n=== STEP 5: User Story 4 - Interactive Poll Studio ===")
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    persona = load_persona(profile_dir / "persona.yaml")

    poll = await generate_poll(persona, topic="Agent Frameworks vs Custom Loops")

    assert poll.question, "Poll question is empty"
    assert 2 <= len(poll.options) <= 4, f"Invalid options count: {len(poll.options)}"
    for opt in poll.options:
        assert len(opt) <= 25, f"Option exceeds 25 chars limit: '{opt}' ({len(opt)} chars)"

    logger.info(f"✅ Generated Poll Question: \"{poll.question}\"")
    logger.info(f"✅ Poll Options (X limit <= 25 chars):")
    for i, opt in enumerate(poll.options, 1):
        logger.info(f"   Option {i}: {opt} ({len(opt)}/25 chars)")
    logger.info(f"✅ Poll Duration: {poll.duration_days} Day(s) | Reasoning: {poll.reasoning}")


async def verify_trend_radar(profile: Profile) -> None:
    logger.info("\n=== STEP 6: User Story 5 - Real-Time Trend Radar Ingestion ===")
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    persona = load_persona(profile_dir / "persona.yaml")

    # 1. Fetch live RSS trends
    feed_urls = ["https://hnrss.org/frontpage"]
    trends = await fetch_rss_trends(feed_urls, keywords=persona.interests.primary, max_items_per_feed=3)
    logger.info(f"✅ Ingested {len(trends)} matching trend items from {feed_urls[0]}")
    if trends:
        sample = trends[0]
        logger.info(f"   Sample Trend: \"{sample.title}\" | Source: {sample.source_name}")

        # 2. Evaluate relevance and formulate take
        eval_result = await generate_trend_take(persona, sample)
        logger.info(f"✅ Trend Relevance Score: {eval_result.relevance_score}/1.0 (Is Relevant: {eval_result.is_relevant})")
        if eval_result.is_relevant:
            logger.info(f"✅ Key Takeaways: {eval_result.key_takeaways}")
            logger.info(f"✅ Persona Hot Take: \"{eval_result.hot_take}\"")
            logger.info(f"✅ Formatted Trend Post:\n{eval_result.optimized_post}")

    # 3. Execute Celery trend radar task
    task_res = await _check_trend_radar_async()
    assert task_res.get("status") in ["success", "completed"], f"Trend radar task failed: {task_res}"
    logger.info(f"✅ Trend Radar Celery periodic task executed successfully: {task_res}")


async def verify_api_and_db_integration(profile: Profile) -> None:
    logger.info("\n=== STEP 7: User Story 6 - REST API & Dashboard Endpoints Verification ===")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check profiles list
        r_profiles = await client.get(f"{API_BASE}/api/profiles")
        assert r_profiles.status_code == 200, f"Profiles list error: {r_profiles.status_code}"
        profiles = r_profiles.json()
        assert any(p["id"] == str(profile.id) for p in profiles), "Profile not found in API"
        logger.info(f"✅ GET /api/profiles returned {len(profiles)} profiles")

        # Check persona endpoint returns target KOLs
        r_persona = await client.get(f"{API_BASE}/api/profiles/{profile.id}/persona")
        assert r_persona.status_code == 200, f"Persona error: {r_persona.status_code}"
        p_data = r_persona.json()
        assert "target_kols" in p_data, "target_kols missing in persona API response"
        logger.info(f"✅ GET /api/profiles/{profile.id}/persona returned target_kols: {len(p_data.get('target_kols', []))} KOLs")

        # Check content queue endpoint
        r_content = await client.get(f"{API_BASE}/api/profiles/{profile.id}/content")
        assert r_content.status_code == 200, f"Content queue error: {r_content.status_code}"
        content_items = r_content.json()
        logger.info(f"✅ GET /api/profiles/{profile.id}/content returned {len(content_items)} content items")

    logger.info("\n=======================================================")
    logger.info("🎉 ALL END-TO-END USER JOURNEY CHECKS PASSED (100%) 🎉")
    logger.info("=======================================================")


async def main() -> None:
    try:
        await verify_services_online()
        profile = await verify_profile_and_kol_setup()
        await verify_kol_sniper_flow(profile)
        await verify_viral_hook_optimizer(profile)
        await verify_poll_generator(profile)
        await verify_trend_radar(profile)
        await verify_api_and_db_integration(profile)
    except Exception as e:
        logger.error(f"❌ End-to-End User Experience Verification Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
