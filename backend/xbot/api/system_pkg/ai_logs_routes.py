"""
AI Prompt and Interaction Logs API Router.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from xbot.ai.prompt_logger import clear_ai_prompt_logs, get_ai_prompt_logs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system/ai-logs", tags=["system-ai-logs"])


class AIPromptLogItem(BaseModel):
    id: str
    timestamp: float
    iso_time: str
    profile_slug: str
    action_type: str
    provider: str
    model: str
    latency_ms: int
    status: str
    system_prompt: str
    user_prompt: str
    other_messages: Optional[list[dict[str, Any]]] = None
    response: str
    error_message: Optional[str] = None
    tokens: Optional[int] = None


class AIPromptLogsResponse(BaseModel):
    status: str = "success"
    count: int
    logs: list[AIPromptLogItem]


@router.get("", response_model=AIPromptLogsResponse)
async def list_ai_prompt_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    provider: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
) -> AIPromptLogsResponse:
    """Lists recent AI prompts, system directives, and model outputs."""
    raw_logs = get_ai_prompt_logs(
        limit=limit,
        offset=offset,
        provider_filter=provider,
        query=q,
    )
    items = [AIPromptLogItem(**l) for l in raw_logs]
    return AIPromptLogsResponse(count=len(items), logs=items)


@router.delete("")
async def clear_ai_logs() -> dict[str, Any]:
    """Clears the AI prompt interaction history from Redis."""
    success = clear_ai_prompt_logs()
    return {"status": "success" if success else "error", "message": "AI prompt logs cleared"}
