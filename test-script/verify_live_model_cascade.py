import asyncio
import logging
from xbot.ai.sniper import generate_sniper_reply
from xbot.persona.loader import load_persona
from pathlib import Path

logging.basicConfig(level=logging.INFO)

async def test():
    persona = load_persona(Path("/home/ubuntu/projects/xbot/data/profiles/test_profile1"))
    
    target_tweet = {
        "text": "The cinematography in this week's One Piece Egghead episode had no business being this cinematic. MAPPA and Ufotable have serious competition.",
        "author": "Sandman_AP",
        "url": "https://x.com/Sandman_AP/status/2091747265044181128",
        "media_urls": ["https://pbs.twimg.com/media/ExampleSakuga.jpg"]
    }

    print("\n--- Testing Live Sniper Reply with Gemini Fallback Cascade ---")
    reply = await generate_sniper_reply(
        persona=persona,
        target_tweet=target_tweet,
    )
    print(f"\nReply Text: \"{reply.reply_text}\"")
    print(f"Angle Used: {reply.angle_used}")
    print(f"Reasoning: {reply.reasoning}")
    print(f"Confidence: {reply.confidence}")

if __name__ == "__main__":
    asyncio.run(test())
