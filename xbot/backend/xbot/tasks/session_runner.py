"""
Session Runner Facade.
Orchestrates end-to-end browser session lifecycle:
1. Profile validation & database session initialization
2. Feed & opportunity snapshot gathering (session_feed_scanner)
3. AI session planning & action dispatch (session_executor)
4. Post-execution reciprocity audit & integrity checks (session_metrics)
5. Telemetry wrap-up and post-session monologues (session_wrapup)
"""

from __future__ import annotations

import datetime
import logging
from typing import Any
import uuid

from sqlalchemy import select

import xbot.tasks as tasks
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Session, SessionStatus
from xbot.tasks.session_executor import execute_planned_actions
from xbot.tasks.session_feed_scanner import scan_session_feed
from xbot.tasks.session_metrics import (
    audit_and_prune_misaligned_actions,
    audit_reciprocity_and_prune,
    clean_temp_storage_and_logs,
)
from xbot.tasks.session_wrapup import (
    finalize_session,
    handle_session_abort,
    handle_session_failure,
)

logger = logging.getLogger("xbot.tasks.session_runner")


async def _run_session_async(profile_id_str: str) -> dict[str, Any]:
    """Runs a complete autonomous session for a given profile."""
    profile_id = uuid.UUID(profile_id_str)

    async with tasks.AsyncSessionLocal() as db:
        # 1. Fetch Profile
        stmt = select(Profile).where(Profile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found."}

        if profile.status in (ProfileStatus.PAUSED, ProfileStatus.LOCKED, ProfileStatus.SUSPENDED):
            return {"status": "ignored", "reason": f"Profile status is {profile.status}."}

        profile_slug = profile.profile_slug

        # 2. Create Session DB record
        session = Session(
            profile_id=profile_id,
            status=SessionStatus.RUNNING,
            started_at=datetime.datetime.utcnow(),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        tasks.broadcast_session_log(session.id, "session_start", {"profile_slug": profile_slug})

        # 3. Open Browser, Scrape Feed Snapshot
        manager = tasks.BrowserManager()
        await manager.start()

        # Lock check
        if not manager.acquire_lock(profile_slug):
            session.status = SessionStatus.FAILED
            session.error_log = "Could not acquire Redis browser lock."
            session.ended_at = datetime.datetime.utcnow()
            await db.commit()
            await manager.stop()
            return {"status": "failed", "error": "Redis browser lock collision."}

        context = None
        page = None
        try:
            config = tasks.load_config(manager.base_profile_dir / profile_slug)
            persona = tasks.load_persona(manager.base_profile_dir / profile_slug)
            is_mock = getattr(config, "mock_mode", False)

            if not is_mock:
                proxy_url = getattr(config, "proxy_url", None)
                schedule_cfg = getattr(config, "schedule", None)
                timezone_str = getattr(schedule_cfg, "timezone", "America/New_York") if schedule_cfg else "America/New_York"

                context = await manager.get_context(
                    profile_slug=profile_slug,
                    timezone=timezone_str,
                    proxy_url=proxy_url,
                )
                page = await context.new_page()

            # Feed & Opportunity snapshot
            feed_snapshot = await scan_session_feed(
                page=page,
                profile_id=profile_id,
                profile_slug=profile_slug,
                persona=persona,
                manager=manager,
                config=config,
                db=db,
                is_mock=is_mock,
                session_id=session.id,
            )

            # 4. Generate AI session plan
            plan = await tasks.plan_session(
                db=db,
                profile_slug=profile_slug,
                feed_snapshot=feed_snapshot,
                base_profile_dir=str(manager.base_profile_dir),
            )

            session.plan = plan.model_dump()
            await db.commit()

            tasks.broadcast_session_log(session.id, "session_planned", {
                "actions_count": len(plan.actions),
                "plan": plan.model_dump(),
            })

            if plan.skip_reason:
                return await handle_session_abort(db, session, plan.skip_reason)

            # 5. Execute planned actions
            actions_planned = plan.actions
            session.actions_planned = len(actions_planned)
            await db.commit()

            completed, failed = await execute_planned_actions(
                db=db,
                session=session,
                profile=profile,
                actions_planned=actions_planned,
                page=page,
                manager=manager,
                config=config,
                persona=persona,
                is_mock=is_mock,
            )

            # 6. Reciprocity audits & Misalignment pruning
            await audit_reciprocity_and_prune(db, profile_id, profile_slug, session.id, page, is_mock)
            await audit_and_prune_misaligned_actions(db, profile_id, page, is_mock)
            clean_temp_storage_and_logs()

            # 7. Finalize stats & post-session processing
            return await finalize_session(
                db=db,
                session=session,
                profile_slug=profile_slug,
                completed=completed,
                failed=failed,
                base_profile_dir=str(manager.base_profile_dir),
            )

        except Exception as ex:
            return await handle_session_failure(db, session, str(ex), profile_slug)

        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            manager.release_lock(profile_slug)
            await manager.stop()


__all__ = [
    "_run_session_async",
    "scan_session_feed",
    "execute_planned_actions",
    "audit_reciprocity_and_prune",
    "audit_and_prune_misaligned_actions",
    "clean_temp_storage_and_logs",
    "finalize_session",
    "handle_session_abort",
    "handle_session_failure",
]
