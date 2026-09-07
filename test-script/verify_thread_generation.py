import asyncio
import logging
from xbot.ai.thread_generator import generate_thread
from xbot.persona.loader import load_persona
from pathlib import Path

logging.basicConfig(level=logging.INFO)

async def test():
    persona = load_persona(Path("/home/ubuntu/projects/xbot/data/profiles/test_profile1"))
    topic = "The Brutal Reality of AI Coding Agents in 2026: What actually works vs what is pure marketing hype"
    res = await generate_thread(topic=topic, persona=persona, num_tweets=4)
    print("\n--- Generated Creator Thread ---")
    print(f"Topic: {res.topic}")
    print(f"Hook Score: {res.hook_score}")
    print(f"Archetype: {res.archetype}")
    for idx, t in enumerate(res.tweets):
        print(f"\n[Tweet {idx+1}] ({len(t)} chars):\n{t}")

if __name__ == "__main__":
    asyncio.run(test())
