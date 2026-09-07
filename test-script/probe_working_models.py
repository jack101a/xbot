import asyncio
from openai import AsyncOpenAI

MODELS = [
    "gemini-3.1-flash-lite",
    "mistral-small",
    "gemini-flash-latest",
]

async def check(client, m):
    try:
        res = await client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": "Write 1 sentence about why One Piece is popular."}],
            max_tokens=50,
            timeout=25.0,
        )
        print(f"✅ {m:22} -> WORKING! Output: {res.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"❌ {m:22} -> Failed: {e}")

async def main():
    client = AsyncOpenAI(base_url="https://llm.002529.xyz/v1", api_key="sk-y_2_lD1m4Ojw1QFMDEWgwA")
    for m in MODELS:
        await check(client, m)

if __name__ == "__main__":
    asyncio.run(main())
