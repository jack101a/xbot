#!/usr/bin/env python3
"""
XBot Autonomous Supervisor CLI Tool.
Inspects system health, monitors pipelines, views healing events, and triggers self-healing.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from xbot.supervisor.manager import SystemSupervisor

# ANSI Color codes
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
DIM = "\033[2m"
RESET = "\033[0m"


def format_status(status: str) -> str:
    s = status.lower()
    if s == "healthy":
        return f"{GREEN}● HEALTHY{RESET}"
    elif s == "recovering":
        return f"{YELLOW}◐ RECOVERING{RESET}"
    elif s == "degraded":
        return f"{YELLOW}▲ DEGRADED{RESET}"
    elif s == "critical":
        return f"{RED}✖ CRITICAL{RESET}"
    return f"{DIM}○ {status.upper()}{RESET}"


async def cmd_status() -> None:
    print(f"\n{BOLD}{CYAN}======================================================{RESET}")
    print(f"{BOLD}{CYAN}        🛡️  XBot Autonomous System Supervisor          {RESET}")
    print(f"{BOLD}{CYAN}======================================================{RESET}\n")

    supervisor = SystemSupervisor()
    cached = supervisor.get_cached_health()

    if cached.get("status") != "unknown":
        print(f"  {BOLD}System Health Status:{RESET}      {format_status(cached['status'])}")
        print(f"  {BOLD}Last Reconciliation:{RESET}       {cached.get('timestamp', 'N/A')}")
        workers = cached.get("active_workers", [])
        worker_str = ", ".join(workers) if workers else "None"
        print(f"  {BOLD}Active Celery Workers:{RESET}     {GREEN if workers else RED}{worker_str}{RESET}")
        print(f"  {BOLD}Anomalies/Stuck Tasks:{RESET}     {cached.get('issues_detected_count', 0)}")
        print(f"  {BOLD}Total Auto-Healed:{RESET}         {cached.get('healed_events_count', 0)}")
        
        details = cached.get("pipelines_health", {})
        print(f"\n  {BOLD}Pipeline & Component Breakdown:{RESET}")
        print(f"    • Orphaned Redis Locks:      {details.get('lock_issues_count', 0)}")
        print(f"    • Stuck Playwright Sessions: {details.get('stuck_sessions_count', 0)}")
        print(f"    • Stuck Background Runs:     {details.get('stuck_runs_count', 0)}")
        print(f"    • Stuck Approved Drafts:     {details.get('stuck_drafts_count', 0)}")
        print(f"    • Overdue Cadence Gaps:      {details.get('overdue_cadences_count', 0)}")
        print(f"    • Zombie Headless Browsers:  {details.get('zombie_browsers_count', 0)}")
        print(f"    • Audit Cycle Duration:      {details.get('reconciliation_duration_ms', 0)} ms")
    else:
        print(f"  {YELLOW}No recent health telemetry cached. Running live audit pass...{RESET}")
        res = await supervisor.reconcile(auto_heal=False)
        print(f"  {BOLD}System Health Status:{RESET}      {format_status(res['status'])}")
        print(f"  {BOLD}Issues Detected:{RESET}           {res.get('issues_count', 0)}")

    print(f"\n{DIM}Run './xbot.sh supervisor heal' to trigger an immediate self-healing cycle.{RESET}\n")


async def cmd_heal() -> None:
    print(f"\n{BOLD}{CYAN}======================================================{RESET}")
    print(f"{BOLD}{CYAN}     🔧 Triggering Autonomous Self-Healing Cycle      {RESET}")
    print(f"{BOLD}{CYAN}======================================================{RESET}\n")

    supervisor = SystemSupervisor()
    res = await supervisor.reconcile(auto_heal=True)

    print(f"  {BOLD}Result Status:{RESET}         {format_status(res['status'])}")
    print(f"  {BOLD}Issues Detected:{RESET}       {res.get('issues_count', 0)}")
    print(f"  {BOLD}Remediations Applied:{RESET}  {res.get('healed_count', 0)}")

    actions = res.get("healing_actions", [])
    if actions:
        print(f"\n  {BOLD}{GREEN}Applied Remediation Actions:{RESET}")
        for act in actions:
            print(f"    ✓ {act}")
    else:
        print(f"\n  {GREEN}✓ System is in full harmony. No corrective actions needed.{RESET}")
    print()


async def cmd_events(limit: int = 15) -> None:
    print(f"\n{BOLD}{CYAN}======================================================{RESET}")
    print(f"{BOLD}{CYAN}       📜 Recent Auto-Healing Events Log              {RESET}")
    print(f"{BOLD}{CYAN}======================================================{RESET}\n")

    supervisor = SystemSupervisor()
    events = await supervisor.get_recent_healing_events(limit=limit)

    if not events:
        print(f"  {DIM}No auto-healing events recorded yet.{RESET}\n")
        return

    print(f"  {'TIMESTAMP':<20} | {'COMPONENT':<18} | {'ACTION TAKEN':<35} | {'STATUS'}")
    print(f"  {'-'*20}-+-{'-'*18}-+-{'-'*35}-+-{'-'*10}")

    for e in events:
        ts = (e["created_at"] or "")[:19].replace("T", " ")
        comp = (e["component"] or "")[:18]
        act = (e["action_taken"] or "")[:35]
        st = e.get("status", "resolved").upper()
        color = GREEN if st == "RESOLVED" else YELLOW
        print(f"  {ts:<20} | {comp:<18} | {act:<35} | {color}{st}{RESET}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="XBot Supervisor & Watchdog CLI")
    subparsers = parser.add_subparsers(dest="subcommand", help="Supervisor command")

    subparsers.add_parser("status", help="Show system health status")
    subparsers.add_parser("heal", help="Trigger immediate audit & self-healing")
    events_p = subparsers.add_parser("events", help="Show recent healing events")
    events_p.add_argument("--limit", type=int, default=15, help="Number of events to show")

    args = parser.parse_args()

    if args.subcommand == "heal":
        asyncio.run(cmd_heal())
    elif args.subcommand == "events":
        asyncio.run(cmd_events(limit=args.limit))
    else:
        asyncio.run(cmd_status())


if __name__ == "__main__":
    main()
