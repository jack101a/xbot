from __future__ import annotations

import logging
import time
from typing import Any

import redis

from xbot.celery_app import celery_app
from xbot.config import settings
from xbot.supervisor.auditor import PipelineAuditor

logger = logging.getLogger("xbot.supervisor.tier2_middleware")


class MiddlewareHealthTier:
    """
    Tier 2 Health Inspector: Middleware and Asynchronous Broker Runtime.
    Monitors Celery worker node responsiveness, Redis queue backlogs/stalls,
    and leaked distributed locks.
    """

    QUEUES_TO_CHECK = ["celery", "publish", "browser"]

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        auditor: PipelineAuditor | None = None,
    ) -> None:
        self.r = redis_client or redis.from_url(settings.REDIS_URL)
        self.auditor = auditor or PipelineAuditor(redis_client=self.r)

    def audit_celery_workers(self) -> list[dict[str, Any]]:
        """
        Pings Celery workers and verifies that tasks@* and browser@* worker nodes are alive.
        """
        findings: list[dict[str, Any]] = []

        try:
            ping_res = celery_app.control.ping(timeout=2.0)
        except Exception as e:
            logger.warning("Celery ping control check failed: %s", e)
            findings.append({
                "level": "CRITICAL",
                "tier": 2,
                "component": "celery_worker",
                "worker": "all",
                "message": f"Celery control ping failed: {e}",
                "action_needed": "restart_container",
            })
            return findings

        worker_names: list[str] = []
        if isinstance(ping_res, list):
            for item in ping_res:
                if isinstance(item, dict):
                    worker_names.extend(item.keys())
                elif isinstance(item, str):
                    worker_names.append(item)
        elif isinstance(ping_res, dict):
            worker_names.extend(ping_res.keys())

        if not worker_names:
            findings.append({
                "level": "CRITICAL",
                "tier": 2,
                "component": "celery_worker",
                "worker": "all",
                "message": "No active Celery workers responded to ping",
                "action_needed": "restart_container",
            })
            return findings

        has_tasks = any(
            w.startswith("tasks@") or ("tasks" in w and "browser" not in w) or (w.startswith("celery@") and "browser" not in w)
            for w in worker_names
        )
        has_browser = any(
            w.startswith("browser@") or "browser" in w
            for w in worker_names
        )

        if not has_tasks:
            findings.append({
                "level": "CRITICAL",
                "tier": 2,
                "component": "celery_worker",
                "worker": "tasks",
                "message": "Celery worker node 'tasks@*' is missing or unresponsive",
                "action_needed": "restart_container",
            })

        if not has_browser:
            findings.append({
                "level": "CRITICAL",
                "tier": 2,
                "component": "celery_worker",
                "worker": "browser",
                "message": "Celery worker node 'browser@*' is missing or unresponsive",
                "action_needed": "restart_container",
            })

        return findings

    def audit_redis_queues(self) -> list[dict[str, Any]]:
        """
        Inspects lengths of celery, publish, and browser queues.
        Flags backlog depth > 50 and unserviced stalls > 15 minutes.
        """
        findings: list[dict[str, Any]] = []
        now_ts = int(time.time())

        for q in self.QUEUES_TO_CHECK:
            try:
                depth = self.r.llen(q)
            except Exception as e:
                logger.error("Failed querying Redis queue length for %s: %s", q, e)
                continue

            stall_key = f"xbot:sentinel:queue_stall:{q}"

            # Depth threshold > 50
            if depth > 50:
                findings.append({
                    "level": "WARNING",
                    "tier": 2,
                    "component": "redis_queue",
                    "queue": q,
                    "depth": depth,
                    "message": f"Queue '{q}' backlog depth {depth} > 50",
                    "action_needed": "soft_heal",
                })

            # Unserviced stall detection (> 15m)
            if depth > 0:
                first_seen = self.r.get(stall_key)
                if not first_seen:
                    self.r.set(stall_key, str(now_ts), ex=3600)
                else:
                    try:
                        stall_duration = now_ts - int(first_seen)
                        if stall_duration > 900:  # 15 minutes
                            findings.append({
                                "level": "CRITICAL",
                                "tier": 2,
                                "component": "redis_queue",
                                "queue": q,
                                "depth": depth,
                                "stall_seconds": stall_duration,
                                "message": f"Queue '{q}' has been unserviced for {stall_duration // 60}m (depth: {depth})",
                                "action_needed": "restart_container",
                            })
                    except (ValueError, TypeError):
                        self.r.set(stall_key, str(now_ts), ex=3600)
            else:
                self.r.delete(stall_key)

        return findings

    def audit_redis_locks(self) -> list[dict[str, Any]]:
        """
        Inspects Redis locks for deadlocks (TTL == -1) or abnormal leaks (TTL > 7200).
        """
        findings: list[dict[str, Any]] = []
        try:
            leaked_locks = self.auditor.audit_redis_locks()
            for lock in leaked_locks:
                ttl = lock.get("ttl", 0)
                findings.append({
                    "level": "CRITICAL" if ttl == -1 else "WARNING",
                    "tier": 2,
                    "component": "redis_lock",
                    "lock_key": lock["key"],
                    "ttl": ttl,
                    "profile_slug": lock.get("profile_slug"),
                    "reason": lock.get("reason"),
                    "action_needed": "soft_heal",
                    "message": f"Leaked Redis lock '{lock['key']}' (TTL: {ttl})",
                })
        except Exception as e:
            logger.error("Failed auditing Redis locks: %s", e)

        return findings

    async def audit_middleware(self) -> list[dict[str, Any]]:
        """
        Runs the full Tier 2 inspection suite.
        """
        findings: list[dict[str, Any]] = []
        findings.extend(self.audit_celery_workers())
        findings.extend(self.audit_redis_queues())
        findings.extend(self.audit_redis_locks())
        return findings
