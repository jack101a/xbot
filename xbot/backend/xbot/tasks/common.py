from __future__ import annotations
import xbot.tasks as tasks

import asyncio
import datetime
import json
import logging
import os
import random
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.analytics import AnalyticsSnapshot, FollowerSnapshot, FollowerChangeLog
from xbot.models.realgraph import RealGraphEdge
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.persona import load_config
from xbot.persona.loader import load_persona
from xbot.safety.guard import SafetyGuard
from xbot.browser.manager import BrowserManager
from xbot.browser.timing import sleep_with_jitter, sleep_think_time
from xbot.browser.actions.x_actions import *
from xbot.celery_app import celery_app
from xbot.ai.client import get_ai_client
from xbot.ai.planner import plan_session
from xbot.ai.sniper import generate_sniper_reply
from xbot.ai.growth_scorer import score_tweet_opportunity
from xbot.ai.trend_radar import fetch_rss_trends, fetch_multi_source_trends
from xbot.ai.trend_generator import generate_trend_take
from xbot.ai.visual_engine import generate_visual_post_spec
from xbot.ai.poll_generator import generate_poll
from xbot.ai.hook_optimizer import extract_links
from xbot.ai.post_session import PostSessionProcessor
from xbot.growth.f4f_engine import populate_f4f_candidates, record_follow_action, record_unfollow_action

logger = logging.getLogger("xbot.tasks")

async def _extract_or_generate_poll_data(
    p_action: Any,
    profile_slug: str,
    base_profile_dir: Path,
) -> tuple[str, list[str], int, str | None, str]:
    """
    Extracts poll question and options if specified in JSON format in the plan action,
    or generates a validated poll via AI matching the persona.
    """
    poll_question = ""
    poll_options: list[str] = []
    poll_duration_days = 1
    poll_context_hook: str | None = None
    poll_reasoning = ""

    if p_action.content:
        try:
            parsed_c = json.loads(p_action.content)
            if isinstance(parsed_c, dict) and "options" in parsed_c and "question" in parsed_c:
                poll_question = str(parsed_c["question"])
                poll_options = [str(opt) for opt in parsed_c["options"]]
                poll_duration_days = int(parsed_c.get("duration_days", 1))
                poll_context_hook = parsed_c.get("context_hook")
                poll_reasoning = parsed_c.get("reasoning", "")
        except Exception:
            pass

    if not poll_options or len(poll_options) < 2:
        persona_loader = getattr(tasks, "load_persona", load_persona)
        persona = persona_loader(base_profile_dir / profile_slug)
        topic = (
            p_action.content
            if (p_action.content and not p_action.content.startswith("{"))
            else (p_action.target or None)
        )
        poll_gen_func = getattr(tasks, "generate_poll", generate_poll)
        gen_poll = await poll_gen_func(persona=persona, topic=topic)
        if gen_poll:
            poll_question = gen_poll.question
            poll_options = gen_poll.options
            poll_duration_days = gen_poll.duration_days
            poll_context_hook = gen_poll.context_hook
            poll_reasoning = gen_poll.reasoning
        else:
            return "", [], 1, None, ""

    full_question = (
        f"{poll_context_hook}\n\n{poll_question}"
        if poll_context_hook and poll_context_hook not in poll_question
        else poll_question
    )

    return full_question, poll_options, poll_duration_days, poll_context_hook, poll_reasoning


def extract_tweet_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    m = re.search(r'/status/(\d+)', str(url))
    return m.group(1) if m else None


async def has_already_acted(
    db: AsyncSession,
    profile_id: uuid.UUID,
    target_url: str | None,
    action_type: Any,
    hours: int = 168,
) -> bool:
    """
    Checks if an action of the specified type has already been executed or queued
    against the given target_url or canonical numeric tweet ID within the last `hours` (default 7 days).
    Prevents duplicate likes, replies, and quotes on the exact same tweets.
    """
    if not target_url:
        return False
    clean_target = target_url.strip().rstrip("/")
    t_id = extract_tweet_id_from_url(clean_target)
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    act_type_str = action_type.value if hasattr(action_type, "value") else str(action_type)

    stmt = (
        select(Action)
        .where(
            Action.profile_id == profile_id,
            Action.action_type == act_type_str,
            Action.status.in_([ActionStatus.COMPLETED, ActionStatus.PENDING, ActionStatus.STAGED]),
            Action.executed_at >= cutoff,
        )
    )
    res = await db.execute(stmt)
    actions = res.scalars().all()
    for act in actions:
        if not act.target_url:
            continue
        if t_id and extract_tweet_id_from_url(act.target_url) == t_id:
            return True
        if act.target_url.strip().rstrip("/") == clean_target:
            return True
    return False

def _parse_x_counts(text: str) -> int:
    """Helper to convert X counts string shorthand like 2.5K or 1M to integers."""
    import re
    # Find the first token representing a number (e.g. 2.5K, 12, 1,234, 1.2M)
    match = re.search(r'([\d.,]+[KMB]?)', text, re.IGNORECASE)
    if not match:
        return 0
    num_str = match.group(1).upper().replace(",", "")
    if "K" in num_str:
        return int(float(num_str.replace("K", "")) * 1000)
    elif "M" in num_str:
        return int(float(num_str.replace("M", "")) * 1000000)
    elif "B" in num_str:
        return int(float(num_str.replace("B", "")) * 1000000000)
    else:
        # Extract digits and decimal point if any
        digits = "".join(filter(lambda ch: ch.isdigit() or ch == '.', num_str))
        try:
            return int(float(digits))
        except ValueError:
            return 0


def broadcast_session_log(
    session_id: uuid.UUID | str,
    event_type: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Broadcasts a real-time event to the Redis channel for live WebSocket logs with standardized payload keys."""
    try:
        import json
        import redis
        from xbot.config import settings
        r = redis.from_url(settings.REDIS_URL)
        payload_data = data or {}
        payload = {
            "event": event_type,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": str(session_id),
            "action_type": payload_data.get("action_type"),
            "status": payload_data.get("status"),
            "content": payload_data.get("content"),
            "error": payload_data.get("error"),
            **payload_data,
        }
        json_str = json.dumps(payload)
        # Publish to single session channel
        r.publish(f"session:log:{session_id}", json_str)
        # Publish to global live stream channel
        r.publish("session:log:live", json_str)
    except Exception as ex:
        logger.error("Failed to broadcast session log: %s", ex)
