from __future__ import annotations
import logging
import time
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
    CHATGPT_BRIDGE_URL: str | None = None

@router.put("/system/config", response_model=dict[str, Any])
async def update_system_config(payload: SystemConfigUpdate) -> dict[str, Any]:
    """Updates primary backend settings configuration details dynamically and persists them in .env."""
    from pathlib import Path
    
    payload_dict = payload.model_dump(exclude_unset=True)
    updated = {}
    for k, v in payload_dict.items():
        if v is not None and hasattr(settings, k):
            setattr(settings, k, v)
            updated[k] = v

    # Persist only explicitly provided fields back to .env
    env_paths = [
        Path("/app/data/.env"),
        Path("/app/.env"),
        Path("/home/ubuntu/projects/xbot/backend/.env"),
        Path("/home/ubuntu/projects/xbot/.env"),
        Path(".env"),
    ]
    env_path = next((p for p in env_paths if p.exists()), None)
    if not env_path:
        env_path = Path("/app/data/.env") if Path("/app/data").exists() else Path(".env")
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

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

    if updated:
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
            "CHATGPT_BRIDGE_URL": getattr(settings, "CHATGPT_BRIDGE_URL", "http://192.168.0.200:8465"),
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


class ChatGPTTestPayload(BaseModel):
    bridge_url: str | None = None


class ChatGPTCookiePayload(BaseModel):
    cookies: str


@router.get("/system/chatgpt/status")
async def get_chatgpt_status() -> dict[str, Any]:
    """Inspects the active status and quota of the standalone ChatGPT Bridge."""
    bridge_url = getattr(settings, "CHATGPT_BRIDGE_URL", "http://192.168.0.200:8465").rstrip("/")
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            status_resp = await client.get(f"{bridge_url}/status")
            quota_resp = await client.get(f"{bridge_url}/api/accounts/quota")
            latency_ms = int((time.time() - start_time) * 1000)

            is_online = status_resp.status_code == 200
            status_data = status_resp.json() if is_online else {}
            quota_data = quota_resp.json().get("quota", {}) if quota_resp.status_code == 200 else {}

            authenticated = status_data.get("authenticated", False)
            if not authenticated and quota_data:
                authenticated = bool(quota_data.get("email"))

            plan_type = quota_data.get("plan_type", "unknown")
            left_percent = quota_data.get("left_percent", 100)
            user_email = quota_data.get("email") or "ChatGPT User"

            return {
                "status": "authenticated" if authenticated else "unauthenticated",
                "online": is_online,
                "authenticated": authenticated,
                "bridge_url": bridge_url,
                "latency_ms": latency_ms,
                "plan_type": plan_type,
                "left_percent": left_percent,
                "used_percent": quota_data.get("used_percent", 0),
                "reset_at_str": quota_data.get("reset_at_str"),
                "email": user_email,
                "message": f"Bridge online ({latency_ms}ms) · Plan: {plan_type.upper()} · {left_percent}% quota left",
            }
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "status": "offline",
            "online": False,
            "authenticated": False,
            "bridge_url": bridge_url,
            "latency_ms": latency_ms,
            "message": f"Bridge offline or unreachable at {bridge_url}: {e}",
        }


@router.post("/system/chatgpt/test")
async def test_chatgpt_live_session(payload: ChatGPTTestPayload | None = None) -> dict[str, Any]:
    """Tests connection, latency, authentication, and quota for the ChatGPT Bridge."""
    target_url = (payload.bridge_url if payload and payload.bridge_url else getattr(settings, "CHATGPT_BRIDGE_URL", "http://192.168.0.200:8465")).strip().rstrip("/")
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            health_resp = await client.get(f"{target_url}/health")
            if health_resp.status_code != 200:
                return {
                    "status": "error",
                    "authenticated": False,
                    "bridge_url": target_url,
                    "latency_ms": int((time.time() - start_time) * 1000),
                    "message": f"Health check returned HTTP {health_resp.status_code} from {target_url}",
                }

            quota_resp = await client.get(f"{target_url}/api/accounts/quota")
            latency_ms = int((time.time() - start_time) * 1000)
            quota_data = quota_resp.json().get("quota", {}) if quota_resp.status_code == 200 else {}

            user_email = quota_data.get("email") or "ChatGPT Account"
            plan = quota_data.get("plan_type", "Standard")
            left = quota_data.get("left_percent", 100)

            return {
                "status": "success",
                "authenticated": True,
                "bridge_url": target_url,
                "latency_ms": latency_ms,
                "user": {
                    "email": user_email,
                    "plan": plan,
                    "left_percent": left,
                },
                "quota": quota_data,
                "message": f"Successfully connected to ChatGPT Bridge at {target_url} ({latency_ms}ms) · Account: {user_email} ({plan.upper()})",
            }
    except Exception as exc:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "status": "error",
            "authenticated": False,
            "bridge_url": target_url,
            "latency_ms": latency_ms,
            "message": f"Failed to connect to {target_url}: {exc}",
        }


@router.post("/system/chatgpt/cookies")
async def import_chatgpt_cookies(payload: ChatGPTCookiePayload) -> dict[str, Any]:
    """Legacy cookie import endpoint kept for backward compatibility."""
    return {
        "status": "success",
        "message": "Cookies managed via standalone bridge. Use the Bridge Dashboard to refresh session tokens.",
    }