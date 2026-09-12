from __future__ import annotations

import logging
from typing import Any

import redis
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.safety.guard.drain_lock import is_daily_post_limit_drained
from xbot.supervisor.auditor import PipelineAuditor

logger = logging.getLogger("xbot.supervisor.tier3_business")


class BusinessLogicHealthTier:
    """
    Tier 3 Health Inspector: Business Logic and Pipeline Workflow State.
    Monitors database session states, pipeline execution cadences, and approved draft
    publishing progress while respecting platform daily limits.
    """

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        auditor: PipelineAuditor | None = None,
    ) -> None:
        self.r = redis_client or redis.from_url(settings.REDIS_URL)
        self.auditor = auditor or PipelineAuditor(redis_client=self.r)

    async def audit_drafts(self, db: AsyncSession) -> list[dict[str, Any]]:
        """
        Audits pending/approved drafts for stuck states.
        CRITICAL SAFEGUARD:
        If `xbot:limits:daily_post_limit_drained` lock is active (globally or for the profile),
        alerts are suppressed and reported as a clean limit hold.
        """
        findings: list[dict[str, Any]] = []

        # Check global daily post limit drain lock
        if self.r.exists("xbot:limits:daily_post_limit_drained"):
            findings.append({
                "level": "INFO",
                "tier": 3,
                "component": "draft",
                "message": "Clean limit hold: global daily post limit drain lock is active",
                "action_needed": "none",
            })
            return findings

        try:
            stuck_drafts = await self.auditor.audit_stuck_drafts(db)
            for draft in stuck_drafts:
                slug = draft.get("profile_slug", "")

                # Check if profile-specific daily post limit is drained
                if slug and (
                    is_daily_post_limit_drained(self.r, slug)
                    or self.r.exists(f"xbot:limits:daily_post_limit_drained:{slug}")
                ):
                    findings.append({
                        "level": "INFO",
                        "tier": 3,
                        "component": "draft",
                        "content_id": draft["content_id"],
                        "profile_slug": slug,
                        "message": f"Clean limit hold: daily post limit drained for profile @{slug}",
                        "action_needed": "none",
                    })
                else:
                    findings.append({
                        "level": "WARNING",
                        "tier": 3,
                        "component": "stuck_draft",
                        "content_id": draft["content_id"],
                        "profile_slug": slug,
                        "reason": draft.get("reason"),
                        "action_needed": "soft_heal",
                        "message": f"Stuck approved draft {draft['content_id']} for @{slug}",
                    })
        except Exception as e:
            logger.error("Failed auditing drafts in Tier 3: %s", e)

        return findings

    async def audit_stuck_sessions(self, db: AsyncSession) -> list[dict[str, Any]]:
        """
        Audits database sessions stuck in RUNNING status > 35 minutes.
        """
        findings: list[dict[str, Any]] = []
        try:
            stuck = await self.auditor.audit_stuck_sessions(db, threshold_minutes=35)
            for sess in stuck:
                findings.append({
                    "level": "WARNING",
                    "tier": 3,
                    "component": "stuck_session",
                    "session_id": sess["session_id"],
                    "profile_slug": sess.get("profile_slug"),
                    "runtime_minutes": sess.get("runtime_minutes"),
                    "reason": sess.get("reason"),
                    "action_needed": "soft_heal",
                    "message": f"Stuck session {sess['session_id']} for @{sess.get('profile_slug')} ({sess.get('runtime_minutes')}m)",
                })
        except Exception as e:
            logger.error("Failed auditing stuck sessions in Tier 3: %s", e)

        return findings

    async def audit_stuck_pipeline_runs(self, db: AsyncSession) -> list[dict[str, Any]]:
        """
        Audits PipelineRun records stuck in running status > 25 minutes.
        """
        findings: list[dict[str, Any]] = []
        try:
            stuck_runs = await self.auditor.audit_stuck_pipeline_runs(db, threshold_minutes=25)
            for r in stuck_runs:
                findings.append({
                    "level": "WARNING",
                    "tier": 3,
                    "component": "stuck_pipeline_run",
                    "run_id": r["run_id"],
                    "pipeline_name": r.get("pipeline_name"),
                    "runtime_minutes": r.get("runtime_minutes"),
                    "reason": r.get("reason"),
                    "action_needed": "soft_heal",
                    "message": f"Stuck pipeline run '{r.get('pipeline_name')}' ({r.get('runtime_minutes')}m)",
                })
        except Exception as e:
            logger.error("Failed auditing stuck pipeline runs in Tier 3: %s", e)

        return findings

    async def audit_business(self, db: AsyncSession) -> list[dict[str, Any]]:
        """
        Runs the full Tier 3 inspection suite across drafts, sessions, and pipeline runs.
        """
        findings: list[dict[str, Any]] = []
        findings.extend(await self.audit_drafts(db))
        findings.extend(await self.audit_stuck_sessions(db))
        findings.extend(await self.audit_stuck_pipeline_runs(db))
        return findings
