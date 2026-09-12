from __future__ import annotations

import datetime
import json
import logging
from typing import Any

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.supervisor import SupervisorHealingEvent, SupervisorHealthSnapshot
from xbot.supervisor.auditor import PipelineAuditor
from xbot.supervisor.healer import SelfHealingEngine
from xbot.utils.time import now_ist

logger = logging.getLogger("xbot.supervisor.manager")


class SystemSupervisor:
    """
    Unified System Manager and Self-Healing Orchestrator.
    Implements the Kubernetes-style Reconciliation Loop:
    Continuously compares Desired State vs Actual State across all XBot pipelines,
    diagnoses failures, deadlocks, and missed cadences, and automatically remediates them.
    """

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self.r = redis_client or redis.from_url(settings.REDIS_URL)
        self.auditor = PipelineAuditor(redis_client=self.r)
        self.healer = SelfHealingEngine(redis_client=self.r)

    async def reconcile(self, auto_heal: bool = True) -> dict[str, Any]:
        """
        Executes a single pass of the Reconciliation Loop:
        1. Observe & Audit: Scans all locks, queues, sessions, pipeline runs, drafts, and processes.
        2. Remediate & Self-Heal: Executes safe idempotent fixes for any diagnosed faults.
        3. Persist Telemetry: Saves healing events and system health snapshot in database & Redis.
        """
        audit_start = now_ist()
        logger.info("Supervisor: Starting system reconciliation pass (auto_heal=%s)...", auto_heal)

        async with AsyncSessionLocal() as db:
            # 1. Auditing (pre-fetch Celery active task context once for sub-second efficiency)
            celery_ctx = self.auditor.get_active_celery_context()

            lock_issues = []
            try:
                lock_issues = self.auditor.audit_redis_locks(celery_ctx=celery_ctx)
            except Exception as e:
                logger.error("Supervisor: Lock audit failed: %s", e)

            stuck_sessions = []
            try:
                stuck_sessions = await self.auditor.audit_stuck_sessions(db, celery_ctx=celery_ctx)
            except Exception as e:
                logger.error("Supervisor: Session audit failed: %s", e)

            stuck_runs = []
            try:
                stuck_runs = await self.auditor.audit_stuck_pipeline_runs(db, celery_ctx=celery_ctx)
            except Exception as e:
                logger.error("Supervisor: Pipeline run audit failed: %s", e)

            stuck_drafts = []
            try:
                stuck_drafts = await self.auditor.audit_stuck_drafts(db, celery_ctx=celery_ctx)
            except Exception as e:
                logger.error("Supervisor: Drafts audit failed: %s", e)

            cadence_issues = []
            try:
                cadence_issues = await self.auditor.audit_pipeline_cadence(db, celery_ctx=celery_ctx)
            except Exception as e:
                logger.error("Supervisor: Cadence audit failed: %s", e)

            worker_health = {"alive": True, "worker_count": 0, "workers": [], "error": None}
            try:
                worker_health = self.auditor.audit_worker_liveness()
            except Exception as e:
                logger.error("Supervisor: Worker liveness audit failed: %s", e)

            zombie_browsers = []
            try:
                zombie_browsers = self.auditor.audit_zombie_browsers(celery_ctx=celery_ctx)
            except Exception as e:
                logger.error("Supervisor: Zombie browser audit failed: %s", e)

            total_issues = (
                len(lock_issues)
                + len(stuck_sessions)
                + len(stuck_runs)
                + len(stuck_drafts)
                + len(cadence_issues)
                + (1 if not worker_health["alive"] else 0)
                + len(zombie_browsers)
            )

            healing_records: list[dict[str, Any]] = []
            orphans_cleared_count = 0

            # 2. Automated Self-Healing
            if auto_heal and total_issues > 0:
                logger.info("Supervisor: Detected %d issue(s). Executing automated self-healing...", total_issues)

                # A. Reclaim Orphan Redis Locks
                for lock in lock_issues:
                    res = self.healer.heal_orphan_lock(lock["key"], profile_slug=lock.get("profile_slug"))
                    if res.get("success"):
                        orphans_cleared_count += 1
                        event = SupervisorHealingEvent(
                            profile_slug=lock.get("profile_slug"),
                            component="redis_lock",
                            issue_detected=f"{lock['type']}: {lock['reason']}",
                            action_taken=res["action"],
                            status="resolved",
                            details=lock,
                        )
                        db.add(event)
                        healing_records.append(res)

                # B. Unstick Hung Sessions (Unblocks scheduler!)
                for sess in stuck_sessions:
                    res = await self.healer.heal_stuck_session(db, sess["session_id"])
                    if res.get("success"):
                        event = SupervisorHealingEvent(
                            profile_slug=sess.get("profile_slug"),
                            component="stuck_session",
                            issue_detected=f"Session running for {sess['runtime_minutes']}m without completion",
                            action_taken=res["action"],
                            status="resolved",
                            details=sess,
                        )
                        db.add(event)
                        healing_records.append(res)

                # C. Unstick Stalled Pipeline Runs
                for run_item in stuck_runs:
                    res = await self.healer.heal_stuck_pipeline_run(db, run_item["run_id"])
                    if res.get("success"):
                        event = SupervisorHealingEvent(
                            profile_slug=None,
                            component="pipeline_run",
                            issue_detected=f"Pipeline {run_item['pipeline_name']} stuck for {run_item['runtime_minutes']}m",
                            action_taken=res["action"],
                            status="resolved",
                            details=run_item,
                        )
                        db.add(event)
                        healing_records.append(res)

                # D. Unstick Queued Approved Drafts
                for draft in stuck_drafts:
                    res = await self.healer.heal_stuck_draft(db, draft["content_id"])
                    if res.get("success"):
                        event = SupervisorHealingEvent(
                            profile_slug=draft.get("profile_slug"),
                            component="stuck_draft",
                            issue_detected=draft["reason"],
                            action_taken=res["action"],
                            status="resolved" if not res.get("quarantined") else "warning",
                            details=draft,
                        )
                        db.add(event)
                        healing_records.append(res)

                # E. Re-dispatch Overdue Pipelines
                for cad in cadence_issues:
                    res = self.healer.heal_overdue_pipeline(
                        pipeline_name=cad["pipeline_name"],
                        profile_slug=cad.get("profile_slug"),
                    )
                    if res.get("success"):
                        event = SupervisorHealingEvent(
                            profile_slug=cad.get("profile_slug"),
                            component="overdue_pipeline",
                            issue_detected=cad["reason"],
                            action_taken=res["action"],
                            status="resolved",
                            details=cad,
                        )
                        db.add(event)
                        healing_records.append(res)

                # F. Reap Zombie Headless Chromium Processes
                if zombie_browsers:
                    pids = [z["pid"] for z in zombie_browsers]
                    res = self.healer.heal_zombie_browsers(pids)
                    if res.get("success"):
                        event = SupervisorHealingEvent(
                            profile_slug=None,
                            component="zombie_browser",
                            issue_detected=f"Found {len(pids)} zombie headless Chromium processes (>20m runtime)",
                            action_taken=res["action"],
                            status="resolved",
                            details={"pids": pids},
                        )
                        db.add(event)
                        healing_records.append(res)

                await db.commit()

            # 3. Compute System Health Status
            if not worker_health["alive"]:
                overall_status = "critical"
            elif total_issues > 0:
                overall_status = "recovering" if auto_heal else "degraded"
            else:
                overall_status = "healthy"

            # 4. Save Health Snapshot in Database
            pipelines_health = {
                "workers": worker_health,
                "lock_issues_count": len(lock_issues),
                "stuck_sessions_count": len(stuck_sessions),
                "stuck_runs_count": len(stuck_runs),
                "stuck_drafts_count": len(stuck_drafts),
                "overdue_cadences_count": len(cadence_issues),
                "zombie_browsers_count": len(zombie_browsers),
                "reconciliation_duration_ms": int((now_ist() - audit_start).total_seconds() * 1000),
            }

            snapshot = SupervisorHealthSnapshot(
                overall_status=overall_status,
                active_workers=worker_health.get("workers", []),
                stuck_tasks_count=total_issues,
                orphans_cleared_count=orphans_cleared_count,
                pipelines_health=pipelines_health,
                created_at=now_ist(),
            )
            db.add(snapshot)
            await db.commit()
            await db.refresh(snapshot)

            # 5. Cache Latest Status in Redis for instant zero-latency dashboard retrieval
            cached_status = {
                "status": overall_status,
                "timestamp": now_ist().isoformat(),
                "snapshot_id": str(snapshot.id),
                "active_workers": worker_health.get("workers", []),
                "issues_detected_count": total_issues,
                "healed_events_count": len(healing_records),
                "pipelines_health": pipelines_health,
            }
            try:
                self.r.set("xbot:supervisor:latest_health", json.dumps(cached_status), ex=300)
            except Exception:
                pass

            # 6. Emit Supervisor Liveness Heartbeat for Out-of-Band Sentinel
            try:
                self.r.set("xbot:supervisor:heartbeat", str(int(now_ist().timestamp())), ex=300)
            except Exception:
                pass

            logger.info(
                "Supervisor: Reconciliation pass complete. System is [%s]. Issues detected: %d, Fixed: %d",
                overall_status.upper(),
                total_issues,
                len(healing_records),
            )

            return {
                "status": overall_status,
                "snapshot_id": str(snapshot.id),
                "issues_count": total_issues,
                "healed_count": len(healing_records),
                "details": pipelines_health,
                "healing_actions": [r.get("action") for r in healing_records],
            }

    async def get_recent_healing_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Retrieves the latest auto-healing events from the database.
        """
        async with AsyncSessionLocal() as db:
            stmt = (
                select(SupervisorHealingEvent)
                .order_by(SupervisorHealingEvent.created_at.desc())
                .limit(limit)
            )
            res = await db.execute(stmt)
            events = res.scalars().all()
            return [
                {
                    "id": str(e.id),
                    "profile_slug": e.profile_slug,
                    "component": e.component,
                    "issue_detected": e.issue_detected,
                    "action_taken": e.action_taken,
                    "status": e.status,
                    "details": e.details,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ]

    def get_cached_health(self) -> dict[str, Any]:
        """
        Reads the latest health snapshot from Redis.
        """
        try:
            val = self.r.get("xbot:supervisor:latest_health") or self.r.get("xbot:supervisor:live_state")
            if val:
                return json.loads(val.decode("utf-8") if isinstance(val, bytes) else val)
        except Exception:
            pass
        return {"status": "unknown", "message": "No supervisor health data recorded yet."}
