from __future__ import annotations
import logging
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel
from xbot.config import settings

router = APIRouter(tags=["System"])
logger = logging.getLogger(__name__)

class SystemConfigUpdate(BaseModel):
    LITELLM_BASE_URL: str | None = None
    LITELLM_API_KEY: str | None = None
    LITELLM_PRIMARY_MODEL: str | None = None
    LITELLM_FAST_MODEL: str | None = None
    MODEL_POST_CREATION: str | None = None
    MODEL_REPLY_ANALYSIS: str | None = None
    MODEL_HOOK_OPTIMIZER: str | None = None
    MODEL_POLL_GENERATOR: str | None = None
    MODEL_TREND_ANALYSIS: str | None = None
    MODEL_LIKE_RETWEET: str | None = None
    MODEL_FOLLOW: str | None = None
    MODEL_REFLECTION: str | None = None
    MODEL_PLANNER: str | None = None
    PROMPT_POST_CREATION: str | None = None
    PROMPT_REPLY_ANALYSIS: str | None = None
    PROMPT_TREND_ANALYSIS: str | None = None
    PROMPT_LIKE_RETWEET: str | None = None
    PROMPT_FOLLOW: str | None = None
    CONTEXT_POST_CREATION: str | None = None
    CONTEXT_REPLY_ANALYSIS: str | None = None
    CONTEXT_TREND_ANALYSIS: str | None = None
    CONTEXT_LIKE_RETWEET: str | None = None
    CONTEXT_FOLLOW: str | None = None
    MISTRAL_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None

@router.put("/system/config", response_model=dict[str, Any])
async def update_system_config(payload: SystemConfigUpdate) -> dict[str, Any]:
    """Updates primary backend settings configuration details dynamically and persists them in .env."""
    from pathlib import Path
    
    # Update settings object in-memory
    if payload.LITELLM_BASE_URL is not None:
        settings.LITELLM_BASE_URL = payload.LITELLM_BASE_URL
    if payload.LITELLM_API_KEY is not None:
        settings.LITELLM_API_KEY = payload.LITELLM_API_KEY
    if payload.LITELLM_PRIMARY_MODEL is not None:
        settings.LITELLM_PRIMARY_MODEL = payload.LITELLM_PRIMARY_MODEL
    if payload.LITELLM_FAST_MODEL is not None:
        settings.LITELLM_FAST_MODEL = payload.LITELLM_FAST_MODEL
    if payload.MODEL_POST_CREATION is not None:
        settings.MODEL_POST_CREATION = payload.MODEL_POST_CREATION
    if payload.MODEL_REPLY_ANALYSIS is not None:
        settings.MODEL_REPLY_ANALYSIS = payload.MODEL_REPLY_ANALYSIS
    if payload.MODEL_HOOK_OPTIMIZER is not None:
        settings.MODEL_HOOK_OPTIMIZER = payload.MODEL_HOOK_OPTIMIZER
    if payload.MODEL_POLL_GENERATOR is not None:
        settings.MODEL_POLL_GENERATOR = payload.MODEL_POLL_GENERATOR
    if payload.MODEL_TREND_ANALYSIS is not None:
        settings.MODEL_TREND_ANALYSIS = payload.MODEL_TREND_ANALYSIS
    if payload.MODEL_LIKE_RETWEET is not None:
        settings.MODEL_LIKE_RETWEET = payload.MODEL_LIKE_RETWEET
    if payload.MODEL_FOLLOW is not None:
        settings.MODEL_FOLLOW = payload.MODEL_FOLLOW
    if payload.MODEL_REFLECTION is not None:
        settings.MODEL_REFLECTION = payload.MODEL_REFLECTION
    if payload.MODEL_PLANNER is not None:
        settings.MODEL_PLANNER = payload.MODEL_PLANNER
    if payload.PROMPT_POST_CREATION is not None:
        settings.PROMPT_POST_CREATION = payload.PROMPT_POST_CREATION
    if payload.PROMPT_REPLY_ANALYSIS is not None:
        settings.PROMPT_REPLY_ANALYSIS = payload.PROMPT_REPLY_ANALYSIS
    if payload.PROMPT_TREND_ANALYSIS is not None:
        settings.PROMPT_TREND_ANALYSIS = payload.PROMPT_TREND_ANALYSIS
    if payload.PROMPT_LIKE_RETWEET is not None:
        settings.PROMPT_LIKE_RETWEET = payload.PROMPT_LIKE_RETWEET
    if payload.PROMPT_FOLLOW is not None:
        settings.PROMPT_FOLLOW = payload.PROMPT_FOLLOW
    if payload.CONTEXT_POST_CREATION is not None:
        settings.CONTEXT_POST_CREATION = payload.CONTEXT_POST_CREATION
    if payload.CONTEXT_REPLY_ANALYSIS is not None:
        settings.CONTEXT_REPLY_ANALYSIS = payload.CONTEXT_REPLY_ANALYSIS
    if payload.CONTEXT_TREND_ANALYSIS is not None:
        settings.CONTEXT_TREND_ANALYSIS = payload.CONTEXT_TREND_ANALYSIS
    if payload.CONTEXT_LIKE_RETWEET is not None:
        settings.CONTEXT_LIKE_RETWEET = payload.CONTEXT_LIKE_RETWEET
    if payload.CONTEXT_FOLLOW is not None:
        settings.CONTEXT_FOLLOW = payload.CONTEXT_FOLLOW
    if payload.MISTRAL_API_KEY is not None:
        settings.MISTRAL_API_KEY = payload.MISTRAL_API_KEY
    if payload.GEMINI_API_KEY is not None:
        settings.GEMINI_API_KEY = payload.GEMINI_API_KEY
    if payload.DEEPSEEK_API_KEY is not None:
        settings.DEEPSEEK_API_KEY = payload.DEEPSEEK_API_KEY
    if payload.OPENROUTER_API_KEY is not None:
        settings.OPENROUTER_API_KEY = payload.OPENROUTER_API_KEY

    # Persist back to .env
    env_path = Path("/home/ubuntu/projects/xbot/backend/.env")
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    updated = {
        "LITELLM_BASE_URL": settings.LITELLM_BASE_URL,
        "LITELLM_API_KEY": settings.LITELLM_API_KEY,
        "LITELLM_PRIMARY_MODEL": settings.LITELLM_PRIMARY_MODEL,
        "LITELLM_FAST_MODEL": settings.LITELLM_FAST_MODEL,
        "MODEL_POST_CREATION": settings.MODEL_POST_CREATION,
        "MODEL_REPLY_ANALYSIS": settings.MODEL_REPLY_ANALYSIS,
        "MODEL_HOOK_OPTIMIZER": settings.MODEL_HOOK_OPTIMIZER,
        "MODEL_POLL_GENERATOR": settings.MODEL_POLL_GENERATOR,
        "MODEL_TREND_ANALYSIS": settings.MODEL_TREND_ANALYSIS,
        "MODEL_LIKE_RETWEET": settings.MODEL_LIKE_RETWEET,
        "MODEL_FOLLOW": settings.MODEL_FOLLOW,
        "MODEL_REFLECTION": settings.MODEL_REFLECTION,
        "MODEL_PLANNER": settings.MODEL_PLANNER,
        "PROMPT_POST_CREATION": settings.PROMPT_POST_CREATION,
        "PROMPT_REPLY_ANALYSIS": settings.PROMPT_REPLY_ANALYSIS,
        "PROMPT_TREND_ANALYSIS": settings.PROMPT_TREND_ANALYSIS,
        "PROMPT_LIKE_RETWEET": settings.PROMPT_LIKE_RETWEET,
        "PROMPT_FOLLOW": settings.PROMPT_FOLLOW,
        "CONTEXT_POST_CREATION": settings.CONTEXT_POST_CREATION,
        "CONTEXT_REPLY_ANALYSIS": settings.CONTEXT_REPLY_ANALYSIS,
        "CONTEXT_TREND_ANALYSIS": settings.CONTEXT_TREND_ANALYSIS,
        "CONTEXT_LIKE_RETWEET": settings.CONTEXT_LIKE_RETWEET,
        "CONTEXT_FOLLOW": settings.CONTEXT_FOLLOW,
        "MISTRAL_API_KEY": settings.MISTRAL_API_KEY,
        "GEMINI_API_KEY": settings.GEMINI_API_KEY,
        "DEEPSEEK_API_KEY": settings.DEEPSEEK_API_KEY,
        "OPENROUTER_API_KEY": settings.OPENROUTER_API_KEY
    }

    found_keys = set()
    new_lines = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updated:
                new_lines.append(f"{k}={updated[k]}")
                found_keys.add(k)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for k, v in updated.items():
        if k not in found_keys:
            new_lines.append(f"{k}={v}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return {
        "status": "success",
        "message": "System configuration updated and saved successfully.",
        "config": {
            "DATABASE_URL": settings.DATABASE_URL.split("@")[-1],
            "REDIS_URL": settings.REDIS_URL,
            "LITELLM_BASE_URL": settings.LITELLM_BASE_URL,
            "LITELLM_API_KEY": settings.LITELLM_API_KEY,
            "LITELLM_PRIMARY_MODEL": settings.LITELLM_PRIMARY_MODEL,
            "LITELLM_FAST_MODEL": settings.LITELLM_FAST_MODEL,
            "MODEL_POST_CREATION": settings.MODEL_POST_CREATION,
            "MODEL_REPLY_ANALYSIS": settings.MODEL_REPLY_ANALYSIS,
            "MODEL_HOOK_OPTIMIZER": settings.MODEL_HOOK_OPTIMIZER,
            "MODEL_POLL_GENERATOR": settings.MODEL_POLL_GENERATOR,
            "MODEL_TREND_ANALYSIS": settings.MODEL_TREND_ANALYSIS,
            "MODEL_LIKE_RETWEET": settings.MODEL_LIKE_RETWEET,
            "MODEL_FOLLOW": settings.MODEL_FOLLOW,
            "MODEL_REFLECTION": settings.MODEL_REFLECTION,
            "MODEL_PLANNER": settings.MODEL_PLANNER,
            "PROMPT_POST_CREATION": settings.PROMPT_POST_CREATION,
            "PROMPT_REPLY_ANALYSIS": settings.PROMPT_REPLY_ANALYSIS,
            "PROMPT_TREND_ANALYSIS": settings.PROMPT_TREND_ANALYSIS,
            "PROMPT_LIKE_RETWEET": settings.PROMPT_LIKE_RETWEET,
            "PROMPT_FOLLOW": settings.PROMPT_FOLLOW,
            "CONTEXT_POST_CREATION": settings.CONTEXT_POST_CREATION,
            "CONTEXT_REPLY_ANALYSIS": settings.CONTEXT_REPLY_ANALYSIS,
            "CONTEXT_TREND_ANALYSIS": settings.CONTEXT_TREND_ANALYSIS,
            "CONTEXT_LIKE_RETWEET": settings.CONTEXT_LIKE_RETWEET,
            "CONTEXT_FOLLOW": settings.CONTEXT_FOLLOW,
            "MISTRAL_API_KEY": settings.MISTRAL_API_KEY,
            "GEMINI_API_KEY": settings.GEMINI_API_KEY,
            "DEEPSEEK_API_KEY": settings.DEEPSEEK_API_KEY,
            "OPENROUTER_API_KEY": settings.OPENROUTER_API_KEY,
            "API_PORT": settings.API_PORT,
        }
    }

import httpx

@router.get("/system/models")
async def get_system_models(
    provider: str = "litellm",
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Fetches the actual model list from the specified OpenAI-compatible or provider API."""
    url = ""
    req_key = api_key or ""
    
    if provider == "gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/openai/models"
        req_key = req_key or settings.GEMINI_API_KEY
    elif provider == "mistral":
        url = "https://api.mistral.ai/v1/models"
        req_key = req_key or settings.MISTRAL_API_KEY
    elif provider == "openrouter":
        url = "https://openrouter.ai/api/v1/models"
        req_key = req_key or settings.OPENROUTER_API_KEY
    elif provider == "deepseek":
        url = "https://api.deepseek.com/models"
        req_key = req_key or settings.DEEPSEEK_API_KEY
    else:  # litellm or custom openai compatible
        target_base = base_url or settings.LITELLM_BASE_URL or "https://llm.002529.xyz/v1"
        url = f"{target_base.rstrip('/')}/models"
        req_key = req_key or settings.LITELLM_API_KEY or "sk-y_2_lD1m4Ojw1QFMDEWgwA"

    if not req_key:
        return {"models": []}
        
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {req_key}"})
            if resp.status_code != 200:
                logger.error(f"Failed to fetch models for {provider}: {resp.status_code} {resp.text}")
                return {"models": []}
            data = resp.json()
            models_list = data.get("data", [])
            model_ids = [m.get("id") for m in models_list if isinstance(m, dict) and "id" in m]
            if not model_ids and isinstance(models_list, list):
                model_ids = [str(m) for m in models_list if isinstance(m, str)]
            return {"models": model_ids, "raw": models_list}
    except Exception as e:
        logger.error(f"Exception fetching models for {provider}: {e}")
        return {"models": []}