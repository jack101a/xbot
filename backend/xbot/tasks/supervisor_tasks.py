from __future__ import annotations

import asyncio
import logging
from typing import Any

from xbot.celery_app import celery_app
from xbot.supervisor.manager import SystemSupervisor

logger = logging.getLogger("xbot.tasks.supervisor")


@celery_app.task(name="xbot.tasks.supervisor_tasks.run_supervisor_watchdog")
def run_supervisor_watchdog(auto_heal: bool = True) -> dict[str, Any]:
    """
    Continuous Supervisor Watchdog Task (runs every 60 seconds).
    Audits queues, locks, sessions, pipeline runs, drafts, and browser processes.
    Reconciles actual state against desired state and executes automated self-healing.
    """
    logger.info("Supervisor Watchdog: Executing periodic health audit & self-healing pass...")
    supervisor = SystemSupervisor()
    try:
        result = asyncio.run(supervisor.reconcile(auto_heal=auto_heal))
        logger.info(
            "Supervisor Watchdog: Pass complete. Status: %s. Issues detected: %d, Healed: %d",
            result.get("status"),
            result.get("issues_count", 0),
            result.get("healed_count", 0),
        )
        return result
    except Exception as e:
        logger.exception("Supervisor Watchdog encountered an unexpected error: %s", e)
        return {"status": "error", "error": str(e)}
