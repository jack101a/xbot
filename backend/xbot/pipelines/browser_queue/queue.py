"""
Browser Queue Data Structures and Redis Queue Operations.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

import redis

from xbot.config import settings

logger = logging.getLogger(__name__)

ACTION_QUEUE_KEY = "xbot:browser_jobs:action_queue"
RESEARCH_QUEUE_KEY = "xbot:browser_jobs:research_queue"
QUEUE_KEY = ACTION_QUEUE_KEY  # Backward-compatible alias
JOB_PREFIX = "xbot:browser_job:"
RESULT_PREFIX = "xbot:browser_result:"
QUEUE_LOCK_KEY = "xbot:lock:browser_queue_worker"

_WRITE_ACTION_STRINGS = {
    "like",
    "reply",
    "quote",
    "post",
    "thread",
    "poll",
    "follow",
    "unfollow",
    "delete_tweet",
    "prune_timeline",
}


def get_queue_key_for_action(action_type: str) -> str:
    """Classifies action as write (action queue) vs read (research queue)."""
    if action_type.lower() in _WRITE_ACTION_STRINGS:
        return ACTION_QUEUE_KEY
    return RESEARCH_QUEUE_KEY


@dataclass
class BrowserJob:
    action_type: str  # "like", "reply", "quote", "post", "follow", "unfollow", "scrape_feed", "scrape_trending", etc.
    profile_slug: str
    params: dict[str, Any] = field(default_factory=dict)
    priority: int = 2  # 0=emergency/sniper, 1=conversation_reply, 2=post/quote, 3=like/follow, 4=scrape
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    ttl_seconds: int = 300  # 5 minutes expiration


def get_redis_client(redis_url: str | None = None) -> redis.Redis:
    return redis.from_url(redis_url or settings.REDIS_URL, decode_responses=True)


def enqueue_browser_job(
    job: BrowserJob,
    r: redis.Redis | None = None,
    queue_key: str | None = None,
) -> str:
    """Enqueues a browser job in Redis with priority scoring and dual-lane routing."""
    if r is None:
        r = get_redis_client()

    target_queue = queue_key or get_queue_key_for_action(job.action_type)

    job_data = asdict(job)
    # Store job payload
    r.set(f"{JOB_PREFIX}{job.job_id}", json.dumps(job_data), ex=job.ttl_seconds + 300)

    # Score = priority * 1e10 + created_at timestamp (lower score = popped first)
    score = float(job.priority * 1e10 + job.created_at)
    r.zadd(target_queue, {job.job_id: score})
    logger.info(
        "Enqueued browser job %s (%s) into '%s' for %s with priority %d (queue depth: %d)",
        job.job_id,
        job.action_type,
        target_queue,
        job.profile_slug,
        job.priority,
        r.zcard(target_queue),
    )

    try:
        from xbot.pipelines.browser_queue.worker import process_browser_queue
        process_browser_queue.apply_async(queue="browser")
    except Exception as e:
        logger.debug("Could not dispatch immediate browser queue trigger: %s", e)

    return job.job_id


def get_browser_job_result(
    job_id: str,
    timeout_seconds: float = 0.0,
    r: redis.Redis | None = None,
) -> dict[str, Any] | None:
    """Retrieves result of a processed browser job. Optionally polls up to timeout_seconds."""
    if r is None:
        r = get_redis_client()

    start_time = time.time()
    while True:
        raw_result = r.get(f"{RESULT_PREFIX}{job_id}")
        if raw_result:
            try:
                return json.loads(raw_result)
            except Exception:
                return {"status": "error", "message": "Failed to parse result JSON"}

        if timeout_seconds <= 0 or (time.time() - start_time) >= timeout_seconds:
            break
        time.sleep(0.5)

    return None


def set_browser_job_result(
    job_id: str,
    result: dict[str, Any],
    r: redis.Redis | None = None,
    ttl_seconds: int = 600,
) -> None:
    """Stores result of a processed browser job in Redis."""
    if r is None:
        r = get_redis_client()
    try:
        r.set(f"{RESULT_PREFIX}{job_id}", json.dumps(result), ex=ttl_seconds)
    except Exception as e:
        logger.error("Failed to set browser job result for %s: %s", job_id, e)


def get_queue_depth(r: redis.Redis | None = None, queue_key: str = QUEUE_KEY) -> int:
    """Returns number of pending jobs in browser queue."""
    if r is None:
        r = get_redis_client()
    try:
        return int(r.zcard(queue_key))
    except Exception:
        return 0


def pop_next_job(
    r: redis.Redis | None = None,
    queue_key: str = QUEUE_KEY,
) -> BrowserJob | None:
    """Atomically pops the highest priority job from the specified queue, discarding expired entries."""
    if r is None:
        r = get_redis_client()

    while True:
        items = r.zpopmin(queue_key, count=1)
        if not items:
            return None

        job_id, _score = items[0]
        raw_payload = r.get(f"{JOB_PREFIX}{job_id}")
        if not raw_payload:
            continue

        try:
            data = json.loads(raw_payload)
            job = BrowserJob(**data)
            # Check TTL
            if (time.time() - job.created_at) > job.ttl_seconds:
                continue
            return job
        except Exception as e:
            logger.error("Failed to deserialize browser job %s: %s", job_id, e)
            continue
