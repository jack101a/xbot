"""
XBot Autonomous Supervisor & Self-Healing Watchdog.
Monitors all pipelines, worker processes, browser states, and scheduled cadences.
Automatically recovers orphan locks, stalled sessions, stuck drafts, and missed runs.
"""
from xbot.supervisor.auditor import PipelineAuditor
from xbot.supervisor.healer import SelfHealingEngine
from xbot.supervisor.manager import SystemSupervisor

__all__ = [
    "PipelineAuditor",
    "SelfHealingEngine",
    "SystemSupervisor",
]
