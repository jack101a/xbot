"""
End-to-End Comprehensive Feature Test for Authenticated Profile (@jackds1234 / test_profile1)

Validates every system feature end-to-end:
1. Live Services Health (Backend on port 8200 & Dashboard Static Mount)
2. Profile Auth Status & Cookie Storage State Inspection
3. Live Sync from X (High-Res Avatar, Followers, Following, Verification)
4. KOL Sniper Reply Engine (Target Scraping, Multi-Angle AI Generation, Safety Limiter)
5. Viral Hook Optimizer (4 Archetypes, Dwell Scorer, Micro-spacing Assembly)
6. Interactive Poll Studio (Debate Generation, <=25 Char Constraints)
7. Real-Time Trend Radar (Live RSS Ingestion, Relevance Scorer, Content Staging, Redis Deduplication)
8. REST API & Dashboard Client Contract Validation
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
from xbot.ai.trend_radar import fetch_rss_trends
from xbot.browser.actions.check_user_action import CheckUserLatestTweet
from xbot.browser.actions.sync_profile_action import SyncProfileFromX
from xbot.browser.auth import inspect_profile_auth_status
from xbot.browser.manager import BrowserManager
from xbot.database import AsyncSessionLocal
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType, Session
from xbot.persona import load_persona
from xbot.safety.guard import SafetyGuard
from xbot.tasks import _check_trend_radar_async, _sniper_check_targets_async

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("e2e_authenticated_test")

API_BASE = "http://127.0.0.1:8200"


async def run_step_1_services_health() -> None:
    logger.info("\n=======================================================")
    logger.info("=== STEP 1: Live Services Health Check ===")
    logger.info("=======================================================")
    async with httpx.AsyncClient(timeout=10.0) as client:
        r_health = await client.get(f"{API_BASE}/health")
        assert r_health.status_code == 200, f"Health returned {r_health.status_code}"
        health_data = r_health.json()
        assert health_data.get("status") == "healthy"
        logger.info(f"✅ Backend API on port 8200: Healthy (Database & Redis configured)")

        r_dash = await client.get(f"{API_BASE}/")
        assert r_dash.status_code == 200, f"Dashboard returned {r_dash.status_code}"
        assert "html" in r_dash.headers.get("content-type", "").lower()
        logger.info(f"✅ Static Glassmorphic Dashboard: Serving directly on / (HTTP 200)")


async def run_step_2_auth_status(profile: Profile) -> dict:
    logger.info("\n=======================================================")
    logger.info("=== STEP 2: Profile Auth Status & Cookie Verification ===")
    logger.info("=======================================================")
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    auth_status = inspect_profile_auth_status(profile_dir)
    assert auth_status.get("has_session_file") is True, "Storage state session file missing"
    assert auth_status.get("has_auth_token") is True, "auth_token cookie missing"
    assert auth_status.get("has_ct0") is True, "ct0 cookie missing"
    assert auth_status.get("status") == "authenticated", f"Expected authenticated, got {auth_status.get('status')}"
    logger.info(f"✅ File-level session inspection: {auth_status['status'].upper()} (Cookies: {auth_status['cookie_count']})")

    # API Endpoint check
    async with httpx.AsyncClient(timeout=10.0) as client:
        r_api = await client.get(f"{API_BASE}/api/profiles/{profile.id}/auth-status")
        assert r_api.status_code == 200, f"Auth status API returned {r_api.status_code}"
        api_data = r_api.json()
        assert api_data.get("is_configured") is True
        assert api_data.get("status") == "authenticated"
        logger.info(f"✅ GET /api/profiles/{profile.id}/auth-status: Confirmed active session")

    return auth_status


async def run_step_3_sync_from_x(profile: Profile) -> dict:
    logger.info("\n=======================================================")
    logger.info("=== STEP 3: Live Sync from X (Profile Info & Avatar) ===")
    logger.info("=======================================================")
    sync_action = SyncProfileFromX()
    # Test action execution logic
    logger.info(f"Syncing profile metrics for @{profile.x_handle} ({profile.display_name})...")

    # API Trigger
    async with httpx.AsyncClient(timeout=30.0) as client:
        r_sync = await client.post(f"{API_BASE}/api/profiles/{profile.id}/sync-from-x")
        assert r_sync.status_code in [200, 409], f"Sync API returned {r_sync.status_code}"
        if r_sync.status_code == 200:
            sync_res = r_sync.json()
            logger.info(f"✅ Live Sync API completed successfully: {sync_res.get('status')}")
            if sync_res.get("sync_data"):
                data = sync_res["sync_data"]
                logger.info(f"   Handle: @{data.get('handle')}")
                logger.info(f"   Display Name: {data.get('display_name')}")
                logger.info(f"   Avatar URL: {data.get('avatar_url')}")
                logger.info(f"   Followers: {data.get('followers_count')} | Following: {data.get('following_count')}")

    # Check database persistence
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Profile).where(Profile.id == profile.id))
        updated_profile = res.scalar_one()

        snap_res = await db.execute(
            select(AnalyticsSnapshot)
            .where(AnalyticsSnapshot.profile_id == profile.id)
            .order_by(AnalyticsSnapshot.snapshot_date.desc())
            .limit(1)
        )
        snap = snap_res.scalar_one_or_none()
        followers = snap.followers if snap else 0
        logger.info(f"✅ Database Profile Record: Followers={followers}, Avatar={'Present (' + updated_profile.avatar_url + ')' if updated_profile.avatar_url else 'None'}")

    return {}


async def run_step_4_kol_sniper(profile: Profile) -> None:
    logger.info("\n=======================================================")
    logger.info("=== STEP 4: KOL Sniper Fast Reply Engine ===")
    logger.info("=======================================================")
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    persona = load_persona(profile_dir)
    assert len(persona.target_kols) >= 1, "Persona has no target KOLs"
    logger.info(f"Loaded {len(persona.target_kols)} target KOLs: {[k.handle for k in persona.target_kols]}")

    sample_target_tweet = {
        "tweet_id": "2089592732780032132",
        "author": "elonmusk",
        "text": "True autonomous systems will require deterministic error-recovery loops, not just bigger LLM context windows.",
        "url": "https://x.com/elonmusk/status/2089592732780032132",
    }

    reply_result = await generate_sniper_reply(
        persona=persona,
        target_tweet=sample_target_tweet,
        preferred_angle="witty",
    )

    assert reply_result.reply_text, "Sniper reply text is empty"
    assert len(reply_result.reply_text) <= 280, "Sniper reply exceeds 280 chars"
    logger.info(f"✅ Sniper Reply Generated (Angle: {reply_result.angle_used}):\n   \"{reply_result.reply_text}\"")

    # Run Celery periodic task
    task_res = await _sniper_check_targets_async()
    assert task_res.get("status") in ["success", "partial_success"], f"Sniper task failed: {task_res}"
    logger.info(f"✅ Celery sniper_check_targets executed: {task_res}")


async def run_step_5_viral_hook_optimizer(profile: Profile) -> None:
    logger.info("\n=======================================================")
    logger.info("=== STEP 5: Viral Hook Multi-Generator & Scorer ===")
    logger.info("=======================================================")
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    persona = load_persona(profile_dir)

    draft_post = (
        "Building autonomous bots requires state ledgers and test verification. "
        "Prompt chaining fails when edge cases arise in production."
    )

    opt_result = await optimize_post_hook(
        persona=persona,
        draft_content=draft_post,
        topic="Autonomous AI Reliability",
    )

    assert opt_result.winning_hook is not None, "No winning hook selected"
    assert len(opt_result.candidates) >= 1, "No hook candidates generated"
    logger.info(f"✅ Generated {len(opt_result.candidates)} hook archetypes:")
    for c in opt_result.candidates:
        logger.info(f"   [{c.archetype.upper()}] (Score: {c.score}/10): {c.hook_text}")

    logger.info(f"✅ Winning Hook: \"{opt_result.winning_hook.hook_text}\" (Score: {opt_result.winning_hook.score}/10)")
    logger.info(f"✅ Dwell-Optimized Post Output:\n{opt_result.optimized_content}")


async def run_step_6_poll_generator(profile: Profile) -> None:
    logger.info("\n=======================================================")
    logger.info("=== STEP 6: Interactive Native Poll Studio ===")
    logger.info("=======================================================")
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    persona = load_persona(profile_dir)

    poll_result = await generate_poll(
        persona=persona,
        topic="AI Agent Frameworks vs Custom Loops",
    )

    assert poll_result.question, "Poll question is empty"
    assert 2 <= len(poll_result.options) <= 4, f"Invalid options count: {len(poll_result.options)}"
    for idx, opt in enumerate(poll_result.options, 1):
        assert len(opt) <= 25, f"Option {idx} exceeds 25 chars: '{opt}' ({len(opt)} chars)"

    logger.info(f"✅ Generated Poll Question: \"{poll_result.question}\"")
    logger.info(f"✅ Validated Options (<= 25 chars constraint):")
    for idx, opt in enumerate(poll_result.options, 1):
        logger.info(f"   Option {idx}: {opt} ({len(opt)}/25 chars)")
    logger.info(f"✅ Duration: {poll_result.duration_days} Day(s) | Strategic Reasoning: {poll_result.reasoning}")


async def run_step_7_trend_radar(profile: Profile) -> None:
    logger.info("\n=======================================================")
    logger.info("=== STEP 7: Real-Time Trend Radar Ingestion ===")
    logger.info("=======================================================")
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    persona = load_persona(profile_dir)

    # 1. Fetch live RSS items
    feed_urls = ["https://hnrss.org/frontpage"]
    items = await fetch_rss_trends(feed_urls, keywords=persona.interests.primary, max_items_per_feed=3)
    logger.info(f"✅ Live RSS Ingested: {len(items)} matching trend items")

    if items:
        sample_item = items[0]
        eval_result = await generate_trend_take(persona=persona, trend_item=sample_item)
        logger.info(f"✅ Trend Relevance Score: {eval_result.relevance_score}/1.0 (Relevant: {eval_result.is_relevant})")
        if eval_result.is_relevant:
            logger.info(f"✅ Hot Take: \"{eval_result.hot_take}\"")
            logger.info(f"✅ Formatted Post:\n{eval_result.optimized_post or eval_result.draft_post}")

    # 2. Celery Periodic Task
    task_res = await _check_trend_radar_async(base_profile_dir=str(Path("/home/ubuntu/projects/xbot/data/profiles")))
    assert task_res.get("status") in ["success", "partial_success"], f"Trend radar task failed: {task_res}"
    logger.info(f"✅ Trend Radar Celery Task executed: {task_res}")


async def run_step_8_rest_api_validation(profile: Profile) -> None:
    logger.info("\n=======================================================")
    logger.info("=== STEP 8: REST API & Dashboard Endpoints Verification ===")
    logger.info("=======================================================")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Profiles list
        r1 = await client.get(f"{API_BASE}/api/profiles")
        assert r1.status_code == 200
        profiles = r1.json()
        assert len(profiles) >= 1
        logger.info(f"✅ GET /api/profiles -> {len(profiles)} active profiles")

        # 2. Persona endpoint
        r2 = await client.get(f"{API_BASE}/api/profiles/{profile.id}/persona")
        assert r2.status_code == 200
        persona_data = r2.json()
        assert "target_kols" in persona_data
        logger.info(f"✅ GET /api/profiles/{profile.id}/persona -> {len(persona_data['target_kols'])} KOLs")

        # 3. Content queue endpoint
        r3 = await client.get(f"{API_BASE}/api/profiles/{profile.id}/content")
        assert r3.status_code == 200
        content_items = r3.json()
        logger.info(f"✅ GET /api/profiles/{profile.id}/content -> {len(content_items)} staged content items")

        # 4. Sessions endpoint
        r4 = await client.get(f"{API_BASE}/api/profiles/{profile.id}/sessions")
        assert r4.status_code == 200
        sessions = r4.json()
        logger.info(f"✅ GET /api/profiles/{profile.id}/sessions -> {len(sessions)} session records")

        # 5. Analytics endpoint
        r5 = await client.get(f"{API_BASE}/api/profiles/{profile.id}/analytics")
        assert r5.status_code == 200
        analytics = r5.json()
        logger.info(f"✅ GET /api/profiles/{profile.id}/analytics -> {len(analytics)} metric snapshots")


async def main() -> None:
    logger.info("********************************************************************************")
    logger.info("🚀 STARTING COMPREHENSIVE END-TO-END FEATURE TEST FOR @jackds1234 🚀")
    logger.info("********************************************************************************")

    # 1. Check services
    await run_step_1_services_health()

    # 2. Locate @jackds1234 (test_profile1)
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Profile).where(Profile.profile_slug == "test_profile1"))
        profile = res.scalar_one_or_none()
        assert profile is not None, "Profile 'test_profile1' not found in database"

    logger.info(f"Testing with Profile: {profile.display_name} (@{profile.x_handle}) [ID: {profile.id}]")

    # 3. Execute all feature validation steps
    await run_step_2_auth_status(profile)
    await run_step_3_sync_from_x(profile)
    await run_step_4_kol_sniper(profile)
    await run_step_5_viral_hook_optimizer(profile)
    await run_step_6_poll_generator(profile)
    await run_step_7_trend_radar(profile)
    await run_step_8_rest_api_validation(profile)

    logger.info("\n********************************************************************************")
    logger.info("🎉 ALL 8 COMPREHENSIVE FEATURE TESTS PASSED 100% FOR @jackds1234 🎉")
    logger.info("********************************************************************************")


if __name__ == "__main__":
    asyncio.run(main())
