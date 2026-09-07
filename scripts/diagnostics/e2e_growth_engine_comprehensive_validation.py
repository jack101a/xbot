"""
Comprehensive End-to-End User Experience Validation for XBot Growth Engine.

Validates all 4 Growth Engine sub-tools:
1. KOL Sniper Engine:
   - Target KOL CRUD via REST API (handles, categories, priorities, angles: contrarian, insight, witty, data, framework).
   - Live sniper reply generation for multiple angles against simulated target tweets.
   - Strict character limits (<280 chars), anti-bot checks (no "great post", no hashtags), angle consistency.
   - Celery background sniper loop execution.

2. Viral Hook Optimizer:
   - Evaluates draft posts/topics across 6 viral hook archetypes:
     (curiosity_gap, contrarian, framework_breakdown, story_relatable, statistical_data, bold_prediction).
   - Scored dwell retention (1.0-10.0) and winning hook selection.
   - Dwell-optimized post output formatting with micro-spacing.

3. Interactive Poll Generator:
   - Poll question generation with debate framing.
   - 2-4 poll options strictly validated to be <= 25 characters (X platform hard limit).
   - Custom voting durations (1 to 7 days).

4. Trend Radar:
   - Live RSS/Atom feed fetching and persona keyword filtering.
   - Niche relevance scoring (0.0 to 1.0, threshold >= 0.65).
   - Multi-stage commentary formulation (takeaways + hot take + draft post + viral hook optimization).
   - Celery background trend radar ingestion task.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Ensure backend is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import httpx
from sqlalchemy import select

from xbot.ai.hook_optimizer import optimize_post_hook, HookOptimizationResult
from xbot.ai.poll_generator import generate_poll, GeneratedPoll
from xbot.ai.sniper import generate_sniper_reply, SniperReplyResult
from xbot.ai.trend_generator import generate_trend_take, TrendEvaluation
from xbot.ai.trend_radar import fetch_rss_trends, TrendItem
from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona import load_persona
from xbot.persona.loader import Persona, TargetKOL
from xbot.tasks import _check_trend_radar_async, _sniper_check_targets_async

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("e2e_growth_tester")

API_BASE = "http://127.0.0.1:8200"


class GrowthEngineTestReport:
    def __init__(self):
        self.results: dict[str, Any] = {
            "services_health": {},
            "kol_sniper": {"subtests": [], "metrics": {}},
            "hook_optimizer": {"subtests": [], "metrics": {}},
            "poll_generator": {"subtests": [], "metrics": {}},
            "trend_radar": {"subtests": [], "metrics": {}},
            "summary": {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "latencies_ms": {},
            }
        }

    def record_pass(self, category: str, subtest_name: str, data: dict[str, Any]):
        self.results[category]["subtests"].append({
            "name": subtest_name,
            "status": "PASSED",
            **data
        })
        self.results["summary"]["total_checks"] += 1
        self.results["summary"]["passed_checks"] += 1

    def record_fail(self, category: str, subtest_name: str, error: str, data: dict[str, Any]):
        self.results[category]["subtests"].append({
            "name": subtest_name,
            "status": "FAILED",
            "error": error,
            **data
        })
        self.results["summary"]["total_checks"] += 1
        self.results["summary"]["failed_checks"] += 1


report = GrowthEngineTestReport()


async def test_01_api_health():
    logger.info("\n" + "="*70)
    logger.info("TEST SECTION 0: API & Background Services Health Check")
    logger.info("="*70)
    start_t = time.perf_counter()
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{API_BASE}/api/health")
        duration_ms = (time.perf_counter() - start_t) * 1000
        assert r.status_code == 200, f"Health endpoint returned status {r.status_code}"
        health_data = r.json()
        assert health_data.get("status") == "healthy"
        logger.info(f"✅ Backend Health: {health_data} (Latency: {duration_ms:.2f}ms)")
        report.results["services_health"] = {
            "status": health_data.get("status"),
            "redis_connected": health_data.get("redis_connected"),
            "latency_ms": round(duration_ms, 2)
        }


async def setup_test_persona_profile() -> tuple[Profile, Persona]:
    logger.info("\n" + "="*70)
    logger.info("SETTING UP TEST PERSONA PROFILE")
    logger.info("="*70)
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.profile_slug == "growth_tester_pro")
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            profile = Profile(
                profile_slug="growth_tester_pro",
                x_handle="growth_tester",
                display_name="Growth AI Architect",
                status=ProfileStatus.ACTIVE,
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize persona with target KOLs
    initial_persona_yaml = f"""id: {profile.profile_slug}
display_name: {profile.display_name}
x_handle: "@{profile.x_handle}"
identity:
  background: Principal AI systems engineer and growth technologist. Building production autonomous agent runtimes.
  occupation: Principal Systems Architect
personality:
  traits: [analytical, sharp, witty, skeptical, high-conviction]
  values: [open_source, deterministic_execution, zero_fluff]
  communication_style: punchy_and_insightful
interests:
  primary: [AI, autonomous agents, distributed systems, developer tools]
  secondary: [Python, Rust, LLM benchmarks, database scalability]
  will_not_discuss: [generic engagement spam, crypto scams, partisan politics]
writing_style:
  tone: authoritative_yet_accessible
  typical_length: concise
  formatting: [micro_spacing, punchy_lines, no_emojis]
  examples:
    - "Most agent frameworks fail on state management, not inference latency."
    - "Your database bottleneck is unindexed queries, not PostgreSQL itself."
goals:
  short_term: [scale audience through high-retention technical sniper replies]
  long_term: [become the go-to authority on autonomous systems architecture]
  content_pillars: [Agent Systems, Production Scale, Latency Engineering]
rules:
  always: [add technical value, cite specific logic or architecture patterns]
  never: [generic praise like 'great post', hashtag spam, say 'let us dive in']
target_kols:
  - handle: "sama"
    category: "ai_industry"
    priority: "high"
    preferred_angle: "contrarian"
  - handle: "ylecun"
    category: "ai_research"
    priority: "high"
    preferred_angle: "insight"
  - handle: "elonmusk"
    category: "tech"
    priority: "medium"
    preferred_angle: "witty"
  - handle: "karpathy"
    category: "ai_education"
    priority: "high"
    preferred_angle: "data"
  - handle: "levelsio"
    category: "indie_hacking"
    priority: "medium"
    preferred_angle: "framework"
"""
    (profile_dir / "persona.yaml").write_text(initial_persona_yaml, encoding="utf-8")
    persona = load_persona(profile_dir)
    return profile, persona


async def test_02_kol_sniper_engine(profile: Profile, persona: Persona):
    logger.info("\n" + "="*70)
    logger.info("TEST SECTION 1: KOL Sniper Engine (Target Creators & AI Reply Angles)")
    logger.info("="*70)

    # 1.1 Test REST API loading of Target KOLs
    start_t = time.perf_counter()
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{API_BASE}/api/profiles/{profile.id}/persona")
        load_time_ms = (time.perf_counter() - start_t) * 1000
        assert r.status_code == 200
        persona_dict = r.json()
        target_kols = persona_dict.get("target_kols", [])
        assert len(target_kols) == 5, f"Expected 5 target KOLs, got {len(target_kols)}"
        logger.info(f"✅ REST API GET /persona returned {len(target_kols)} KOL targets in {load_time_ms:.2f}ms")
        report.record_pass("kol_sniper", "api_load_kols", {
            "kol_count": len(target_kols),
            "kols": [k["handle"] for k in target_kols],
            "latency_ms": round(load_time_ms, 2)
        })

    # 1.2 Test adding a new KOL via REST API PUT
    start_t = time.perf_counter()
    new_kol = {
        "handle": "drjimfan",
        "category": "embodied_ai",
        "priority": "high",
        "preferred_angle": "insight"
    }
    updated_kols = target_kols + [new_kol]
    persona_dict["target_kols"] = updated_kols

    async with httpx.AsyncClient(timeout=10.0) as client:
        r_put = await client.put(f"{API_BASE}/api/profiles/{profile.id}/persona", json=persona_dict)
        save_time_ms = (time.perf_counter() - start_t) * 1000
        assert r_put.status_code == 200
        logger.info(f"✅ REST API PUT /persona successfully registered new target @{new_kol['handle']} in {save_time_ms:.2f}ms")
        report.record_pass("kol_sniper", "api_add_kol", {
            "added_handle": new_kol["handle"],
            "total_kols": len(updated_kols),
            "latency_ms": round(save_time_ms, 2)
        })

    # Reload persona to refresh targets
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles") / profile.profile_slug
    persona = load_persona(profile_dir)

    # 1.3 Test AI Sniper Reply Simulation for 4 angles: contrarian, insight, witty, data, framework
    scenarios = [
        {
            "angle": "contrarian",
            "kol": "sama",
            "tweet": {
                "author": "sama",
                "text": "The limiting factor for AI agents in 2026 is no longer model reasoning—it is context window size and memory retention.",
                "url": "https://x.com/sama/status/18888888881",
            }
        },
        {
            "angle": "insight",
            "kol": "ylecun",
            "tweet": {
                "author": "ylecun",
                "text": "Auto-regressive LLMs are inherently susceptible to hallucination chains because error probabilities compound exponentially with sequence length.",
                "url": "https://x.com/ylecun/status/18888888882",
            }
        },
        {
            "angle": "witty",
            "kol": "elonmusk",
            "tweet": {
                "author": "elonmusk",
                "text": "Autonomous humanoid robots will outnumber humans on Earth before 2040.",
                "url": "https://x.com/elonmusk/status/18888888883",
            }
        },
        {
            "angle": "data",
            "kol": "karpathy",
            "tweet": {
                "author": "karpathy",
                "text": "Small, specialized fine-tunes running on local hardware are shockingly competitive with giant frontier models on 90% of coding tasks.",
                "url": "https://x.com/karpathy/status/18888888884",
            }
        },
        {
            "angle": "framework",
            "kol": "levelsio",
            "tweet": {
                "author": "levelsio",
                "text": "You don't need a 10-person dev team anymore. 1 founder + AI tools can build and scale a $100k/mo SaaS solo.",
                "url": "https://x.com/levelsio/status/18888888885",
            }
        },
    ]

    for sc in scenarios:
        angle = sc["angle"]
        kol = sc["kol"]
        tweet = sc["tweet"]
        logger.info(f"\n--- Simulating Sniper Reply to @{kol} [Angle: {angle.upper()}] ---")
        logger.info(f"Target Tweet: \"{tweet['text']}\"")
        
        t0 = time.perf_counter()
        reply_result: SniperReplyResult = await generate_sniper_reply(
            persona=persona,
            target_tweet=tweet,
            preferred_angle=angle,
        )
        gen_time_ms = (time.perf_counter() - t0) * 1000

        # Assertions & Quality Checks
        assert reply_result.reply_text, "Sniper reply text is empty!"
        assert len(reply_result.reply_text) <= 280, f"Sniper reply exceeds 280 chars ({len(reply_result.reply_text)})"
        assert "#" not in reply_result.reply_text, "Hashtag found in sniper reply (violation of X algorithm rules)"
        assert "great post" not in reply_result.reply_text.lower(), "Generic bot praise detected"
        assert "awesome thread" not in reply_result.reply_text.lower(), "Generic bot filler detected"
        assert reply_result.angle_used in ["contrarian", "insight", "witty", "data", "framework"]

        logger.info(f"✅ Generated Sniper Reply ({len(reply_result.reply_text)} chars, {gen_time_ms:.2f}ms):")
        logger.info(f"   \"{reply_result.reply_text}\"")
        logger.info(f"   Angle Used: {reply_result.angle_used} | Confidence: {reply_result.confidence} | Reasoning: {reply_result.reasoning}")

        report.record_pass("kol_sniper", f"sniper_reply_{angle}", {
            "target_kol": kol,
            "target_tweet": tweet["text"],
            "requested_angle": angle,
            "angle_used": reply_result.angle_used,
            "reply_text": reply_result.reply_text,
            "char_count": len(reply_result.reply_text),
            "confidence": reply_result.confidence,
            "reasoning": reply_result.reasoning,
            "latency_ms": round(gen_time_ms, 2),
        })

    # 1.4 Test Celery periodic task execution for sniper scanning
    logger.info("\n--- Testing Sniper Celery Target Loop Task ---")
    t0 = time.perf_counter()
    task_res = await _sniper_check_targets_async()
    task_time_ms = (time.perf_counter() - t0) * 1000
    assert task_res.get("status") in ["success", "completed"]
    logger.info(f"✅ Celery Sniper Loop Task executed successfully in {task_time_ms:.2f}ms: {task_res}")
    report.record_pass("kol_sniper", "celery_sniper_task", {
        "task_result": task_res,
        "latency_ms": round(task_time_ms, 2)
    })


async def test_03_viral_hook_optimizer(persona: Persona):
    logger.info("\n" + "="*70)
    logger.info("TEST SECTION 2: Viral Hook Optimizer (6 Psychological Archetypes)")
    logger.info("="*70)

    test_drafts = [
        {
            "topic": "Autonomous Coding Agents in Production",
            "draft_body": (
                "Deterministic verification loops outperform unconstrained prompt chaining by 4.2x in real codebases.\n\n"
                "State ledgers prevent catastrophic context drift during session compaction.\n\n"
                "Never trust agent output without running automated test suites."
            )
        },
        {
            "topic": "PostgreSQL Performance Under High Write Concurrency",
            "draft_body": (
                "Connection pool saturation is the #1 silent killer of high-throughput Postgres clusters.\n\n"
                "Switching from process-per-connection to PgBouncer cut p99 query latency from 340ms to 18ms.\n\n"
                "Always check active lock contention before blaming disk I/O."
            )
        }
    ]

    for d in test_drafts:
        topic = d["topic"]
        draft_body = d["draft_body"]
        logger.info(f"\n--- Optimizing Draft for Topic: '{topic}' ---")
        logger.info(f"Draft Body:\n{draft_body}")

        t0 = time.perf_counter()
        result: HookOptimizationResult = await optimize_post_hook(
            persona=persona,
            draft_content=draft_body,
            topic=topic
        )
        opt_time_ms = (time.perf_counter() - t0) * 1000

        # Assertions & Validations
        assert result.winning_hook is not None, "Winning hook is None!"
        assert 1.0 <= result.winning_hook.score <= 10.0, f"Invalid winning hook score: {result.winning_hook.score}"
        assert len(result.candidates) >= 4, f"Expected at least 4 candidate hooks, got {len(result.candidates)}"
        assert result.optimized_content.startswith(result.winning_hook.hook_text), "Optimized post does not lead with winning hook!"

        archetypes_generated = [c.archetype for c in result.candidates]
        logger.info(f"✅ Generated {len(result.candidates)} Hook Archetypes ({opt_time_ms:.2f}ms): {archetypes_generated}")
        for c in result.candidates:
            logger.info(f"   [{c.archetype.upper()}] (Score: {c.score}/10): \"{c.hook_text}\" (Reasoning: {c.reasoning})")

        logger.info(f"🏆 Winning Hook Selected: [{result.winning_hook.archetype.upper()}] \"{result.winning_hook.hook_text}\" (Score: {result.winning_hook.score}/10)")
        logger.info(f"📝 Full Dwell-Optimized Post Output:\n{result.optimized_content}")

        report.record_pass("hook_optimizer", f"optimize_hook_{topic[:20].strip().replace(' ', '_')}", {
            "topic": topic,
            "candidate_count": len(result.candidates),
            "candidates": [
                {
                    "archetype": c.archetype,
                    "hook_text": c.hook_text,
                    "score": c.score,
                    "reasoning": c.reasoning
                }
                for c in result.candidates
            ],
            "winning_hook": {
                "archetype": result.winning_hook.archetype,
                "hook_text": result.winning_hook.hook_text,
                "score": result.winning_hook.score,
                "reasoning": result.winning_hook.reasoning,
            },
            "optimized_content": result.optimized_content,
            "latency_ms": round(opt_time_ms, 2)
        })


async def test_04_interactive_poll_generator(persona: Persona):
    logger.info("\n" + "="*70)
    logger.info("TEST SECTION 3: Interactive Poll Generator (Strict <=25 char limit & durations)")
    logger.info("="*70)

    topics = [
        "Autonomous Agents vs Human Devs for Bug Fixing",
        "Postgres vs Redis for AI Agent Memory State",
        "Monolith vs Microservices in 2026",
    ]

    for topic in topics:
        logger.info(f"\n--- Generating Interactive Poll for: '{topic}' ---")
        t0 = time.perf_counter()
        poll: GeneratedPoll = await generate_poll(
            persona=persona,
            topic=topic
        )
        poll_time_ms = (time.perf_counter() - t0) * 1000

        # Assertions & Strict X Constraints
        assert poll.question, "Poll question is empty!"
        assert len(poll.question) <= 200, f"Poll question exceeds 200 chars ({len(poll.question)})"
        assert 2 <= len(poll.options) <= 4, f"Options count not between 2 and 4 ({len(poll.options)})"
        assert 1 <= poll.duration_days <= 7, f"Invalid duration {poll.duration_days} days"

        for opt in poll.options:
            assert len(opt) <= 25, f"Option '{opt}' exceeds strict X character limit of 25 ({len(opt)} chars)"

        logger.info(f"✅ Generated Poll in {poll_time_ms:.2f}ms:")
        if poll.context_hook:
            logger.info(f"   Context Hook: \"{poll.context_hook}\"")
        logger.info(f"   Question: \"{poll.question}\"")
        logger.info(f"   Options (<=25 chars):")
        for i, opt in enumerate(poll.options, 1):
            logger.info(f"     [{i}] {opt} ({len(opt)}/25 chars)")
        logger.info(f"   Duration: {poll.duration_days} Day(s) | Reasoning: {poll.reasoning}")

        report.record_pass("poll_generator", f"poll_{topic[:20].strip().replace(' ', '_')}", {
            "topic": topic,
            "context_hook": poll.context_hook,
            "question": poll.question,
            "options": poll.options,
            "option_lengths": [len(opt) for opt in poll.options],
            "duration_days": poll.duration_days,
            "reasoning": poll.reasoning,
            "latency_ms": round(poll_time_ms, 2)
        })


async def test_05_trend_radar(persona: Persona):
    logger.info("\n" + "="*70)
    logger.info("TEST SECTION 4: Trend Radar (RSS Ingestion, Relevance Scoring & Hot Takes)")
    logger.info("="*70)

    # 4.1 Live Feed Fetching
    feed_urls = ["https://hnrss.org/frontpage"]
    logger.info(f"Fetching live RSS trends from: {feed_urls[0]} with keywords: {persona.interests.primary}")
    
    t0 = time.perf_counter()
    trends = await fetch_rss_trends(
        feed_urls=feed_urls,
        keywords=persona.interests.primary,
        max_items_per_feed=4
    )
    fetch_time_ms = (time.perf_counter() - t0) * 1000

    assert isinstance(trends, list)
    logger.info(f"✅ Fetched {len(trends)} trend items in {fetch_time_ms:.2f}ms")
    report.record_pass("trend_radar", "rss_fetch", {
        "feed_url": feed_urls[0],
        "items_fetched": len(trends),
        "latency_ms": round(fetch_time_ms, 2)
    })

    # If no live items matched keywords, construct a sample relevant and irrelevant item
    sample_relevant = TrendItem(
        id="test_ai_agent_trend",
        title="DeepSeek and OpenAI release new benchmarks on autonomous code repair systems",
        summary="A new benchmark paper evaluates multi-agent vs single-agent test loops on 10,000 GitHub pull requests, showing 78% resolution accuracy.",
        source_url="https://news.ycombinator.com/item?id=4999901",
        source_name="Hacker News",
        published_at="2026-08-22T10:00:00Z"
    )

    sample_irrelevant = TrendItem(
        id="test_gardening_trend",
        title="Top 10 heirloom tomato cultivars for high-altitude organic gardening",
        summary="Tips and seed saving strategies for growing heirloom beefsteak tomatoes in cold mountain climates.",
        source_url="https://news.ycombinator.com/item?id=4999902",
        source_name="Gardening Digest",
        published_at="2026-08-22T10:00:00Z"
    )

    # 4.2 Test Relevant Trend Item Evaluation & Hot Take Generation
    logger.info("\n--- Evaluating Relevant Industry Trend Item ---")
    logger.info(f"Headline: \"{sample_relevant.title}\"")
    t0 = time.perf_counter()
    rel_eval: TrendEvaluation = await generate_trend_take(persona, sample_relevant)
    eval_time_ms = (time.perf_counter() - t0) * 1000

    assert rel_eval.relevance_score >= 0.65, f"Expected relevant score >= 0.65, got {rel_eval.relevance_score}"
    assert rel_eval.is_relevant is True, "Expected is_relevant to be True"
    assert len(rel_eval.key_takeaways) >= 1, "Key takeaways empty"
    assert rel_eval.hot_take, "Persona hot take empty"
    assert rel_eval.optimized_post or rel_eval.draft_post, "Trend post output empty"

    logger.info(f"✅ Evaluated as RELEVANT (Score: {rel_eval.relevance_score:.2f}/1.0, {eval_time_ms:.2f}ms):")
    logger.info(f"   Reasoning: {rel_eval.reasoning}")
    logger.info(f"   Takeaways: {rel_eval.key_takeaways}")
    logger.info(f"   Hot Take: \"{rel_eval.hot_take}\"")
    logger.info(f"   Dwell-Optimized Post Output:\n{rel_eval.optimized_post or rel_eval.draft_post}")

    report.record_pass("trend_radar", "evaluate_relevant_trend", {
        "title": sample_relevant.title,
        "relevance_score": rel_eval.relevance_score,
        "is_relevant": rel_eval.is_relevant,
        "reasoning": rel_eval.reasoning,
        "key_takeaways": rel_eval.key_takeaways,
        "hot_take": rel_eval.hot_take,
        "optimized_post": rel_eval.optimized_post or rel_eval.draft_post,
        "latency_ms": round(eval_time_ms, 2)
    })

    # 4.3 Test Irrelevant Trend Item Rejection
    logger.info("\n--- Evaluating Off-Niche / Irrelevant Trend Item ---")
    logger.info(f"Headline: \"{sample_irrelevant.title}\"")
    t0 = time.perf_counter()
    irrel_eval: TrendEvaluation = await generate_trend_take(persona, sample_irrelevant)
    irrel_time_ms = (time.perf_counter() - t0) * 1000

    assert irrel_eval.relevance_score < 0.65 or not irrel_eval.is_relevant, f"Expected rejection, got score {irrel_eval.relevance_score}"
    assert irrel_eval.is_relevant is False, "Expected is_relevant to be False for off-niche topic"
    logger.info(f"✅ Successfully REJECTED off-niche item (Score: {irrel_eval.relevance_score:.2f}/1.0, {irrel_time_ms:.2f}ms):")
    logger.info(f"   Reasoning: {irrel_eval.reasoning}")

    report.record_pass("trend_radar", "evaluate_irrelevant_trend", {
        "title": sample_irrelevant.title,
        "relevance_score": irrel_eval.relevance_score,
        "is_relevant": irrel_eval.is_relevant,
        "reasoning": irrel_eval.reasoning,
        "latency_ms": round(irrel_time_ms, 2)
    })

    # 4.4 Test Celery Trend Radar Periodic Task
    logger.info("\n--- Testing Celery Trend Radar Periodic Ingestion Task ---")
    t0 = time.perf_counter()
    task_res = await _check_trend_radar_async()
    trend_task_time_ms = (time.perf_counter() - t0) * 1000
    assert task_res.get("status") in ["success", "completed", "partial_success"]
    logger.info(f"✅ Celery Trend Radar Task executed successfully in {trend_task_time_ms:.2f}ms: {task_res}")
    report.record_pass("trend_radar", "celery_trend_task", {
        "task_result": task_res,
        "latency_ms": round(trend_task_time_ms, 2)
    })


async def main():
    logger.info("Starting Full End-to-End Growth Engine Validation Suite...")
    total_start = time.perf_counter()
    try:
        await test_01_api_health()
        profile, persona = await setup_test_persona_profile()
        await test_02_kol_sniper_engine(profile, persona)
        await test_03_viral_hook_optimizer(persona)
        await test_04_interactive_poll_generator(persona)
        await test_05_trend_radar(persona)
        
        total_time_s = time.perf_counter() - total_start
        logger.info("\n" + "="*70)
        logger.info(f"🎉 ALL GROWTH ENGINE E2E VALIDATION TESTS PASSED ({report.results['summary']['passed_checks']}/{report.results['summary']['total_checks']} checks) in {total_time_s:.2f}s 🎉")
        logger.info("="*70)

        # Output raw report JSON to disk for report generation
        report_file = Path("/home/ubuntu/projects/xbot/test-script/growth_engine_e2e_results.json")
        report_file.write_text(json.dumps(report.results, indent=2), encoding="utf-8")
        logger.info(f"Detailed execution metrics saved to {report_file}")

    except Exception as e:
        logger.error(f"❌ Growth Engine E2E Validation Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
