from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from typing import Any

import redis

from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.supervisor import SupervisorHealingEvent, SupervisorHealthSnapshot
from xbot.supervisor.docker_client import DockerSocketClient
from xbot.supervisor.healer import SelfHealingEngine
from xbot.supervisor.tiers.tier1_container import ContainerHealthTier
from xbot.supervisor.tiers.tier2_middleware import MiddlewareHealthTier
from xbot.supervisor.tiers.tier3_business import BusinessLogicHealthTier
from xbot.utils.time import now_ist

logger = logging.getLogger("xbot.supervisor.sentinel")


class SentinelDaemon:
    """
    Dedicated Autonomous Sentinel Container Daemon.
    Performs out-of-band, multi-tiered continuous observation and remediation
    across the entire XBot operational stack:
      - Tier 1: Container-level runtime (Docker stats, sustained CPU, memory leaks, Chrome processes)
      - Tier 2: Middleware & broker runtime (Celery workers, Redis queues, distributed locks)
      - Tier 3: Business logic & pipeline state (stuck sessions, pipelines, approved drafts, limit holds)
    
    Executes progressive 3-level escalation:
      - Level 1: Warning log & Redis incident counter
      - Level 2: Soft heal (revoke hung task, clear orphan lock, fail stuck DB session)
      - Level 3: Container restart via anti-flapping circuit breaker if anomaly persists for >= 3 ticks
    """

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        docker_client: DockerSocketClient | None = None,
        check_interval: float = 30.0,
    ) -> None:
        self.r = redis_client or redis.from_url(settings.REDIS_URL)
        self.docker_client = docker_client or DockerSocketClient()
        self.check_interval = check_interval

        # Multi-tier health inspectors
        self.tier1 = ContainerHealthTier(docker_client=self.docker_client)
        self.tier2 = MiddlewareHealthTier(redis_client=self.r)
        self.tier3 = BusinessLogicHealthTier(redis_client=self.r)

        # Self-healing engine with Docker integration
        self.healer = SelfHealingEngine(redis_client=self.r, docker_client=self.docker_client)

        self._running = False
        self._last_db_snapshot_ts = 0.0
        self._anomaly_persistence: dict[str, int] = {}

    def setup_signal_handlers(self) -> None:
        """
        Registers graceful shutdown handlers for SIGINT and SIGTERM.
        """
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self.stop)
        except (NotImplementedError, RuntimeError):
            # Fallback for non-main thread or Windows/unsupported platforms
            signal.signal(signal.SIGINT, lambda *_: self.stop())
            signal.signal(signal.SIGTERM, lambda *_: self.stop())

    def stop(self) -> None:
        """
        Signals the daemon loop to terminate gracefully.
        """
        logger.info("SentinelDaemon: Shutdown signal received. Halting loop...")
        self._running = False

    def _build_anomaly_key(self, finding: dict[str, Any]) -> str:
        """
        Constructs a unique tracking key for an anomaly to monitor persistence across ticks.
        """
        tier = finding.get("tier", 0)
        component = finding.get("component") or finding.get("container") or finding.get("metric") or "unknown"
        identifier = (
            finding.get("lock_key")
            or finding.get("session_id")
            or finding.get("run_id")
            or finding.get("content_id")
            or finding.get("worker")
            or finding.get("queue")
            or finding.get("metric")
            or "default"
        )
        return f"t{tier}:{component}:{identifier}"

    async def run_tick(self) -> dict[str, Any]:
        """
        Executes a single inspection, progressive escalation, and state sync tick.
        """
        tick_start = now_ist()
        logger.debug("SentinelDaemon: Executing 3-tier inspection tick at %s...", tick_start.isoformat())

        async with AsyncSessionLocal() as db:
            # 1. Gather multi-tier findings
            tier1_findings = await self.tier1.audit_containers()
            tier2_findings = await self.tier2.audit_middleware()
            tier3_findings = await self.tier3.audit_business(db)

            all_findings = tier1_findings + tier2_findings + tier3_findings

            # Separate findings by severity
            active_anomalies = [
                f for f in all_findings if f.get("level") in ("WARNING", "CRITICAL")
            ]
            current_keys = set()
            healed_actions: list[str] = []

            # 2. Progressive Escalation Handling
            for finding in active_anomalies:
                anomaly_key = self._build_anomaly_key(finding)
                current_keys.add(anomaly_key)

                # Increment persistence count
                consecutive_ticks = self._anomaly_persistence.get(anomaly_key, 0) + 1
                self._anomaly_persistence[anomaly_key] = consecutive_ticks

                level = finding.get("level", "WARNING")
                action_needed = finding.get("action_needed", "none")

                # Level 1: Warning log & Redis incident counter
                incident_redis_key = f"xbot:sentinel:incidents:{anomaly_key}"
                try:
                    self.r.incr(incident_redis_key)
                    self.r.expire(incident_redis_key, 86400)
                except Exception:
                    pass

                logger.warning(
                    "Sentinel Anomaly [Level 1] [%s] %s: %s (persistence: %d ticks)",
                    level,
                    anomaly_key,
                    finding.get("message", "Anomaly detected"),
                    consecutive_ticks,
                )

                # Level 2: Soft Heal (executed when action_needed is soft_heal)
                if action_needed == "soft_heal":
                    comp = finding.get("component")
                    heal_res: dict[str, Any] | None = None

                    if comp == "redis_lock" and "lock_key" in finding:
                        heal_res = self.healer.heal_orphan_lock(
                            finding["lock_key"],
                            profile_slug=finding.get("profile_slug"),
                        )
                    elif comp == "stuck_session" and "session_id" in finding:
                        heal_res = await self.healer.heal_stuck_session(db, finding["session_id"])
                    elif comp == "stuck_pipeline_run" and "run_id" in finding:
                        heal_res = await self.healer.heal_stuck_pipeline_run(db, finding["run_id"])
                    elif comp == "stuck_draft" and "content_id" in finding:
                        heal_res = await self.healer.heal_stuck_draft(db, finding["content_id"])

                    if heal_res and heal_res.get("success"):
                        healed_actions.append(heal_res.get("action", str(heal_res)))
                        event = SupervisorHealingEvent(
                            profile_slug=finding.get("profile_slug"),
                            component=comp or "soft_heal",
                            issue_detected=finding.get("message") or finding.get("reason") or "Soft-heal anomaly",
                            action_taken=heal_res.get("action", "Remediated"),
                            status="resolved",
                            details=finding,
                        )
                        db.add(event)
                        await db.commit()

                # Level 3: Container Restart via Circuit Breaker (if anomaly persists >= 3 ticks)
                if consecutive_ticks >= 3:
                    target_container: str | None = None

                    # Check if finding explicitly targets a container
                    if finding.get("container"):
                        target_container = finding["container"]
                    elif finding.get("component") == "celery_worker":
                        worker_node = finding.get("worker", "")
                        if "browser" in worker_node:
                            target_container = "browser-worker"
                        else:
                            target_container = "worker"
                    elif finding.get("metric") == "chrome":
                        target_container = "browser-worker"
                    elif finding.get("component") == "redis_queue" and finding.get("action_needed") == "restart_container":
                        q = finding.get("queue", "")
                        if q in ("celery", "publish"):
                            target_container = "worker"
                        elif q == "browser":
                            target_container = "browser-worker"

                    if target_container:
                        logger.warning(
                            "Sentinel Escalation [Level 3]: Anomaly '%s' persisted for %d ticks. "
                            "Triggering container restart via circuit breaker for '%s'...",
                            anomaly_key,
                            consecutive_ticks,
                            target_container,
                        )
                        restart_res = await self.healer.restart_container_with_circuit_breaker(
                            container_name=target_container,
                            db=db,
                        )
                        if restart_res.get("success"):
                            healed_actions.append(restart_res.get("action", f"Restarted {target_container}"))
                            # Reset persistence counter following successful restart trigger
                            self._anomaly_persistence[anomaly_key] = 0
                            # Clear queue stall marker in Redis if it was a queue stall
                            if finding.get("component") == "redis_queue" and "queue" in finding:
                                try:
                                    self.r.delete(f"xbot:sentinel:queue_stall:{finding['queue']}")
                                except Exception:
                                    pass

            # Prune resolved anomalies from persistence tracker
            for k in list(self._anomaly_persistence.keys()):
                if k not in current_keys:
                    del self._anomaly_persistence[k]

            # 3. Overall System Health Computation
            has_critical = any(f.get("level") == "CRITICAL" for f in all_findings)
            has_warning = any(f.get("level") == "WARNING" for f in all_findings)

            if has_critical:
                overall_status = "critical"
            elif has_warning:
                overall_status = "recovering" if healed_actions else "degraded"
            else:
                overall_status = "healthy"

            # 4. Live Health State Cache in Redis
            live_state = {
                "status": overall_status,
                "timestamp": now_ist().isoformat(),
                "check_interval": self.check_interval,
                "tier1": tier1_findings,
                "tier2": tier2_findings,
                "tier3": tier3_findings,
                "active_anomalies_count": len(active_anomalies),
                "healed_actions_count": len(healed_actions),
                "actions_taken": healed_actions,
            }
            try:
                # Store live_state with 120s TTL
                self.r.set("xbot:supervisor:live_state", json.dumps(live_state), ex=120)
                # Keep latest_health updated for backward compatibility with manager.py and API routes
                self.r.set("xbot:supervisor:latest_health", json.dumps(live_state), ex=300)
                # Keep heartbeat updated
                self.r.set("xbot:supervisor:heartbeat", str(int(now_ist().timestamp())), ex=300)
            except Exception as e:
                logger.error("Failed saving live state to Redis: %s", e)

            # 5. Periodic SQLite Health Snapshot (every 5 minutes / 300s)
            now_epoch = time.time()
            if now_epoch - self._last_db_snapshot_ts >= 300:
                try:
                    snapshot = SupervisorHealthSnapshot(
                        overall_status=overall_status,
                        active_workers=[],
                        stuck_tasks_count=len(active_anomalies),
                        orphans_cleared_count=len(healed_actions),
                        pipelines_health=live_state,
                        created_at=now_ist(),
                    )
                    db.add(snapshot)
                    await db.commit()
                    self._last_db_snapshot_ts = now_epoch
                    logger.debug("SentinelDaemon: Persisted 5-minute SupervisorHealthSnapshot to SQLite")
                except Exception as e:
                    logger.error("Failed persisting SupervisorHealthSnapshot to SQLite: %s", e)

            logger.info(
                "SentinelDaemon: Tick pass complete. Status: [%s]. Anomalies: %d, Remediations: %d",
                overall_status.upper(),
                len(active_anomalies),
                len(healed_actions),
            )

            return {
                "status": overall_status,
                "tier1_findings": tier1_findings,
                "tier2_findings": tier2_findings,
                "tier3_findings": tier3_findings,
                "anomalies_count": len(active_anomalies),
                "healed_actions": healed_actions,
            }

    async def start(self) -> None:
        """
        Starts the continuous autonomous sentinel daemon loop.
        """
        self._running = True
        self.setup_signal_handlers()
        logger.info(
            "SentinelDaemon: Autonomous sentinel daemon started (interval=%.1fs). Ready.",
            self.check_interval,
        )

        while self._running:
            try:
                await self.run_tick()
            except Exception as e:
                logger.error("SentinelDaemon: Error encountered during reconciliation tick: %s", e, exc_info=True)

            # Responsive sleep loop checking self._running periodically
            sleep_elapsed = 0.0
            while self._running and sleep_elapsed < self.check_interval:
                await asyncio.sleep(min(0.5, self.check_interval - sleep_elapsed))
                sleep_elapsed += 0.5

        logger.info("SentinelDaemon: Loop terminated. Performing graceful shutdown...")
        await self.close()

    async def close(self) -> None:
        """
        Closes underlying client transports.
        """
        if self.docker_client:
            await self.docker_client.close()


async def run_sentinel_daemon(check_interval: float = 30.0) -> None:
    """
    Convenience entrypoint for launching the Sentinel daemon process.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    daemon = SentinelDaemon(check_interval=check_interval)
    await daemon.start()


if __name__ == "__main__":
    asyncio.run(run_sentinel_daemon())
