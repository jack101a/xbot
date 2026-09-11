#!/usr/bin/env python3
"""
XBot Out-of-Band Supervisor Sentinel (The Watcher of the Watcher).
Runs completely decoupled from Celery and FastAPI as a lightweight OS-level guardian.
Continuously monitors:
1. Core services (Redis, Celery, FastAPI)
2. The Fixer's own heartbeat (xbot:supervisor:heartbeat)
If Celery freezes or the Fixer dies, this sentinel automatically:
- Executes an out-of-band emergency healing pass
- Revives and restarts Celery and FastAPI
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
PID_DIR = PROJECT_ROOT / ".pids"
LOG_DIR = PROJECT_ROOT / "logs"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [SENTINEL] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "sentinel.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("sentinel")


def is_pid_alive(pid_path: Path) -> bool:
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError):
        return False


def check_and_revive_services() -> None:
    """Verifies that Backend and Celery are running; revives them via xbot.sh if dead."""
    backend_alive = is_pid_alive(PID_DIR / "backend.pid")
    celery_alive = is_pid_alive(PID_DIR / "celery.pid")
    celery_browser_alive = is_pid_alive(PID_DIR / "celery_browser.pid")

    if not backend_alive or not celery_alive or not celery_browser_alive:
        logger.warning(
            "Service outage detected (Backend: %s, Celery: %s, Browser: %s). Reviving via xbot.sh...",
            backend_alive,
            celery_alive,
            celery_browser_alive,
        )
        try:
            xbot_sh = PROJECT_ROOT / "xbot.sh"
            subprocess.run([str(xbot_sh), "start"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Service revival command executed.")
        except Exception as e:
            logger.error("Failed reviving services: %s", e)


async def check_fixer_heartbeat() -> None:
    """
    Checks the Fixer's heartbeat in Redis.
    If the in-band Fixer has not checked in for > 150 seconds,
    executes an immediate out-of-band self-healing pass and restarts Celery.
    """
    import redis
    from xbot.config import settings

    try:
        r = redis.from_url(settings.REDIS_URL, socket_timeout=3.0)
        heartbeat_raw = r.get("xbot:supervisor:heartbeat")
        now_ts = int(time.time())

        is_missing_or_stale = False
        gap_seconds = 0

        if not heartbeat_raw:
            # First boot grace period: initialize heartbeat so Celery beat has time to perform its first tick
            r.set("xbot:supervisor:heartbeat", str(now_ts), ex=300)
            logger.info("Sentinel: Initialized baseline heartbeat for fresh startup (150s grace window).")
            return
        else:
            try:
                hb_ts = int(heartbeat_raw)
                gap_seconds = now_ts - hb_ts
                if gap_seconds > 150:
                    is_missing_or_stale = True
            except (ValueError, TypeError):
                is_missing_or_stale = True

        if is_missing_or_stale:
            logger.critical(
                "🚨 FIXER DEADLOCK OR CRASH DETECTED! Fixer heartbeat gap is %ds (>150s threshold).",
                gap_seconds,
            )
            logger.info("Sentinel: Initiating emergency out-of-band reconciliation & self-healing...")

            try:
                from xbot.supervisor.manager import SystemSupervisor
                supervisor = SystemSupervisor(redis_client=r)
                result = await supervisor.reconcile(auto_heal=True)
                logger.info(
                    "Sentinel: Emergency healing complete. Status: %s, Fixed: %d",
                    result.get("status"),
                    result.get("healed_count", 0),
                )
            except Exception as e:
                logger.exception("Sentinel: Emergency healing encounter: %s", e)

            # Restart Celery to unblock frozen thread pool
            logger.warning("Sentinel: Recycling frozen Celery workers...")
            xbot_sh = PROJECT_ROOT / "xbot.sh"
            subprocess.run([str(xbot_sh), "restart"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Refresh heartbeat
            r.set("xbot:supervisor:heartbeat", str(int(time.time())), ex=300)
            logger.info("Sentinel: Fixer heartbeat restored.")
        else:
            logger.debug("Fixer heartbeat healthy (gap: %ds)", gap_seconds)

    except Exception as ex:
        logger.error("Sentinel encountered error during heartbeat verification: %s", ex)


async def sentinel_loop() -> None:
    logger.info("Starting XBot Out-of-Band Supervisor Sentinel (Loop cadence: 45s)...")
    while True:
        try:
            check_and_revive_services()
            await check_fixer_heartbeat()
        except Exception as e:
            logger.error("Unexpected error in sentinel loop: %s", e)
        await asyncio.sleep(45)


if __name__ == "__main__":
    try:
        asyncio.run(sentinel_loop())
    except KeyboardInterrupt:
        logger.info("Sentinel shutting down.")
