import asyncio
from openai import AsyncOpenAI

MODELS = [
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gpt-oss-120b",
    "mistral-small",
    "deepseek-v4-flash-0731",
]

async def main():
    client = AsyncOpenAI(base_url="https://llm.002529.xyz/v1", api_key="sk-y_2_lD1m4Ojw1QFMDEWgwA", timeout=15.0)
    for m in MODELS:
        try:
            res = await client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": "Say 'OK' and explain in 5 words."}],
                max_tokens=20,
            )
            print(f"✅ {m:26} -> ALIVE! Response: {res.choices[0].message.content}")
        except Exception as e:
            print(f"❌ {m:26} -> Failed: {str(e)[:80]}")

if __name__ == "__main__":
    asyncio.run(main())
