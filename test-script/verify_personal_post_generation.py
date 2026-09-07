import asyncio
import json
import logging

from xbot.ai.planner import plan_session
from xbot.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)

async def test_planning():
    sample_feed = [
        {
            "author": "pewpiece",
            "text": "One Piece Chapter 1140 Spoilers: The giant warriors reveal the true name of the ancient kingdom, but the final double page is cut short before the reaction.",
            "likes": 14200,
            "retweets": 3100,
            "replies": 840,
            "url": "https://x.com/pewpiece/status/2091565038729417047"
        },
        {
            "author": "MKBHD",
            "text": "The new iPhone 17 Pro camera vs Galaxy S26 Ultra blind test results are in. 85% of people chose the phone with more saturated skin tones over color accuracy.",
            "likes": 9800,
            "retweets": 1200,
            "replies": 650,
            "url": "https://x.com/MKBHD/status/2091600000000000000"
        },
        {
            "author": "sama",
            "text": "The next frontier of AI isn't raw parameter size; it's reasoning chains and multi-agent coordination working across complex environments.",
            "likes": 22000,
            "retweets": 4100,
            "replies": 1200,
            "url": "https://x.com/sama/status/2091700000000000000"
        }
    ]

    async with AsyncSessionLocal() as db:
        print("\n--- Planning Session with New Personal Creator Prompts ---")
        plan = await plan_session(
            db=db,
            profile_slug="test_profile1",
            feed_snapshot=sample_feed,
        )
        print(f"\nMood: {plan.mood}")
        print(f"Reasoning: {plan.reasoning}")
        print("\nPlanned Actions:")
        for idx, act in enumerate(plan.actions):
            print(f"\n[{idx+1}] Type: {act.type} | Priority: {act.priority}")
            print(f"    Target: {act.target}")
            print(f"    Content: {act.content}")
            if act.thread_items:
                print("    Thread Items:")
                for tidx, ttext in enumerate(act.thread_items):
                    print(f"      ({tidx+1}) {ttext}")
            print(f"    Reasoning: {act.reasoning}")

if __name__ == "__main__":
    asyncio.run(test_planning())
