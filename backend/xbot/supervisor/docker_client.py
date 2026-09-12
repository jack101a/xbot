from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("xbot.supervisor.docker_client")


class DockerSocketClient:
    """
    Lightweight, asynchronous Docker engine client communicating directly over
    the UNIX Domain Socket (/var/run/docker.sock) via httpx.
    Gracefully handles absence or permission issues on the Docker socket.
    """

    def __init__(
        self,
        socket_path: str = "/var/run/docker.sock",
        base_url: str = "http://docker",
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.socket_path = socket_path
        self.base_url = base_url
        self.timeout = timeout
        self._is_available = True
        self._custom_client = client is not None

        if client is not None:
            self._client = client
        else:
            try:
                transport = httpx.AsyncHTTPTransport(uds=self.socket_path)
                self._client = httpx.AsyncClient(
                    transport=transport,
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.warning("Failed initializing Docker UDS transport: %s", e)
                self._client = None
                self._is_available = False

    def is_available(self) -> bool:
        """
        Gracefully detects if the Docker socket exists and is reachable.
        """
        if not self._custom_client:
            if not self.socket_path or not os.path.exists(self.socket_path):
                return False
            if not os.access(self.socket_path, os.R_OK | os.W_OK):
                return False
        return self._is_available and self._client is not None

    async def list_containers(
        self, all: bool = True, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Lists Docker containers. GET /containers/json
        """
        if not self.is_available() or self._client is None:
            return []

        params: dict[str, Any] = {"all": "true" if all else "false"}
        if filters:
            params["filters"] = json.dumps(filters)

        try:
            resp = await self._client.get("/containers/json", params=params)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(
                "Docker list_containers returned unexpected status %d: %s",
                resp.status_code,
                resp.text[:200],
            )
            return []
        except (httpx.HTTPError, OSError) as e:
            logger.debug("Docker list_containers failed: %s", e)
            return []

    async def get_container_stats(self, id_or_name: str) -> dict[str, Any]:
        """
        Fetches container performance metrics (CPU %, true memory MB, PID count).
        GET /containers/{id_or_name}/stats?stream=false
        """
        default_result: dict[str, Any] = {
            "container_id": id_or_name,
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "memory_limit_mb": 0.0,
            "pids_current": 0,
        }
        if not self.is_available() or self._client is None:
            return default_result

        try:
            resp = await self._client.get(f"/containers/{id_or_name}/stats", params={"stream": "false"})
            if resp.status_code != 200:
                logger.warning("Docker get_container_stats for %s failed with status %d", id_or_name, resp.status_code)
                return default_result

            data = resp.json()

            # 1. CPU Percentage Calculation
            cpu_stats = data.get("cpu_stats", {})
            precpu_stats = data.get("precpu_stats", {})
            cpu_usage = cpu_stats.get("cpu_usage", {})
            precpu_usage = precpu_stats.get("cpu_usage", {})

            cpu_delta = cpu_usage.get("total_usage", 0) - precpu_usage.get("total_usage", 0)
            system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get("system_cpu_usage", 0)

            online_cpus = cpu_stats.get("online_cpus")
            if not online_cpus:
                percpu = cpu_usage.get("percpu_usage") or []
                online_cpus = len(percpu) if percpu else 1

            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta >= 0:
                cpu_percent = round((cpu_delta / system_delta) * online_cpus * 100.0, 2)

            # 2. True Memory Calculation (accounting for cgroups v1 and v2)
            mem_stats = data.get("memory_stats", {})
            stats_detail = mem_stats.get("stats", {})

            raw_usage = mem_stats.get("usage", 0)
            # Inactive file memory (page cache that can be reclaimed)
            inactive_file = stats_detail.get(
                "inactive_file",
                stats_detail.get("total_inactive_file", 0),
            )
            # Anonymous memory (active RSS)
            anon_mem = stats_detail.get(
                "anon",
                stats_detail.get("total_inactive_anon", 0),
            )

            if anon_mem and anon_mem > 0:
                mem_bytes = anon_mem
            elif raw_usage > 0:
                mem_bytes = max(0, raw_usage - inactive_file)
            else:
                mem_bytes = 0

            memory_mb = round(mem_bytes / (1024 * 1024), 2)
            limit_bytes = mem_stats.get("limit", 0)
            memory_limit_mb = round(limit_bytes / (1024 * 1024), 2)

            # 3. PIDs current
            pids_stats = data.get("pids_stats", {})
            pids_current = pids_stats.get("current", 0)

            return {
                "container_id": id_or_name,
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "memory_limit_mb": memory_limit_mb,
                "pids_current": pids_current,
            }
        except (httpx.HTTPError, OSError) as e:
            logger.debug("Failed getting stats for container %s: %s", id_or_name, e)
            default_result["error"] = str(e)
            return default_result

    async def get_container_top(
        self, id_or_name: str, ps_args: str = "aux"
    ) -> list[dict[str, str]]:
        """
        Fetches running processes inside the container.
        GET /containers/{id_or_name}/top?ps_args={ps_args}
        Returns list of process dictionaries (PID, %CPU, %MEM, COMMAND, etc.).
        """
        if not self.is_available() or self._client is None:
            return []

        try:
            resp = await self._client.get(
                f"/containers/{id_or_name}/top",
                params={"ps_args": ps_args},
            )
            if resp.status_code != 200:
                return []

            top_data = resp.json()
            titles = top_data.get("Titles", [])
            processes = top_data.get("Processes", [])

            procs: list[dict[str, str]] = []
            for row in processes:
                if len(row) == len(titles):
                    procs.append(dict(zip(titles, row, strict=False)))
                else:
                    # Fallback if length differs
                    procs.append({titles[i] if i < len(titles) else f"col_{i}": val for i, val in enumerate(row)})
            return procs
        except (httpx.HTTPError, OSError) as e:
            logger.debug("Failed getting top for container %s: %s", id_or_name, e)
            return []

    async def restart_container(
        self, id_or_name: str, timeout_seconds: int = 30
    ) -> bool:
        """
        Restarts a container. POST /containers/{id_or_name}/restart?t={timeout_seconds}
        Returns True on 204 or 200, False otherwise.
        """
        if not self.is_available() or self._client is None:
            return False

        try:
            resp = await self._client.post(
                f"/containers/{id_or_name}/restart",
                params={"t": timeout_seconds},
                timeout=timeout_seconds + 10.0,
            )
            return resp.status_code in (200, 204)
        except (httpx.HTTPError, OSError) as e:
            logger.error("Failed restarting container %s: %s", id_or_name, e)
            return False

    async def close(self) -> None:
        """
        Closes the underlying httpx client transport.
        """
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception as e:
                logger.debug("Error closing DockerSocketClient: %s", e)
