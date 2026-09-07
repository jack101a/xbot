"""
AI Prompt and Conversation Interaction Logger for XBot Pro.

Captures all outbound prompts (system & user directives), model parameters,
latency, raw responses, and cascade fallbacks for dashboard inspection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import redis

from xbot.config import settings

logger = logging.getLogger(__name__)

REDIS_LOG_KEY = "xbot:ai_prompt_logs"
MAX_LOG_ITEMS = 500


def _get_redis_client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


async def log_ai_interaction_async(
    messages: list[dict[str, Any]],
    response_text: str | None,
    model: str,
    provider: str,
    latency_ms: int,
    status: str = "success",
    action_type: str = "general",
    profile_slug: str | None = None,
    error_message: str | None = None,
    tokens: int | None = None,
) -> None:
    """Non-blocking background helper to record an AI prompt and response."""
    try:
        system_prompt = ""
        user_prompt = ""
        other_messages = []

        for msg in messages:
            role = msg.get("role", "")
            content = str(msg.get("content", ""))
            if role == "system" and not system_prompt:
                system_prompt = content
            elif role == "user" and not user_prompt:
                user_prompt = content
            else:
                other_messages.append({"role": role, "content": content})

        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "profile_slug": profile_slug or "global",
            "action_type": action_type,
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "status": status,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "other_messages": other_messages if other_messages else None,
            "response": response_text or "",
            "error_message": error_message,
            "tokens": tokens,
        }

        r = _get_redis_client()
        serialized = json.dumps(entry)
        pipe = r.pipeline()
        pipe.lpush(REDIS_LOG_KEY, serialized)
        pipe.ltrim(REDIS_LOG_KEY, 0, MAX_LOG_ITEMS - 1)
        pipe.execute()
    except Exception as e:
        logger.debug("Failed to record AI prompt log: %s", e)


def get_ai_prompt_logs(
    limit: int = 50,
    offset: int = 0,
    provider_filter: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieves and filters recent AI prompt interactions."""
    try:
        r = _get_redis_client()
        raw_items = r.lrange(REDIS_LOG_KEY, 0, MAX_LOG_ITEMS - 1)
        logs: list[dict[str, Any]] = []

        for item in raw_items:
            try:
                entry = json.loads(item)
                if provider_filter and provider_filter.lower() not in entry.get("provider", "").lower():
                    continue
                if query:
                    q = query.lower()
                    text_blob = f"{entry.get('system_prompt', '')} {entry.get('user_prompt', '')} {entry.get('response', '')} {entry.get('action_type', '')}"
                    if q not in text_blob.lower():
                        continue
                logs.append(entry)
            except Exception:
                continue

        return logs[offset : offset + limit]
    except Exception as e:
        logger.warning("Error fetching AI prompt logs from Redis: %s", e)
        return []


def clear_ai_prompt_logs() -> bool:
    """Clears the AI prompt logs from Redis."""
    try:
        r = _get_redis_client()
        r.delete(REDIS_LOG_KEY)
        return True
    except Exception as e:
        logger.warning("Error clearing AI prompt logs: %s", e)
        return False
