import asyncio
from openai import AsyncOpenAI

MODELS = [
    "gemini-flash-latest",
    "gemini-flash-latest-lite",
    "gemini-3.1-flash-lite",
    "gpt-oss-120b",
    "mistral-large",
    "mistral-medium",
    "mistral-small",
    "kimi-k2.6",
    "qwen-3.5",
    "glm-5.2",
    "deepseek-v4-flash-0731",
    "gemma-4-31b",
]

async def check_model(client, m):
    try:
        res = await client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": "Say 'OK'."}],
            max_tokens=10,
        )
        ans = res.choices[0].message.content.strip()
        print(f"✅ {m:26} -> ALIVE & WORKING! Response: '{ans}'")
        return (m, True)
    except Exception as e:
        print(f"❌ {m:26} -> Error: {str(e)[:70]}")
        return (m, False)

async def main():
    client = AsyncOpenAI(base_url="https://llm.002529.xyz/v1", api_key="sk-y_2_lD1m4Ojw1QFMDEWgwA", timeout=12.0)
    print("--- Probing Exact Gateway Model IDs in Parallel ---\n")
    tasks = [check_model(client, m) for m in MODELS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
