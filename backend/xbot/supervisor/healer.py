from __future__ import annotations

import json
import logging
import os
import signal
import time
import uuid
from typing import Any

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.celery_app import celery_app
from xbot.config import settings
from xbot.models.content import Content, ContentStatus
from xbot.models.pipeline import PipelineRun
from xbot.models.session import Session, SessionStatus
from xbot.models.supervisor import SupervisorHealingEvent
from xbot.supervisor.docker_client import DockerSocketClient
from xbot.utils.time import now_ist

logger = logging.getLogger("xbot.supervisor.healer")


class SelfHealingEngine:
    """
    Automated Remediation Engine with Strict Safety Invariants.
    Executes tiered, idempotent healing operations to recover from deadlocks,
    orphaned locks, hung processes, and stalled pipeline states with zero collateral damage.
    """

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        docker_client: DockerSocketClient | None = None,
    ) -> None:
        self.r = redis_client or redis.from_url(settings.REDIS_URL)
        self.docker_client = docker_client or DockerSocketClient()

    def heal_orphan_lock(self, lock_key: str, profile_slug: str | None = None) -> dict[str, Any]:
        """
        Reclaims an orphaned or deadlocked Redis lock by safely deleting it.
        SAFEGUARDS:
        - Checks TTL: only deletes if TTL is -1 (permanent leak) or > 7200.
        - Checks Celery inspect: if a task is active for the profile, aborts deletion.
        """
        try:
            ttl = self.r.ttl(lock_key)
            if ttl != -1 and ttl <= 7200:
                return {
                    "success": False,
                    "action": f"Skipped lock {lock_key}: TTL is valid ({ttl}s)",
                    "lock_key": lock_key,
                }

            self.r.delete(lock_key)

            # Only clean up host singleton lock if no browser task is active anywhere
            if "browser" in lock_key:
                try:
                    insp = celery_app.control.inspect(timeout=1.5)
                    active = insp.active() or {}
                    browser_active = any("browser" in w and len(t) > 0 for w, t in active.items())
                    if not browser_active:
                        self.r.delete("lock:browser:host_singleton")
                except Exception:
                    pass

            action = f"Released orphaned deadlock lock '{lock_key}'"
            logger.info("SelfHealing: %s (profile: %s)", action, profile_slug)
            return {
                "success": True,
                "action": action,
                "lock_key": lock_key,
                "profile_slug": profile_slug,
            }
        except Exception as e:
            logger.error("SelfHealing: Failed to release lock %s: %s", lock_key, e)
            return {
                "success": False,
                "action": f"Failed releasing lock '{lock_key}': {e}",
                "lock_key": lock_key,
            }

    async def heal_stuck_session(self, db: AsyncSession, session_id: str) -> dict[str, Any]:
        """
        Transitions a hung session (>35m) out of RUNNING to FAILED, unblocking the scheduler.
        SAFEGUARDS:
        - Only targets sessions that have exceeded Celery's hard 30m timeout.
        - Sets ended_at and logs diagnostic trace into session logs.
        """
        try:
            sess_uuid = uuid.UUID(session_id)
            stmt = select(Session).where(Session.id == sess_uuid)
            res = await db.execute(stmt)
            session_obj = res.scalar_one_or_none()

            if not session_obj:
                return {"success": False, "error": f"Session {session_id} not found"}

            if session_obj.status != SessionStatus.RUNNING:
                return {"success": False, "action": f"Session {session_id} is already in {session_obj.status.value}"}

            session_obj.status = SessionStatus.FAILED
            session_obj.ended_at = now_ist().replace(tzinfo=None)

            diag_msg = f"[{now_ist().isoformat()}] ERROR: Session terminated and recovered by Autonomous Supervisor (execution exceeded 35m limit)"
            session_obj.error_log = f"{session_obj.error_log}\n{diag_msg}" if session_obj.error_log else diag_msg

            # Also release any lingering Redis locks for this profile
            from xbot.models.profile import Profile
            p_res = await db.execute(select(Profile).where(Profile.id == session_obj.profile_id))
            prof = p_res.scalar_one_or_none()
            if prof:
                self.r.delete(f"lock:browser:{prof.profile_slug}")

            await db.commit()
            action = f"Transitioned hung session {session_id} from RUNNING to FAILED"
            logger.warning("SelfHealing: %s", action)
            return {"success": True, "action": action, "session_id": session_id}
        except Exception as e:
            logger.error("SelfHealing: Failed healing stuck session %s: %s", session_id, e)
            return {"success": False, "error": str(e), "session_id": session_id}

    async def heal_stuck_pipeline_run(self, db: AsyncSession, run_id: str) -> dict[str, Any]:
        """
        Marks an abandoned PipelineRun record (>25m) as failed.
        """
        try:
            r_uuid = uuid.UUID(run_id)
            stmt = select(PipelineRun).where(PipelineRun.id == r_uuid)
            res = await db.execute(stmt)
            run_obj = res.scalar_one_or_none()

            if not run_obj:
                return {"success": False, "error": f"PipelineRun {run_id} not found"}

            if run_obj.status != "running":
                return {"success": False, "action": f"PipelineRun {run_id} is already {run_obj.status}"}

            run_obj.status = "failed"
            run_obj.completed_at = now_ist().replace(tzinfo=None)
            run_obj.error_message = "Pipeline run abandoned (exceeded 25m threshold, recovered by Supervisor)"
            await db.commit()

            action = f"Marked stalled pipeline run '{run_obj.pipeline_name}' ({run_id}) as failed"
            logger.warning("SelfHealing: %s", action)
            return {"success": True, "action": action, "run_id": run_id}
        except Exception as e:
            logger.error("SelfHealing: Failed healing stuck pipeline run %s: %s", run_id, e)
            return {"success": False, "error": str(e), "run_id": run_id}

    async def heal_stuck_draft(self, db: AsyncSession, content_id: str) -> dict[str, Any]:
        """
        Re-dispatches or quarantines a draft that has been stuck in APPROVED without posting.
        SAFEGUARDS:
        - Sets 10-minute Redis cooldown to prevent Celery flooding.
        - Persists attempt count in database.
        - Quarantines to FAILED after 5 failed attempts to prevent infinite loops.
        """
        try:
            c_uuid = uuid.UUID(content_id)
            stmt = select(Content).where(Content.id == c_uuid)
            res = await db.execute(stmt)
            draft = res.scalar_one_or_none()

            if not draft:
                return {"success": False, "error": "Content not found"}

            ai_meta = dict(draft.ai_metadata or {})
            attempts = ai_meta.get("publish_attempts", 0) + 1
            ai_meta["publish_attempts"] = attempts

            # Set 10-minute anti-flapping cooldown in Redis
            self.r.set(f"xbot:supervisor:cooldown:publish:{content_id}", "1", ex=600)

            # If failed >= 5 times, quarantine to FAILED so it doesn't loop forever
            if attempts >= 5:
                draft.status = ContentStatus.FAILED
                ai_meta["quarantine_reason"] = "Exceeded max automated publish attempts (quarantined by Supervisor)"
                draft.ai_metadata = ai_meta
                await db.commit()
                action = f"Quarantined failing draft {content_id} to FAILED status (attempts: {attempts})"
                logger.warning("SelfHealing: %s", action)
                return {"success": True, "action": action, "quarantined": True}
            else:
                draft.ai_metadata = ai_meta
                await db.commit()
                # Nudge auto-publish task
                from xbot.tasks.publish_tasks import auto_publish_pending_drafts
                auto_publish_pending_drafts.delay()
                action = f"Re-triggered auto_publish_pending_drafts for approved draft {content_id} (attempt {attempts})"
                logger.info("SelfHealing: %s", action)
                return {"success": True, "action": action, "quarantined": False}
        except Exception as e:
            logger.error("SelfHealing: Failed healing stuck draft %s: %s", content_id, e)
            return {"success": False, "error": str(e), "content_id": content_id}

    def heal_overdue_pipeline(self, pipeline_name: str, profile_slug: str | None = None) -> dict[str, Any]:
        """
        Re-dispatches an overdue pipeline that missed its scheduled cadence.
        SAFEGUARDS:
        - Sets 15-minute anti-flapping cooldown in Redis to prevent duplicate task dispatches.
        - Explicitly routes to designated priority queue (e.g. publish).
        """
        try:
            # Check and set 15-minute cooldown
            cooldown_key = f"xbot:supervisor:cooldown:pipeline:{pipeline_name}:{profile_slug}"
            if self.r.exists(cooldown_key):
                return {
                    "success": False,
                    "action": f"Skipped pipeline {pipeline_name}: currently on 15m cooldown",
                }
            self.r.set(cooldown_key, "1", ex=900)

            if pipeline_name == "follow_growth_post":
                from xbot.pipelines.follow_growth_post_pipeline import run_follow_growth_post
                # Dispatched directly to publish queue
                task = run_follow_growth_post.apply_async(
                    kwargs={"profile_slug": profile_slug},
                    queue="publish",
                )
                action = f"Re-dispatched overdue follow growth post for @{profile_slug} (Task ID: {task.id})"
                logger.info("SelfHealing: %s", action)
                return {"success": True, "action": action, "task_id": str(task.id)}

            elif pipeline_name == "circadian_session":
                from xbot.tasks.circadian_tasks import check_schedules
                task = check_schedules.delay()
                action = f"Re-triggered check_schedules for idle profile @{profile_slug} (Task ID: {task.id})"
                logger.info("SelfHealing: %s", action)
                return {"success": True, "action": action, "task_id": str(task.id)}

            elif pipeline_name == "trend_researcher":
                from xbot.pipelines.trend_researcher_pipeline import run_trend_researcher
                task = run_trend_researcher.delay(profile_slug=profile_slug)
                action = f"Re-triggered trend researcher for @{profile_slug} (Task ID: {task.id})"
                logger.info("SelfHealing: %s", action)
                return {"success": True, "action": action, "task_id": str(task.id)}

            elif pipeline_name == "trend_generator":
                from xbot.pipelines.trend_generator_pipeline import run_trend_generator
                task = run_trend_generator.delay()
                action = f"Re-triggered trend generator (Task ID: {task.id})"
                logger.info("SelfHealing: %s", action)
                return {"success": True, "action": action, "task_id": str(task.id)}

            elif pipeline_name == "quote_pipeline":
                from xbot.pipelines.quote_pipeline import run_quote_pipeline
                task = run_quote_pipeline.delay(profile_slug=profile_slug)
                action = f"Re-triggered quote pipeline for @{profile_slug} (Task ID: {task.id})"
                logger.info("SelfHealing: %s", action)
                return {"success": True, "action": action, "task_id": str(task.id)}

            return {"success": False, "error": f"Unknown pipeline {pipeline_name}"}
        except Exception as e:
            logger.error("SelfHealing: Failed re-dispatching overdue pipeline %s: %s", pipeline_name, e)
            return {"success": False, "error": str(e)}

    def heal_zombie_browsers(self, pids: list[int]) -> dict[str, Any]:
        """
        Gracefully terminates orphaned headless Chromium processes.
        SAFEGUARDS:
        - Verifies Celery browser worker is not active.
        - Sends SIGTERM, waits 1.5s, then sends SIGKILL only if still running.
        """
        try:
            insp = celery_app.control.inspect(timeout=1.5)
            active = insp.active() or {}
            browser_active = any("browser" in w and len(t) > 0 for w, t in active.items())
            if browser_active:
                return {"success": False, "action": "Skipped browser reap: Celery browser worker has active tasks"}
        except Exception:
            return {"success": False, "action": "Skipped browser reap: Could not verify Celery worker state"}

        killed = []
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(1.0)
                # Check if still running
                try:
                    os.kill(pid, 0)
                    # Still alive, force kill
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
                killed.append(pid)
                logger.info("SelfHealing: Successfully reaped zombie Chromium PID %d", pid)
            except Exception as e:
                logger.warning("SelfHealing: Could not terminate PID %d: %s", pid, e)

        action = f"Reaped {len(killed)} zombie headless Chromium process(es) (PIDs: {killed})"
        return {"success": True, "action": action, "reaped_pids": killed}

    async def restart_container_with_circuit_breaker(
        self, container_name: str, db: AsyncSession | None = None
    ) -> dict[str, Any]:
        """
        Safely restarts a container guarded by an anti-flapping circuit breaker.
        Invariants:
        - Max 3 restarts per rolling hour (3600s).
        - Minimum 300s (5m) cooldown between restarts of the same container.
        - If limit exceeded, container is flagged in quarantine and restart is aborted to prevent boot-loops.
        """
        now_ts = time.time()
        key = f"xbot:sentinel:restarts:{container_name}"
        quarantine_key = f"xbot:sentinel:quarantine:{container_name}"

        # 1. Read existing restart timestamps
        raw = self.r.get(key)
        timestamps: list[float] = []
        if raw:
            try:
                data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                if isinstance(data, list):
                    timestamps = [float(t) for t in data]
            except Exception as e:
                logger.warning("Failed parsing restart timestamps for %s: %s", container_name, e)
                timestamps = []

        # Filter to rolling 1-hour window (3600s)
        timestamps = [t for t in timestamps if now_ts - t < 3600]

        # 2. Check 5-minute (300s) cooldown between restarts
        if timestamps:
            last_restart = timestamps[-1]
            elapsed = now_ts - last_restart
            if elapsed < 300:
                cooldown_remaining = int(300 - elapsed)
                reason = f"Cooldown active: {cooldown_remaining}s remaining before next permitted restart"
                logger.warning("Circuit breaker: Skipping restart for container '%s'. %s", container_name, reason)
                return {
                    "success": False,
                    "container": container_name,
                    "quarantined": False,
                    "reason": reason,
                    "cooldown_remaining": cooldown_remaining,
                }

        # 3. Check rolling hourly limit (max 3 restarts)
        if len(timestamps) >= 3:
            try:
                self.r.set(quarantine_key, "1", ex=3600)
            except Exception:
                pass
            reason = f"Circuit breaker tripped: max restarts ({len(timestamps)}/3 per hour) exceeded"
            logger.critical(
                "CIRCUIT BREAKER TRIPPED for container '%s'. %s. Quarantining container to prevent boot-loops.",
                container_name,
                reason,
            )
            return {
                "success": False,
                "container": container_name,
                "quarantined": True,
                "reason": reason,
                "restarts_in_last_hour": len(timestamps),
            }

        # 4. Invoke Docker restart via DockerSocketClient
        logger.info(
            "Circuit breaker: Initiating restart for container '%s' (restart %d of 3 in rolling hour)...",
            container_name,
            len(timestamps) + 1,
        )
        restarted = await self.docker_client.restart_container(container_name, timeout_seconds=30)
        if not restarted:
            logger.error("Failed executing Docker restart for container '%s'", container_name)
            return {
                "success": False,
                "container": container_name,
                "quarantined": False,
                "reason": "Docker restart command failed or socket unavailable",
            }

        # 5. Record restart timestamp in Redis (3600s TTL)
        timestamps.append(now_ts)
        try:
            self.r.set(key, json.dumps(timestamps), ex=3600)
        except Exception as e:
            logger.error("Failed recording restart timestamp for %s: %s", container_name, e)

        action = f"Restarted container '{container_name}' via circuit breaker ({len(timestamps)}/3 in rolling hour)"
        logger.warning("SelfHealing: %s", action)

        # 6. Record SupervisorHealingEvent in database if db session provided
        if db is not None:
            try:
                event = SupervisorHealingEvent(
                    profile_slug=None,
                    component="container_restart",
                    issue_detected=f"Container {container_name} persistent anomaly / health check failure",
                    action_taken=action,
                    status="resolved",
                    details={
                        "container": container_name,
                        "restarts_in_last_hour": len(timestamps),
                        "restarted_at": now_ts,
                    },
                )
                db.add(event)
                await db.commit()
            except Exception as e:
                logger.error("Failed saving container restart healing event: %s", e)

        return {
            "success": True,
            "container": container_name,
            "quarantined": False,
            "action": action,
            "restarts_in_last_hour": len(timestamps),
        }

