import asyncio
from openai import AsyncOpenAI
from xbot.config import settings

MODELS_TO_TEST = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gpt-oss-120b",
    "deepseek-v4-flash-0731",
    "deepseek-v4-pro",
    "mistral-large",
    "mistral-medium",
    "mistral-small",
    "qwen-3.5",
    "glm-5.2",
    "kimi-k2.6",
    "gemma-4-31b",
    "gemma-4-26b",
]

async def probe():
    client = AsyncOpenAI(base_url=settings.LITELLM_BASE_URL, api_key=settings.LITELLM_API_KEY, timeout=10.0)
    print(f"--- Probing Gateway: {settings.LITELLM_BASE_URL} ---\n")
    
    for m in MODELS_TO_TEST:
        try:
            res = await client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": "Say 'OK' in 1 word."}],
                max_tokens=10,
            )
            content = res.choices[0].message.content.strip()
            print(f"✅ {m:25} -> Working! Response: {content}")
        except Exception as e:
            err_msg = str(e)
            if "410" in err_msg:
                err_msg = "410 Gone (Model EOL on upstream provider)"
            elif "400" in err_msg:
                err_msg = "400 Invalid model name or config"
            elif "429" in err_msg:
                err_msg = "429 Rate Limited"
            elif "503" in err_msg or "502" in err_msg or "500" in err_msg:
                err_msg = "5xx Gateway / Upstream Error"
            print(f"❌ {m:25} -> Failed: {err_msg[:60]}")

if __name__ == "__main__":
    asyncio.run(probe())
