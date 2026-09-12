from __future__ import annotations

import logging
from typing import Any

from xbot.supervisor.docker_client import DockerSocketClient

logger = logging.getLogger("xbot.supervisor.tier1_container")


class ContainerHealthTier:
    """
    Tier 1 Health Inspector: Container-Level Runtime Inspection.
    Monitors Docker containers for memory leaks, CPU thrashing, and defunct processes.
    Target containers: worker, browser-worker, backend, redis.
    """

    DEFAULT_TARGET_PATTERNS = ["worker", "browser-worker", "backend", "redis"]

    def __init__(
        self,
        docker_client: DockerSocketClient | None = None,
        target_patterns: list[str] | None = None,
    ) -> None:
        self.docker_client = docker_client or DockerSocketClient()
        self.target_patterns = target_patterns or self.DEFAULT_TARGET_PATTERNS
        self._cpu_high_counts: dict[str, int] = {}

    def _determine_container_thresholds(self, name: str) -> tuple[str, float]:
        """
        Determines the role and memory warning threshold (MB) for a container.
        """
        name_lower = name.lower()
        if "browser" in name_lower:
            return "browser-worker", 800.0
        elif "worker" in name_lower:
            return "worker", 600.0
        elif "backend" in name_lower:
            return "backend", 800.0
        elif "redis" in name_lower:
            return "redis", 64.0
        return "other", 800.0

    async def audit_containers(self) -> list[dict[str, Any]]:
        """
        Audits running containers against memory, sustained CPU, and chrome process thresholds.
        Emits structured findings with severity levels and suggested remediation actions.
        """
        findings: list[dict[str, Any]] = []

        if not self.docker_client.is_available():
            logger.info("Docker socket not available; skipping container-level inspection.")
            return [
                {
                    "level": "INFO",
                    "tier": 1,
                    "message": "Docker socket not available (non-container mode)",
                }
            ]

        containers = await self.docker_client.list_containers(all=True)
        if not containers:
            return findings

        for c in containers:
            names = c.get("Names") or []
            if not names:
                continue
            container_name = names[0].lstrip("/")

            # Ensure we do not audit third-party containers (e.g. immich_redis or paperless-broker)
            is_xbot_related = (
                "xbot" in container_name.lower()
                or container_name in ("redis", "worker", "browser-worker", "backend")
                or container_name.startswith(("worker", "browser-worker", "backend", "redis"))
            )
            if not is_xbot_related:
                continue

            # Check if container matches target stack patterns
            if not any(pattern in container_name for pattern in self.target_patterns):
                continue

            state = c.get("State", "").lower()
            if state != "running":
                findings.append({
                    "level": "CRITICAL",
                    "tier": 1,
                    "container": container_name,
                    "metric": "status",
                    "value": state,
                    "action_needed": "restart_container",
                    "message": f"Container '{container_name}' is not running (state: {state})",
                })
                continue

            role, mem_threshold = self._determine_container_thresholds(container_name)

            # 1. Fetch container stats
            stats = await self.docker_client.get_container_stats(container_name)
            mem_mb = stats.get("memory_mb", 0.0)
            cpu_pct = stats.get("cpu_percent", 0.0)

            # Check Memory Threshold
            if mem_mb > mem_threshold:
                level = "CRITICAL" if mem_mb > (mem_threshold * 1.25) else "WARNING"
                findings.append({
                    "level": level,
                    "tier": 1,
                    "container": container_name,
                    "metric": "memory",
                    "value": mem_mb,
                    "threshold": mem_threshold,
                    "action_needed": "restart_container",
                    "message": f"Container '{container_name}' memory {mem_mb} MB exceeds threshold {mem_threshold} MB",
                })

            # Check Sustained CPU > 95%
            if cpu_pct > 95.0:
                count = self._cpu_high_counts.get(container_name, 0) + 1
                self._cpu_high_counts[container_name] = count
                findings.append({
                    "level": "CRITICAL" if count >= 3 else "WARNING",
                    "tier": 1,
                    "container": container_name,
                    "metric": "cpu",
                    "value": cpu_pct,
                    "sustained_ticks": count,
                    "action_needed": "restart_container" if count >= 3 else "soft_heal",
                    "message": f"Container '{container_name}' CPU usage {cpu_pct}% > 95% (sustained {count} ticks)",
                })
            else:
                self._cpu_high_counts[container_name] = 0

            # 2. Check Chrome processes for browser-worker
            if role == "browser-worker":
                top_procs = await self.docker_client.get_container_top(container_name)
                chrome_count = 0
                defunct_count = 0

                for proc in top_procs:
                    cmd = (proc.get("COMMAND") or proc.get("CMD") or "").lower()
                    stat = (proc.get("STAT") or proc.get("S") or "").upper()
                    is_chrome = "chrome" in cmd or "chromium" in cmd

                    if is_chrome:
                        chrome_count += 1
                        if "defunct" in cmd or stat.startswith("Z"):
                            defunct_count += 1
                    elif "defunct" in cmd or stat.startswith("Z"):
                        defunct_count += 1

                if chrome_count > 6 or defunct_count > 0:
                    level = "CRITICAL" if (chrome_count > 10 or defunct_count > 2) else "WARNING"
                    findings.append({
                        "level": level,
                        "tier": 1,
                        "container": container_name,
                        "metric": "chrome",
                        "value": chrome_count,
                        "defunct_count": defunct_count,
                        "action_needed": "restart_container" if chrome_count > 8 else "soft_heal",
                        "message": f"Container '{container_name}' has {chrome_count} Chrome processes ({defunct_count} defunct)",
                    })

        return findings
