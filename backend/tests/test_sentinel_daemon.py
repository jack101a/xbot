from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xbot.supervisor.docker_client import DockerSocketClient
from xbot.supervisor.healer import SelfHealingEngine
from xbot.supervisor.sentinel import SentinelDaemon
from xbot.supervisor.tiers.tier1_container import ContainerHealthTier
from xbot.supervisor.tiers.tier2_middleware import MiddlewareHealthTier
from xbot.supervisor.tiers.tier3_business import BusinessLogicHealthTier


class MockRedis:
    """Mock Redis client providing standard dictionary-backed key/value & TTL operations."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self.ttls: dict[str, int] = {}

    def exists(self, key: str) -> int:
        return 1 if key in self.store else 0

    def get(self, key: str) -> str | bytes | None:
        return self.store.get(key)

    def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    def ttl(self, key: str) -> int:
        if key not in self.store:
            return -2
        return self.ttls.get(key, -1)

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                self.ttls.pop(k, None)
                count += 1
        return count

    def incr(self, key: str) -> int:
        val = int(self.store.get(key, 0)) + 1
        self.store[key] = str(val)
        return val

    def expire(self, key: str, ex: int) -> bool:
        if key in self.store:
            self.ttls[key] = ex
            return True
        return False

    def llen(self, key: str) -> int:
        val = self.store.get(key, [])
        if isinstance(val, list):
            return len(val)
        return int(val) if isinstance(val, (int, str)) and str(val).isdigit() else 0

    def keys(self, pattern: str) -> list[str]:
        # Basic prefix pattern matching
        prefix = pattern.rstrip("*")
        return [k for k in self.store if k.startswith(prefix)]


# =========================================================================
# 1. DockerSocketClient Tests
# =========================================================================

@pytest.mark.asyncio
async def test_docker_socket_client_nonexistent():
    """Verify DockerSocketClient gracefully handles non-existent docker socket."""
    client = DockerSocketClient(socket_path="/nonexistent/docker.sock")
    assert client.is_available() is False

    # All operations should gracefully return safe fallbacks without exceptions
    containers = await client.list_containers()
    assert containers == []

    stats = await client.get_container_stats("test-container")
    assert stats["cpu_percent"] == 0.0
    assert stats["memory_mb"] == 0.0
    assert stats["pids_current"] == 0

    top = await client.get_container_top("test-container")
    assert top == []

    restarted = await client.restart_container("test-container")
    assert restarted is False

    await client.close()


@pytest.mark.asyncio
async def test_docker_socket_stats_calculation():
    """Verify DockerSocketClient accurately calculates CPU % and RSS memory MB from stats payload."""
    mock_http = AsyncMock()

    # Raw Docker stats payload
    stats_payload = {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 400_000_000, "percpu_usage": [200_000_000, 200_000_000]},
            "system_cpu_usage": 2_000_000_000,
            "online_cpus": 2,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 200_000_000},
            "system_cpu_usage": 1_000_000_000,
        },
        "memory_stats": {
            "usage": 524_288_000,  # 500 MB
            "limit": 1_073_741_824,  # 1024 MB
            "stats": {
                "inactive_file": 104_857_600,  # 100 MB inactive cache
                "anon": 419_430_400,  # 400 MB anon RSS
            },
        },
        "pids_stats": {
            "current": 18,
        },
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = stats_payload
    mock_http.get.return_value = mock_resp

    client = DockerSocketClient(client=mock_http)
    assert client.is_available() is True

    stats = await client.get_container_stats("worker")
    # cpu: (200M / 1000M) * 2 * 100 = 40.0%
    assert stats["cpu_percent"] == 40.0
    # memory: anon is 419430400 = 400 MB
    assert stats["memory_mb"] == 400.0
    assert stats["memory_limit_mb"] == 1024.0
    assert stats["pids_current"] == 18


@pytest.mark.asyncio
async def test_docker_socket_top_and_restart():
    """Verify get_container_top processes rows and restart_container returns boolean."""
    mock_http = AsyncMock()

    top_payload = {
        "Titles": ["PID", "%CPU", "COMMAND"],
        "Processes": [
            ["1001", "1.5", "celery worker -A xbot"],
            ["1002", "12.0", "/opt/google/chrome/chrome --headless"],
        ],
    }
    top_resp = MagicMock()
    top_resp.status_code = 200
    top_resp.json.return_value = top_payload

    restart_resp = MagicMock()
    restart_resp.status_code = 204

    mock_http.get.return_value = top_resp
    mock_http.post.return_value = restart_resp

    client = DockerSocketClient(client=mock_http)
    procs = await client.get_container_top("browser-worker")
    assert len(procs) == 2
    assert procs[0]["PID"] == "1001"
    assert "celery" in procs[0]["COMMAND"]
    assert "chrome" in procs[1]["COMMAND"]

    restarted = await client.restart_container("browser-worker")
    assert restarted is True


# =========================================================================
# 2. ContainerHealthTier (Tier 1) Tests
# =========================================================================

@pytest.mark.asyncio
async def test_container_tier_socket_not_available():
    """Tier 1 reports INFO finding when docker socket is unavailable."""
    client = DockerSocketClient(socket_path="/nonexistent/docker.sock")
    tier1 = ContainerHealthTier(docker_client=client)

    findings = await tier1.audit_containers()
    assert len(findings) == 1
    assert findings[0]["level"] == "INFO"
    assert "Docker socket not available" in findings[0]["message"]


@pytest.mark.asyncio
async def test_container_tier_memory_and_cpu_thresholds():
    """Tier 1 detects memory leaks and sustained CPU thrashing."""
    client = MagicMock(spec=DockerSocketClient)
    client.is_available.return_value = True
    client.list_containers = AsyncMock(return_value=[
        {"Names": ["/xbot-worker"], "State": "running"},
        {"Names": ["/xbot-browser-worker"], "State": "running"},
    ])

    async def fake_get_stats(name: str):
        if "browser" in name:
            # browser-worker threshold is 800 MB, report 850 MB
            return {"memory_mb": 850.0, "cpu_percent": 10.0}
        else:
            # worker threshold is 600 MB, report 650 MB and 98% CPU
            return {"memory_mb": 650.0, "cpu_percent": 98.0}

    client.get_container_stats = AsyncMock(side_effect=fake_get_stats)
    client.get_container_top = AsyncMock(return_value=[])

    tier1 = ContainerHealthTier(docker_client=client)

    findings = await tier1.audit_containers()

    # Worker exceeded 600 MB
    worker_mem = next(f for f in findings if f["container"] == "xbot-worker" and f["metric"] == "memory")
    assert worker_mem["level"] in ("WARNING", "CRITICAL")
    assert worker_mem["value"] == 650.0
    assert worker_mem["action_needed"] == "restart_container"

    # Browser worker exceeded 800 MB
    browser_mem = next(f for f in findings if f["container"] == "xbot-browser-worker" and f["metric"] == "memory")
    assert browser_mem["level"] in ("WARNING", "CRITICAL")
    assert browser_mem["value"] == 850.0


@pytest.mark.asyncio
async def test_container_tier_chrome_process_threshold():
    """Tier 1 detects excess Chrome processes (>6) or defunct Chrome processes."""
    client = MagicMock(spec=DockerSocketClient)
    client.is_available.return_value = True
    client.list_containers = AsyncMock(return_value=[
        {"Names": ["/browser-worker"], "State": "running"},
    ])
    client.get_container_stats = AsyncMock(return_value={"memory_mb": 400.0, "cpu_percent": 5.0})

    # Return 7 chrome processes with 1 defunct
    client.get_container_top = AsyncMock(return_value=[
        {"COMMAND": "/opt/google/chrome/chrome --headless", "STAT": "S"},
        {"COMMAND": "/opt/google/chrome/chrome --headless", "STAT": "S"},
        {"COMMAND": "/opt/google/chrome/chrome --headless", "STAT": "S"},
        {"COMMAND": "/opt/google/chrome/chrome --headless", "STAT": "S"},
        {"COMMAND": "/opt/google/chrome/chrome --headless", "STAT": "S"},
        {"COMMAND": "/opt/google/chrome/chrome --headless", "STAT": "S"},
        {"COMMAND": "/opt/google/chrome/chrome --headless <defunct>", "STAT": "Z"},
    ])

    tier1 = ContainerHealthTier(docker_client=client)
    findings = await tier1.audit_containers()

    chrome_finding = next((f for f in findings if f.get("metric") == "chrome"), None)
    assert chrome_finding is not None
    assert chrome_finding["value"] == 7
    assert chrome_finding["defunct_count"] == 1
    assert chrome_finding["level"] in ("WARNING", "CRITICAL")


# =========================================================================
# 3. Circuit Breaker Restart Limiter Tests
# =========================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_restart_limits_and_cooldown():
    """
    Verify circuit breaker:
    - Initial restart succeeds.
    - Subsequent restart within 5m cooldown is rejected.
    - Subsequent restarts after cooldown up to 3 succeed.
    - 4th restart within 1h trips circuit breaker and quarantines container.
    """
    fake_r = MockRedis()
    mock_docker = MagicMock(spec=DockerSocketClient)
    mock_docker.restart_container = AsyncMock(return_value=True)

    healer = SelfHealingEngine(redis_client=fake_r, docker_client=mock_docker)
    container = "worker"

    with patch("time.time") as mock_time:
        t0 = 10000.0
        mock_time.return_value = t0

        # Restart 1: Should succeed
        res1 = await healer.restart_container_with_circuit_breaker(container)
        assert res1["success"] is True
        assert res1["restarts_in_last_hour"] == 1
        assert res1["quarantined"] is False

        # Restart 2 within 100s: Should be rejected by 300s cooldown
        mock_time.return_value = t0 + 100.0
        res2 = await healer.restart_container_with_circuit_breaker(container)
        assert res2["success"] is False
        assert "Cooldown active" in res2["reason"]
        assert res2["quarantined"] is False

        # Restart 2 after 301s: Should succeed
        mock_time.return_value = t0 + 301.0
        res3 = await healer.restart_container_with_circuit_breaker(container)
        assert res3["success"] is True
        assert res3["restarts_in_last_hour"] == 2

        # Restart 3 after another 301s (total 602s < 3600s): Should succeed
        mock_time.return_value = t0 + 602.0
        res4 = await healer.restart_container_with_circuit_breaker(container)
        assert res4["success"] is True
        assert res4["restarts_in_last_hour"] == 3

        # Restart 4 after another 301s (total 903s < 3600s): Trips circuit breaker (max 3/hr exceeded)
        mock_time.return_value = t0 + 903.0
        res5 = await healer.restart_container_with_circuit_breaker(container)
        assert res5["success"] is False
        assert res5["quarantined"] is True
        assert "Circuit breaker tripped" in res5["reason"]

        # Quarantine flag in Redis should be active
        assert fake_r.exists(f"xbot:sentinel:quarantine:{container}") == 1


# =========================================================================
# 4. MiddlewareHealthTier (Tier 2) Tests
# =========================================================================

@pytest.mark.asyncio
async def test_middleware_tier_worker_and_queue_audits():
    """Verify MiddlewareHealthTier detects missing worker nodes and queue backlogs."""
    fake_r = MockRedis()
    fake_r.store["celery"] = 55  # depth > 50

    tier2 = MiddlewareHealthTier(redis_client=fake_r)

    # Patch celery ping to return only tasks worker, missing browser worker
    with patch("xbot.celery_app.celery_app.control.ping", return_value=[{"tasks@host1": {"ok": "pong"}}]):
        worker_findings = tier2.audit_celery_workers()
        assert any(f["worker"] == "browser" and f["level"] == "CRITICAL" for f in worker_findings)

    # Audit queues
    queue_findings = tier2.audit_redis_queues()
    assert any(f["queue"] == "celery" and f["depth"] == 55 for f in queue_findings)


# =========================================================================
# 5. BusinessLogicHealthTier (Tier 3) Tests & Limit Drain Suppression
# =========================================================================

@pytest.mark.asyncio
async def test_business_tier_daily_limit_drain_suppresses_draft_alert():
    """
    CRITICAL INVARIANT:
    When daily_post_limit_drained lock is present, approved draft alerts
    MUST be suppressed and reported as clean limit holds (INFO level).
    """
    fake_r = MockRedis()
    slug = "test_creator"

    # Set profile daily post limit drained lock in Redis
    fake_r.set(f"xbot:limits:daily_post_limit_drained:{slug}", "Hit daily post limit", ex=86400)

    # Mock auditor to report a stuck approved draft for this profile
    mock_auditor = MagicMock()
    mock_auditor.audit_stuck_drafts = AsyncMock(return_value=[
        {
            "type": "STUCK_APPROVED_DRAFT",
            "content_id": "draft-12345",
            "profile_slug": slug,
            "reason": "Draft approved 45m ago without posting",
        }
    ])
    mock_auditor.audit_stuck_sessions = AsyncMock(return_value=[])
    mock_auditor.audit_stuck_pipeline_runs = AsyncMock(return_value=[])

    tier3 = BusinessLogicHealthTier(redis_client=fake_r, auditor=mock_auditor)
    db_mock = AsyncMock()

    findings = await tier3.audit_business(db_mock)

    # The finding MUST be INFO, NOT WARNING or CRITICAL
    draft_finding = next(f for f in findings if f.get("component") == "draft")
    assert draft_finding["level"] == "INFO"
    assert "Clean limit hold" in draft_finding["message"]
    assert draft_finding["action_needed"] == "none"


@pytest.mark.asyncio
async def test_business_tier_unlocked_draft_emits_warning():
    """When daily limit is NOT drained, a stuck approved draft emits a WARNING."""
    fake_r = MockRedis()
    slug = "active_creator"

    mock_auditor = MagicMock()
    mock_auditor.audit_stuck_drafts = AsyncMock(return_value=[
        {
            "type": "STUCK_APPROVED_DRAFT",
            "content_id": "draft-999",
            "profile_slug": slug,
            "reason": "Draft approved 50m ago without posting",
        }
    ])
    mock_auditor.audit_stuck_sessions = AsyncMock(return_value=[])
    mock_auditor.audit_stuck_pipeline_runs = AsyncMock(return_value=[])

    tier3 = BusinessLogicHealthTier(redis_client=fake_r, auditor=mock_auditor)
    db_mock = AsyncMock()

    findings = await tier3.audit_business(db_mock)
    draft_finding = next(f for f in findings if f.get("component") == "stuck_draft")
    assert draft_finding["level"] == "WARNING"
    assert draft_finding["action_needed"] == "soft_heal"


# =========================================================================
# 6. SentinelDaemon Full Tick & Escalation Tests
# =========================================================================

@pytest.mark.asyncio
async def test_sentinel_daemon_tick_and_persistence_escalation():
    """
    Verify SentinelDaemon executes a tick, stores live state in Redis,
    and escalates to Level 3 container restart if anomaly persists >= 3 ticks.
    """
    fake_r = MockRedis()
    mock_docker = MagicMock(spec=DockerSocketClient)
    mock_docker.is_available.return_value = True
    mock_docker.restart_container = AsyncMock(return_value=True)

    daemon = SentinelDaemon(redis_client=fake_r, docker_client=mock_docker, check_interval=1.0)

    # Mock Tier 1 to report high memory on worker
    daemon.tier1.audit_containers = AsyncMock(return_value=[
        {
            "level": "WARNING",
            "tier": 1,
            "container": "worker",
            "metric": "memory",
            "value": 750.0,
            "action_needed": "restart_container",
            "message": "Worker memory 750 MB exceeds 600 MB",
        }
    ])
    daemon.tier2.audit_middleware = AsyncMock(return_value=[])
    daemon.tier3.audit_business = AsyncMock(return_value=[])

    # Tick 1: Persistence = 1 -> Logged, incident counter set
    res1 = await daemon.run_tick()
    assert res1["status"] in ("degraded", "recovering", "critical")
    assert fake_r.exists("xbot:supervisor:live_state") == 1
    assert fake_r.exists("xbot:supervisor:latest_health") == 1
    assert mock_docker.restart_container.call_count == 0

    # Tick 2: Persistence = 2 -> Still no restart
    await daemon.run_tick()
    assert mock_docker.restart_container.call_count == 0

    # Tick 3: Persistence = 3 -> Triggers Level 3 restart via circuit breaker!
    await daemon.run_tick()
    assert mock_docker.restart_container.call_count == 1
    mock_docker.restart_container.assert_awaited_with("worker", timeout_seconds=30)


@pytest.mark.asyncio
async def test_sentinel_daemon_escalates_on_unserviced_queue_stall():
    """
    Verify SentinelDaemon escalates unserviced Redis queue stalls to
    the responsible worker container ('worker' for celery/publish, 'browser-worker' for browser).
    """
    fake_r = MockRedis()
    fake_r.set("xbot:sentinel:queue_stall:celery", "12345")

    mock_docker = MagicMock(spec=DockerSocketClient)
    mock_docker.is_available.return_value = True
    mock_docker.restart_container = AsyncMock(return_value=True)

    daemon = SentinelDaemon(redis_client=fake_r, docker_client=mock_docker, check_interval=1.0)
    daemon.tier1.audit_containers = AsyncMock(return_value=[])
    daemon.tier3.audit_business = AsyncMock(return_value=[])

    # Mock Tier 2 queue finding: unserviced for > 15m (action_needed: restart_container)
    daemon.tier2.audit_middleware = AsyncMock(return_value=[
        {
            "level": "CRITICAL",
            "tier": 2,
            "component": "redis_queue",
            "queue": "celery",
            "depth": 120,
            "stall_seconds": 1200,
            "message": "Queue 'celery' has been unserviced for 20m (depth: 120)",
            "action_needed": "restart_container",
        }
    ])

    # Tick 1 & 2: Persistence counters increment
    await daemon.run_tick()
    await daemon.run_tick()
    assert mock_docker.restart_container.call_count == 0

    # Tick 3: Persistence = 3 -> Triggers restart on 'worker'
    await daemon.run_tick()
    assert mock_docker.restart_container.call_count == 1
    mock_docker.restart_container.assert_awaited_with("worker", timeout_seconds=30)

    # Stall marker in Redis should be deleted after successful restart
    assert fake_r.exists("xbot:sentinel:queue_stall:celery") == 0

