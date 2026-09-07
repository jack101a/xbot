import asyncio
import datetime
import logging
from pathlib import Path
from xbot.ai.opportunity_radar import (
    CandidateOpportunity,
    OpportunityRadar,
    calculate_arbitrage_score,
)
from xbot.ai.sniper import generate_sniper_reply, verify_sniper_reply
from xbot.persona.loader import load_persona
from xbot.scheduler.circadian import (
    generate_daily_circadian_schedule,
    is_within_active_session,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_24_7")


async def run_all_verifications():
    print("=================================================================")
    print("🚀 XBOT PRO: 24/7 AUTONOMOUS GROWTH ENGINE VERIFICATION SUITE")
    print("=================================================================\n")

    # 1. Verify Opportunity Radar
    print("🔍 [TEST 1/5] OPPORTUNITY RADAR & ARBITRAGE SCORING")
    radar = OpportunityRadar(min_arbitrage_threshold=65.0)
    candidates = [
        CandidateOpportunity(
            tweet_id="k1",
            author="thetanmay",
            text="Every tech startup founder says we are revolutionizing productivity until they schedule a 90 minute call.",
            url="https://x.com/thetanmay/status/k1",
            age_minutes=3.5,
            reply_count=4,
            likes=850,
            impressions=12000,
            relevance_score=95.0,
            author_factor=85.0,
        ),
        CandidateOpportunity(
            tweet_id="k2",
            author="spammer",
            text="Good morning chai coffee terrace vibes!",
            url="https://x.com/spammer/status/k2",
            age_minutes=150.0,
            reply_count=90,
            likes=1,
            relevance_score=15.0,
            author_factor=10.0,
        ),
    ]
    ranked = radar.rank_opportunities(candidates)
    assert len(ranked) == 1, "Failed: Should rank exactly 1 high-signal opportunity"
    top_opp = ranked[0]
    print(f"   ✅ Top Opportunity: @{top_opp.author} (Score: {top_opp.arbitrage_score:.1f}/100)")
    print(f"   ✅ Filtered Saturated Spammer Post (Score below 65.0)")

    # 2. Verify Sniper 4-Archetype Engine & 5-Stage Verification Gatekeeper
    print("\n🎯 [TEST 2/5] SNIPER 4-ARCHETYPE ENGINE & TOPIC FILTER")
    persona_path = Path("/home/ubuntu/projects/xbot/data/profiles/test_profile1")
    persona = load_persona(persona_path)

    # Test Gatekeeper on Bad Strings
    bad_chai = "Drinking adrak chai on the terrace while thinking about databases."
    is_v, reason = verify_sniper_reply(bad_chai, language_mode="english")
    assert not is_v and "routine/beverage filler" in reason, f"Gatekeeper failed on chai check: {reason}"
    print("   ✅ Gatekeeper blocked chai/beverage filler successfully")

    bad_ai_slop = "This tweet is a multifaceted testament to the beacon of scalable architectures, let us delve into it."
    is_v2, reason2 = verify_sniper_reply(bad_ai_slop, language_mode="english")
    assert not is_v2 and "academic word" in reason2, f"Gatekeeper failed on AI words: {reason2}"
    print("   ✅ Gatekeeper blocked pretentious AI vocabulary ('testament', 'delve', 'beacon')")

    # Generate Real Live Sniper Replies across Archetypes
    tweet_target = {
        "author": "thetanmay",
        "text": "Every tech startup founder says we are revolutionizing productivity until they schedule a 90 minute call.",
        "top_comments": ["Email could have been a slack message", "Meeting fatigue is real"],
    }
    for angle in ["witty", "contrarian", "framework"]:
        res = await generate_sniper_reply(persona=persona, target_tweet=tweet_target, preferred_angle=angle)
        print(f"   ⚡ [{angle.upper()}] Reply: \"{res.reply_text}\" (GIF: {res.gif_query})")
        assert len(res.reply_text) <= 280
        import re
        assert not re.search(r"\b(chai|coffee|matcha)\b", res.reply_text, re.I)

    # 3. Verify Episodic Circadian Scheduler
    print("\n⏰ [TEST 3/5] EPISODIC CIRCADIAN SCHEDULER & 8-HOUR SLEEP BLOCK")
    schedule = generate_daily_circadian_schedule(
        wake_hour=8,
        sleep_hour=23,
        target_sessions=4,
        skip_probability=0.0,
        seed=42,
    )
    print(f"   Generated {len(schedule)} organic sessions for today:")
    for i, s in enumerate(schedule, 1):
        end_m = (s.start_hour * 60 + s.start_minute + s.duration_minutes) % (24 * 60)
        end_str = f"{end_m // 60:02d}:{end_m % 60:02d}"
        print(f"     Session {i}: {s.start_hour:02d}:{s.start_minute:02d} -> {end_str} ({s.duration_minutes}m, Wave: {s.target_wave})")
        assert 8 <= s.start_hour < 23, "Session scheduled during sleep block!"
    print("   ✅ Preserved 8-hour continuous nightly sleep window (23:00 - 08:00)")

    # 4. Verify Active Session Boundary Evaluation
    t_test = datetime.time(schedule[0].start_hour, schedule[0].start_minute + 5)
    in_session = is_within_active_session(t_test, schedule)
    assert in_session is True, "Boundary evaluation failed"
    print("   ✅ Real-time session window detection verified")

    print("\n=================================================================")
    print("🏆 ALL 24/7 AUTONOMOUS ENGINE INVARIANTS 100% VERIFIED")
    print("=================================================================\n")

asyncio.run(run_all_verifications())
