from __future__ import annotations

import datetime
import logging
import os
import time
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None
import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.celery_app import celery_app
from xbot.config import settings
from xbot.models.content import Content, ContentStatus
from xbot.models.pipeline import PipelineRun
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Session, SessionStatus
from xbot.utils.time import now_ist

logger = logging.getLogger("xbot.supervisor.auditor")


class PipelineAuditor:
    """
    Continuous Observation and Audit Engine with Bulletproof Safety Guards.
    Inspects Redis distributed locks, Celery queues, database session states,
    pipeline runs, approved drafts, and OS process tables to detect stalled or failed operations
    without ever interfering with legitimate running tasks.
    """

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self.r = redis_client or redis.from_url(settings.REDIS_URL)

    def get_active_celery_context(self) -> dict[str, Any]:
        """
        Safely queries Celery control inspect to determine active tasks, pipelines, and profiles.
        Fails safely (returns empty/busy) on inspect timeout so no destructive action is taken.
        """
        try:
            insp = celery_app.control.inspect(timeout=1.5)
            active = insp.active() or {}
            reserved = insp.reserved() or {}

            all_active: list[dict[str, Any]] = []
            for worker_tasks in active.values():
                if worker_tasks:
                    all_active.extend(worker_tasks)
            for worker_tasks in reserved.values():
                if worker_tasks:
                    all_active.extend(worker_tasks)

            active_task_names = set()
            active_profiles = set()

            for t in all_active:
                name = t.get("name", "")
                active_task_names.add(name)
                args = t.get("args") or []
                kwargs = t.get("kwargs") or {}
                if "profile_slug" in kwargs:
                    active_profiles.add(str(kwargs["profile_slug"]))
                for a in args:
                    if isinstance(a, str) and len(a) < 50:
                        active_profiles.add(a)

            browser_busy = any(
                len(tasks) > 0 for worker, tasks in active.items() if "browser" in worker
            ) or any(
                len(tasks) > 0 for worker, tasks in reserved.items() if "browser" in worker
            )

            return {
                "active_tasks": all_active,
                "task_names": active_task_names,
                "active_profiles": active_profiles,
                "browser_busy": browser_busy,
            }
        except Exception as e:
            logger.warning("Celery active inspect timed out or failed: %s. Defaulting to fail-safe.", e)
            return {
                "active_tasks": [],
                "task_names": set(),
                "active_profiles": set(),
                "browser_busy": True,  # Fail-safe: assume busy to prevent pruning active browser
            }

    def audit_redis_locks(self, celery_ctx: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Inspects all browser and pipeline execution locks in Redis.
        SAFEGUARDS:
        - Only flags locks with ttl == -1 (permanent leaked keys with no expiration) or ttl > 7200 (abnormal >2h leak).
        - NEVER flags locks with normal remaining TTL (e.g. 100-1800s).
        - NEVER touches locks belonging to profiles actively running in Celery.
        """
        issues: list[dict[str, Any]] = []
        lock_patterns = ["lock:browser:*", "xbot:*:lock:*", "xbot:lock:*"]
        ctx = celery_ctx if celery_ctx is not None else self.get_active_celery_context()

        for pattern in lock_patterns:
            try:
                keys = self.r.keys(pattern)
            except Exception as e:
                logger.error("Failed querying Redis keys with pattern %s: %s", pattern, e)
                continue

            for key_raw in keys:
                key = key_raw.decode("utf-8") if isinstance(key_raw, bytes) else str(key_raw)
                try:
                    ttl = self.r.ttl(key)
                    val = self.r.get(key)
                    val_str = val.decode("utf-8") if isinstance(val, bytes) else str(val) if val else ""

                    profile_slug = None
                    if key.startswith("lock:browser:"):
                        profile_slug = key.replace("lock:browser:", "")
                    elif ":lock:" in key:
                        parts = key.split(":")
                        if len(parts) >= 3:
                            profile_slug = parts[-1]

                    # Safeguard: If profile is actively executing a task in Celery, it is NOT an orphan
                    if profile_slug and profile_slug in ctx["active_profiles"]:
                        continue

                    # Condition 1: Lock has no TTL (-1 means permanent key with no expiration!)
                    if ttl == -1:
                        issues.append({
                            "type": "ORPHAN_REDIS_LOCK",
                            "key": key,
                            "profile_slug": profile_slug,
                            "ttl": ttl,
                            "holder": val_str,
                            "reason": "Lock key has no expiration TTL (permanent deadlock risk)",
                        })
                    # Condition 2: Abnormal excessive TTL (> 2 hours)
                    elif ttl > 7200:
                        issues.append({
                            "type": "STALE_REDIS_LOCK",
                            "key": key,
                            "profile_slug": profile_slug,
                            "ttl": ttl,
                            "holder": val_str,
                            "reason": f"Lock key has excessive abnormal TTL ({ttl}s)",
                        })
                except Exception as ex:
                    logger.debug("Error auditing lock key %s: %s", key, ex)

        return issues

    async def audit_stuck_sessions(
        self,
        db: AsyncSession,
        threshold_minutes: int = 35,
        celery_ctx: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Detects Sessions stuck in 'running' state beyond Celery's hard 30m execution limit.
        SAFEGUARDS:
        - Threshold is 35 minutes (> Celery task_time_limit of 30 mins).
        - Skips any session whose profile is still actively reported by Celery inspect.
        """
        cutoff = now_ist() - datetime.timedelta(minutes=threshold_minutes)
        cutoff_naive = cutoff.replace(tzinfo=None)
        ctx = celery_ctx if celery_ctx is not None else self.get_active_celery_context()

        stmt = (
            select(Session, Profile.profile_slug)
            .join(Profile, Session.profile_id == Profile.id)
            .where(
                Session.status == SessionStatus.RUNNING,
                Session.started_at <= cutoff_naive,
            )
        )
        res = await db.execute(stmt)
        rows = res.all()

        issues = []
        for sess, slug in rows:
            # Safeguard: If Celery worker still actively holds this profile, do NOT fail it
            if slug in ctx["active_profiles"] or str(sess.id) in str(ctx["active_tasks"]):
                continue

            runtime_m = int((now_ist().replace(tzinfo=None) - sess.started_at).total_seconds() // 60)
            issues.append({
                "type": "STUCK_SESSION",
                "session_id": str(sess.id),
                "profile_slug": slug,
                "started_at": sess.started_at.isoformat(),
                "runtime_minutes": runtime_m,
                "reason": f"Session running for {runtime_m}m without completion (threshold: {threshold_minutes}m)",
            })
        return issues

    async def audit_stuck_pipeline_runs(
        self,
        db: AsyncSession,
        threshold_minutes: int = 25,
        celery_ctx: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Detects PipelineRun entries stuck in 'running' state past threshold duration.
        SAFEGUARDS:
        - Skips any pipeline whose task name is still in Celery active tasks.
        """
        cutoff_naive = (now_ist() - datetime.timedelta(minutes=threshold_minutes)).replace(tzinfo=None)
        ctx = celery_ctx if celery_ctx is not None else self.get_active_celery_context()

        stmt = (
            select(PipelineRun, PipelineRun.pipeline_name)
            .where(
                PipelineRun.status == "running",
                PipelineRun.started_at <= cutoff_naive,
            )
        )
        res = await db.execute(stmt)
        stuck_runs = res.all()

        issues = []
        for run_obj, name in stuck_runs:
            # Safeguard: check if worker is actively running this pipeline
            if any(name in tname for tname in ctx["task_names"]):
                continue

            runtime_m = int((now_ist().replace(tzinfo=None) - run_obj.started_at).total_seconds() // 60)
            issues.append({
                "type": "STUCK_PIPELINE_RUN",
                "run_id": str(run_obj.id),
                "pipeline_name": name,
                "started_at": run_obj.started_at.isoformat(),
                "runtime_minutes": runtime_m,
                "reason": f"Pipeline run '{name}' stuck in running state for {runtime_m}m",
            })
        return issues

    async def audit_stuck_drafts(
        self,
        db: AsyncSession,
        threshold_minutes: int = 30,
        celery_ctx: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Detects Content items marked APPROVED that have not been posted within the threshold window.
        SAFEGUARDS:
        - Respects 'scheduled_for' in ai_metadata: Future scheduled posts are NEVER marked stuck!
        - Anti-flapping: Skips drafts currently on supervisor healing cooldown.
        - Skips if auto_publish_pending_drafts is actively running in Celery.
        """
        now_curr = now_ist()
        cutoff_naive = (now_curr - datetime.timedelta(minutes=threshold_minutes)).replace(tzinfo=None)
        ctx = celery_ctx if celery_ctx is not None else self.get_active_celery_context()

        # If auto_publish is currently running, let it do its job
        if "xbot.tasks.auto_publish_pending_drafts" in ctx["task_names"]:
            return []

        stmt = (
            select(Content, Profile.profile_slug)
            .join(Profile, Content.profile_id == Profile.id)
            .where(
                Content.status == ContentStatus.APPROVED,
                Content.posted_at.is_(None),
                Content.created_at <= cutoff_naive,
            )
        )
        res = await db.execute(stmt)
        stuck_items = res.all()

        issues = []
        for content_item, slug in stuck_items:
            ai_meta = content_item.ai_metadata or {}

            # Safeguard 1: Check future scheduled time
            sched_str = ai_meta.get("scheduled_for")
            if sched_str:
                try:
                    sched_dt = datetime.datetime.fromisoformat(sched_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    if sched_dt > now_curr.replace(tzinfo=None):
                        continue  # Scheduled for the future, perfectly normal
                    # If scheduled in the past, calculate overdue time based on scheduled_for
                    if (now_curr.replace(tzinfo=None) - sched_dt).total_seconds() < (threshold_minutes * 60):
                        continue  # Has not exceeded threshold past its scheduled time
                except Exception:
                    pass

            # Safeguard 2: Check Redis healing cooldown
            cooldown_key = f"xbot:supervisor:cooldown:publish:{content_item.id}"
            if self.r.exists(cooldown_key):
                continue

            age_m = int((now_curr.replace(tzinfo=None) - content_item.created_at).total_seconds() // 60)
            attempts = ai_meta.get("publish_attempts", 0)
            last_err = ai_meta.get("last_error", "None")

            issues.append({
                "type": "STUCK_APPROVED_DRAFT",
                "content_id": str(content_item.id),
                "profile_slug": slug,
                "created_at": content_item.created_at.isoformat(),
                "age_minutes": age_m,
                "publish_attempts": attempts,
                "last_error": last_err,
                "reason": f"Draft approved {age_m}m ago but unposted (attempts: {attempts}, last_err: {last_err})",
            })
        return issues

    async def audit_pipeline_cadence(
        self,
        db: AsyncSession,
        celery_ctx: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Checks what was planned vs reality for all active profiles.
        Identifies overdue growth posts and stalled research pipelines.
        SAFEGUARDS:
        - Respects anti-flapping Redis cooldowns (15 min cooldown after supervisor intervention).
        - Skips pipelines that are currently running or queued in Celery.
        - Only checks during active creator hours (06:00 to 02:00 IST).
        """
        issues: list[dict[str, Any]] = []
        stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
        res = await db.execute(stmt)
        profiles = res.scalars().all()

        current_dt_ist = now_ist()
        current_hour = current_dt_ist.hour
        now_ts = int(time.time())
        ctx = celery_ctx if celery_ctx is not None else self.get_active_celery_context()

        # Active creator hours: 06:00 to 02:00 IST
        is_active_hours = (6 <= current_hour <= 23) or (0 <= current_hour < 2)
        if not is_active_hours:
            return []

        for prof in profiles:
            slug = prof.profile_slug

            # 1. Follow Growth Post Cadence Check
            growth_cooldown_key = f"xbot:supervisor:cooldown:pipeline:follow_growth_post:{slug}"
            if not self.r.exists(growth_cooldown_key):
                # Only check if not already running in Celery
                if not any("follow_growth_post" in t for t in ctx["task_names"]):
                    next_due_key = f"xbot:growth_post:next_due:{slug}"
                    next_due_raw = self.r.get(next_due_key)
                    if next_due_raw:
                        try:
                            next_due_ts = int(next_due_raw)
                            # Overdue by > 30 minutes
                            if now_ts > (next_due_ts + 1800):
                                overdue_m = (now_ts - next_due_ts) // 60
                                issues.append({
                                    "type": "OVERDUE_GROWTH_POST",
                                    "pipeline_name": "follow_growth_post",
                                    "profile_slug": slug,
                                    "overdue_minutes": overdue_m,
                                    "reason": f"Follow Growth post was due {overdue_m}m ago but has not executed.",
                                })
                        except (ValueError, TypeError):
                            pass

            # 2. Circadian Session Gap Check
            circ_cooldown_key = f"xbot:supervisor:cooldown:pipeline:circadian_session:{slug}"
            if not self.r.exists(circ_cooldown_key) and prof.last_session_at:
                if not any("check_schedules" in t or "run_session" in t for t in ctx["task_names"]):
                    idle_seconds = (now_ist().replace(tzinfo=None) - prof.last_session_at).total_seconds()
                    idle_minutes = int(idle_seconds // 60)
                    # If active profile has been completely idle for > 240 minutes (4.0 hours)
                    if idle_minutes > 240:
                        issues.append({
                            "type": "OVERDUE_CIRCADIAN_SESSION",
                            "pipeline_name": "circadian_session",
                            "profile_slug": slug,
                            "idle_minutes": idle_minutes,
                            "reason": f"Profile has been idle for {idle_minutes}m during daytime active hours.",
                        })

        return issues

    def audit_worker_liveness(self) -> dict[str, Any]:
        """
        Pings all Celery workers and inspects active task queues.
        """
        try:
            ping_res = celery_app.control.ping(timeout=2.0)
            active_workers = []
            if ping_res:
                for w in ping_res:
                    if isinstance(w, dict):
                        active_workers.extend(list(w.keys()))
                    elif isinstance(w, str):
                        active_workers.append(w)

            return {
                "alive": len(active_workers) > 0,
                "worker_count": len(active_workers),
                "workers": active_workers,
                "error": None,
            }
        except Exception as e:
            logger.warning("Celery ping check failed: %s", e)
            return {
                "alive": False,
                "worker_count": 0,
                "workers": [],
                "error": str(e),
            }

    def audit_zombie_browsers(self, celery_ctx: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Scans for orphaned headless Chromium processes.
        SAFEGUARDS:
        - NEVER reaps Chromium if Celery browser worker is actively running or reserved with ANY task!
        - Only checks processes owned by current user UID (never touches system or Docker).
        - Threshold is > 30 minutes (safely exceeding max session duration).
        """
        ctx = celery_ctx if celery_ctx is not None else self.get_active_celery_context()

        # Fail-safe: if any browser worker has active tasks, do not touch any Chromium process!
        if ctx["browser_busy"] or psutil is None:
            return []

        zombies: list[dict[str, Any]] = []
        now_ts = time.time()
        current_uid = os.getuid() if hasattr(os, "getuid") else None

        for proc in psutil.process_iter(['pid', 'name', 'create_time', 'cmdline', 'uids']):
            try:
                # Only check processes owned by current user (avoids Docker/system root processes)
                if current_uid is not None:
                    uids = proc.info.get('uids')
                    if uids and uids.real != current_uid:
                        continue

                cmdline = proc.info.get('cmdline') or []
                cmd_str = " ".join(cmdline).lower()

                if ("chrome" in cmd_str or "chromium" in cmd_str) and "--headless" in cmd_str:
                    create_time = proc.info.get('create_time') or now_ts
                    age_seconds = now_ts - create_time
                    age_minutes = int(age_seconds // 60)

                    # If headless chromium has been running for > 30 minutes while browser worker is idle
                    if age_minutes > 30:
                        zombies.append({
                            "type": "ZOMBIE_BROWSER_PROCESS",
                            "pid": proc.info['pid'],
                            "age_minutes": age_minutes,
                            "reason": f"Headless Chromium process (PID {proc.info['pid']}) running idle for {age_minutes}m",
                        })
            except Exception:
                continue

        return zombies
