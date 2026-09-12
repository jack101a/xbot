"""
XBot Autonomous Supervisor & Self-Healing Watchdog.
Monitors all containers, pipelines, worker processes, browser states, and scheduled cadences.
Automatically recovers orphan locks, stalled sessions, stuck drafts, missed runs, and flapping containers.
"""
from xbot.supervisor.auditor import PipelineAuditor
from xbot.supervisor.docker_client import DockerSocketClient
from xbot.supervisor.healer import SelfHealingEngine
from xbot.supervisor.manager import SystemSupervisor
from xbot.supervisor.sentinel import SentinelDaemon, run_sentinel_daemon
from xbot.supervisor.tiers import (
    BusinessLogicHealthTier,
    ContainerHealthTier,
    MiddlewareHealthTier,
)

__all__ = [
    "PipelineAuditor",
    "SelfHealingEngine",
    "SystemSupervisor",
    "DockerSocketClient",
    "ContainerHealthTier",
    "MiddlewareHealthTier",
    "BusinessLogicHealthTier",
    "SentinelDaemon",
    "run_sentinel_daemon",
]
