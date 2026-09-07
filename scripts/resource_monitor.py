#!/usr/bin/env python3
"""
==============================================================================
XBot Pro: Comprehensive Resource Monitor & Memory Profiler
==============================================================================
Tracks real-time memory (RSS, VMS), CPU usage, process counts, and host-level
utilization across all XBot Pro components:
  1. FastAPI Backend (uvicorn)
  2. Celery Task Worker & Beat (scheduler + execution pool)
  3. Celery Browser Action Worker (browser queue engine)
  4. Playwright / Chromium Headless instances
  5. Next.js Dashboard UI (node / serve static SPA)
  6. Redis Server

Usage:
  python scripts/resource_monitor.py                   # Snapshot report + tuning advice
  python scripts/resource_monitor.py --watch 3         # Live real-time terminal monitor (every 3s)
  python scripts/resource_monitor.py --csv logs/usage.csv --watch 5  # Log telemetry to CSV
  python scripts/resource_monitor.py --json            # JSON output for APIs/dashboards
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import psutil
except ImportError:
    psutil = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PID_DIR = PROJECT_ROOT / ".pids"
LOG_DIR = PROJECT_ROOT / "logs"

DEFAULT_TELEMETRY_CSV = LOG_DIR / "resource_telemetry.csv"
DEFAULT_SPIKES_LOG = LOG_DIR / "resource_spikes.log"
MONITOR_PID_FILE = PID_DIR / "monitor.pid"
MAX_TELEMETRY_RECORDS = 2016  # 7 days of 5-minute ticks (7 * 24 * 12)
MAX_SPIKES_LOG_BYTES = 2 * 1024 * 1024  # 2 MB

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_RED = "\033[0;31m"
C_GREEN = "\033[0;32m"
C_YELLOW = "\033[1;33m"
C_BLUE = "\033[0;34m"
C_MAGENTA = "\033[0;35m"
C_CYAN = "\033[0;36m"
C_GRAY = "\033[0;90m"


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cmdline: str
    rss_mb: float
    vms_mb: float
    cpu_percent: float
    status: str
    created_time: float


@dataclass
class ComponentMetrics:
    name: str
    category: str
    is_running: bool
    main_pid: Optional[int] = None
    process_count: int = 0
    thread_count: int = 0
    rss_mb: float = 0.0
    vms_mb: float = 0.0
    cpu_percent: float = 0.0
    processes: List[ProcessInfo] = field(default_factory=list)


@dataclass
class HostMetrics:
    total_ram_mb: float
    used_ram_mb: float
    free_ram_mb: float
    available_ram_mb: float
    ram_percent: float
    total_swap_mb: float
    used_swap_mb: float
    swap_percent: float
    cpu_count_logical: int
    cpu_count_physical: int
    host_cpu_percent: float
    load_avg: List[float]


@dataclass
class ResourceSnapshot:
    timestamp: str
    components: Dict[str, ComponentMetrics]
    total_xbot_rss_mb: float
    total_xbot_vms_mb: float
    total_xbot_cpu_percent: float
    total_xbot_processes: int
    xbot_ram_percent_of_total: float
    xbot_ram_percent_of_used: float
    host: HostMetrics
    advisory: List[str] = field(default_factory=list)


class ResourceMonitor:
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or PROJECT_ROOT
        self.pid_dir = self.project_root / ".pids"
        self.peak_rss_mb = 0.0
        self.peak_cpu_percent = 0.0

    def _read_pid_file(self, filename: str) -> Optional[int]:
        path = self.pid_dir / filename
        if not path.exists():
            return None
        try:
            val = path.read_text().strip()
            return int(val) if val else None
        except Exception:
            return None

    def _get_process_tree(self, main_pid: int) -> List[Any]:
        if not psutil or not main_pid:
            return []
        try:
            parent = psutil.Process(main_pid)
            if not parent.is_running() or parent.status() == psutil.STATUS_ZOMBIE:
                return []
            children = parent.children(recursive=True)
            return [parent] + [c for c in children if c.is_running() and c.status() != psutil.STATUS_ZOMBIE]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return []

    def _find_orphan_chromium_processes(self, known_pids: set[int]) -> List[Any]:
        if not psutil:
            return []
        orphans = []
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if p.pid in known_pids:
                    continue
                cmd = " ".join(p.info.get("cmdline") or [])
                name = (p.info.get("name") or "").lower()
                if ("chrome" in name or "chromium" in name or "chrome-headless" in cmd) and (
                    "xbot" in cmd or "/home/ubuntu" in cmd or "--remote-debugging-pipe" in cmd
                ):
                    orphans.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return orphans

    def _find_redis_process(self) -> Optional[Any]:
        if not psutil:
            return None
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = (p.info.get("name") or "").lower()
                cmd = " ".join(p.info.get("cmdline") or [])
                if "redis-server" in name or "redis-server" in cmd:
                    if "6379" in cmd or p.info.get("name") == "redis-server":
                        return p
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def _extract_component_metrics(
        self, name: str, category: str, procs: List[Any], main_pid: Optional[int]
    ) -> ComponentMetrics:
        if not procs:
            return ComponentMetrics(name=name, category=category, is_running=False, main_pid=main_pid)

        proc_infos: List[ProcessInfo] = []
        total_rss = 0.0
        total_vms = 0.0
        total_cpu = 0.0
        total_threads = 0

        for p in procs:
            try:
                mem = p.memory_info()
                rss_mb = mem.rss / (1024 * 1024)
                vms_mb = mem.vms / (1024 * 1024)
                cpu = p.cpu_percent(interval=0.0)
                threads = p.num_threads()
                status = p.status()
                cmdline = " ".join(p.cmdline()[:3]) if p.cmdline() else p.name()

                total_rss += rss_mb
                total_vms += vms_mb
                total_cpu += cpu
                total_threads += threads

                proc_infos.append(
                    ProcessInfo(
                        pid=p.pid,
                        name=p.name(),
                        cmdline=cmdline,
                        rss_mb=round(rss_mb, 2),
                        vms_mb=round(vms_mb, 2),
                        cpu_percent=round(cpu, 1),
                        status=status,
                        created_time=p.create_time(),
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return ComponentMetrics(
            name=name,
            category=category,
            is_running=len(proc_infos) > 0,
            main_pid=main_pid,
            process_count=len(proc_infos),
            thread_count=total_threads,
            rss_mb=round(total_rss, 2),
            vms_mb=round(total_vms, 2),
            cpu_percent=round(total_cpu, 1),
            processes=proc_infos,
        )

    def get_host_metrics(self) -> HostMetrics:
        if not psutil:
            return HostMetrics(
                total_ram_mb=0,
                used_ram_mb=0,
                free_ram_mb=0,
                available_ram_mb=0,
                ram_percent=0,
                total_swap_mb=0,
                used_swap_mb=0,
                swap_percent=0,
                cpu_count_logical=os.cpu_count() or 1,
                cpu_count_physical=1,
                host_cpu_percent=0,
                load_avg=[0.0, 0.0, 0.0],
            )

        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        load = os.getloadavg() if hasattr(os, "getloadavg") else [0.0, 0.0, 0.0]

        return HostMetrics(
            total_ram_mb=round(vm.total / (1024 * 1024), 1),
            used_ram_mb=round(vm.used / (1024 * 1024), 1),
            free_ram_mb=round(vm.free / (1024 * 1024), 1),
            available_ram_mb=round(vm.available / (1024 * 1024), 1),
            ram_percent=round(vm.percent, 1),
            total_swap_mb=round(swap.total / (1024 * 1024), 1),
            used_swap_mb=round(swap.used / (1024 * 1024), 1),
            swap_percent=round(swap.percent, 1),
            cpu_count_logical=psutil.cpu_count(logical=True) or 1,
            cpu_count_physical=psutil.cpu_count(logical=False) or 1,
            host_cpu_percent=round(psutil.cpu_percent(interval=0.1), 1),
            load_avg=[round(x, 2) for x in load],
        )

    def collect_snapshot(self) -> ResourceSnapshot:
        backend_pid = self._read_pid_file("backend.pid")
        celery_pid = self._read_pid_file("celery.pid")
        celery_browser_pid = self._read_pid_file("celery_browser.pid")
        dashboard_pid = self._read_pid_file("dashboard.pid")

        backend_procs = self._get_process_tree(backend_pid) if backend_pid else []
        celery_procs = self._get_process_tree(celery_pid) if celery_pid else []
        browser_worker_procs = self._get_process_tree(celery_browser_pid) if celery_browser_pid else []
        dashboard_procs = self._get_process_tree(dashboard_pid) if dashboard_pid else []

        # Separate Chromium processes from the browser worker if present
        pure_browser_worker_procs = []
        chromium_procs = []
        for p in browser_worker_procs:
            try:
                name = p.name().lower()
                cmd = " ".join(p.cmdline() or [])
                if "chrome" in name or "chromium" in name or "chrome-headless" in cmd:
                    chromium_procs.append(p)
                else:
                    pure_browser_worker_procs.append(p)
            except Exception:
                pure_browser_worker_procs.append(p)

        # Also search for any detached or orphan chromium instances
        known_pids = {p.pid for p in (backend_procs + celery_procs + browser_worker_procs + dashboard_procs)}
        extra_chromium = self._find_orphan_chromium_processes(known_pids)
        chromium_procs.extend(extra_chromium)

        redis_proc = self._find_redis_process()
        redis_procs = [redis_proc] if redis_proc else []

        # Build component metrics
        components: Dict[str, ComponentMetrics] = {
            "backend": self._extract_component_metrics(
                "FastAPI Backend", "API Service", backend_procs, backend_pid
            ),
            "celery_tasks": self._extract_component_metrics(
                "Celery Task Worker & Beat", "Task Scheduler", celery_procs, celery_pid
            ),
            "celery_browser": self._extract_component_metrics(
                "Celery Browser Worker", "Queue Dispatcher", pure_browser_worker_procs, celery_browser_pid
            ),
            "chromium": self._extract_component_metrics(
                "Chromium Playwright Engine", "Headless Browser", chromium_procs, chromium_procs[0].pid if chromium_procs else None
            ),
            "dashboard": self._extract_component_metrics(
                "Dashboard UI", "Web Frontend", dashboard_procs, dashboard_pid
            ),
            "redis": self._extract_component_metrics(
                "Redis Datastore", "In-Memory Broker", redis_procs, redis_procs[0].pid if redis_procs else None
            ),
        }

        # Totals
        xbot_components = ["backend", "celery_tasks", "celery_browser", "chromium", "dashboard"]
        total_rss = sum(components[c].rss_mb for c in xbot_components)
        total_vms = sum(components[c].vms_mb for c in xbot_components)
        total_cpu = sum(components[c].cpu_percent for c in xbot_components)
        total_procs = sum(components[c].process_count for c in xbot_components)

        host = self.get_host_metrics()
        xbot_ram_pct_total = round((total_rss / host.total_ram_mb) * 100, 2) if host.total_ram_mb else 0.0
        xbot_ram_pct_used = round((total_rss / host.used_ram_mb) * 100, 2) if host.used_ram_mb else 0.0

        if total_rss > self.peak_rss_mb:
            self.peak_rss_mb = total_rss
        if total_cpu > self.peak_cpu_percent:
            self.peak_cpu_percent = total_cpu

        advisory = self._generate_advisory(components, total_rss, host)

        return ResourceSnapshot(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            components=components,
            total_xbot_rss_mb=round(total_rss, 2),
            total_xbot_vms_mb=round(total_vms, 2),
            total_xbot_cpu_percent=round(total_cpu, 1),
            total_xbot_processes=total_procs,
            xbot_ram_percent_of_total=xbot_ram_pct_total,
            xbot_ram_percent_of_used=xbot_ram_pct_used,
            host=host,
            advisory=advisory,
        )

    def _generate_advisory(
        self, components: Dict[str, ComponentMetrics], total_rss: float, host: HostMetrics
    ) -> List[str]:
        tips = []

        # 1. Host memory pressure
        if host.available_ram_mb < 1000:
            tips.append(
                f"CRITICAL: Low Host Available RAM ({host.available_ram_mb:.0f} MB). Host is under severe pressure."
            )
        elif host.available_ram_mb < 2000:
            tips.append(
                f"NOTICE: Available Host RAM is {host.available_ram_mb:.0f} MB. Sufficient for current load, but monitor browser peaks."
            )

        # 2. Celery Worker footprint
        tasks_rss = components["celery_tasks"].rss_mb
        if tasks_rss > 450:
            tips.append(
                f"Celery Task Worker is using {tasks_rss:.1f} MB. Consider adding worker_max_tasks_per_child=50 to auto-recycle worker processes."
            )

        # 3. Chromium Headless footprint
        chrom_rss = components["chromium"].rss_mb
        if components["chromium"].is_running:
            if chrom_rss > 500:
                tips.append(
                    f"Chromium instance footprint is high ({chrom_rss:.1f} MB across {components['chromium'].process_count} procs). Ensure TabPool closes idle worker tabs promptly."
                )
            else:
                tips.append(
                    f"Chromium instance is active and lean ({chrom_rss:.1f} MB, {components['chromium'].process_count} procs)."
                )
        else:
            tips.append(
                "Chromium Engine is currently idle (0 MB). Dual-lane browser starts on-demand during scheduled actions."
            )

        # 4. Dashboard mode
        dash = components["dashboard"]
        if dash.is_running:
            if dash.rss_mb > 250:
                tips.append(
                    f"Dashboard UI is using {dash.rss_mb:.1f} MB (likely next dev mode). Run 'npm run build' and use 'serve' static mode to reduce to ~70 MB."
                )
            else:
                tips.append(
                    f"Dashboard UI is running in lightweight static mode ({dash.rss_mb:.1f} MB)."
                )

        # 5. Swap usage
        if host.used_swap_mb > 3000:
            tips.append(
                f"Host Swap usage is elevated ({host.used_swap_mb:.0f} MB / {host.total_swap_mb:.0f} MB). Consider adjusting vm.swappiness=10 to preserve responsiveness."
            )

        return tips


def format_progress_bar(percent: float, width: int = 20) -> str:
    filled = int(round(width * (percent / 100)))
    filled = max(0, min(width, filled))
    bar = "█" * filled + "░" * (width - filled)
    if percent > 85:
        return f"{C_RED}[{bar}]{C_RESET}"
    elif percent > 65:
        return f"{C_YELLOW}[{bar}]{C_RESET}"
    return f"{C_GREEN}[{bar}]{C_RESET}"


def print_snapshot_report(snap: ResourceSnapshot, peak_rss: float = 0.0, peak_cpu: float = 0.0) -> None:
    h = snap.host
    print(f"\n{C_BOLD}{C_CYAN}=============================================================================={C_RESET}")
    print(f"{C_BOLD}{C_CYAN}                📊 XBot Pro Comprehensive Resource Report                    {C_RESET}")
    print(f"{C_BOLD}{C_CYAN}=============================================================================={C_RESET}")
    print(f"  {C_BOLD}Timestamp:{C_RESET} {snap.timestamp}  |  {C_BOLD}Host CPU Load:{C_RESET} {h.load_avg[0]}, {h.load_avg[1]}, {h.load_avg[2]} ({h.cpu_count_logical} cores)")
    print(f"  {C_BOLD}Host RAM:{C_RESET}  {h.used_ram_mb:,.0f} MB used / {h.total_ram_mb:,.0f} MB total ({h.ram_percent}%) {format_progress_bar(h.ram_percent, 16)}  Avail: {h.available_ram_mb:,.0f} MB")
    print(f"  {C_BOLD}Host Swap:{C_RESET} {h.used_swap_mb:,.0f} MB used / {h.total_swap_mb:,.0f} MB total ({h.swap_percent}%)")
    print(f"{C_CYAN}------------------------------------------------------------------------------{C_RESET}")

    # Table Header
    print(
        f"{C_BOLD}{'COMPONENT / SERVICE':<30} {'STATUS':<12} {'PROCS':<7} {'THREADS':<9} {'RSS (RAM)':<14} {'CPU %':<8}{C_RESET}"
    )
    print(f"{C_GRAY}{'-'*30} {'-'*12} {'-'*7} {'-'*9} {'-'*14} {'-'*8}{C_RESET}")

    for key, c in snap.components.items():
        if c.is_running:
            status_str = f"{C_GREEN}● RUNNING{C_RESET}"
            rss_str = f"{c.rss_mb:6.1f} MB"
            cpu_str = f"{c.cpu_percent:5.1f}%"
            procs_str = f"{c.process_count:<7}"
            thr_str = f"{c.thread_count:<9}"
        else:
            status_str = f"{C_GRAY}○ IDLE/OFF{C_RESET}"
            rss_str = f"{C_GRAY}   0.0 MB{C_RESET}"
            cpu_str = f"{C_GRAY}  0.0%{C_RESET}"
            procs_str = f"{C_GRAY}0{C_RESET}      "
            thr_str = f"{C_GRAY}0{C_RESET}        "

        # Highlight Redis differently since it is external shared
        name_str = f"{c.name} {C_GRAY}(Shared){C_RESET}" if key == "redis" else c.name
        print(f"{name_str:<30} {status_str:<21} {procs_str} {thr_str} {rss_str:<14} {cpu_str}")

    print(f"{C_CYAN}------------------------------------------------------------------------------{C_RESET}")

    # Aggregates
    print(
        f"{C_BOLD}{'TOTAL XBOT CORE WORKLOAD':<30} {'● ACTIVE':<12} {snap.total_xbot_processes:<7} {'-':<9} "
        f"{C_BOLD}{C_GREEN}{snap.total_xbot_rss_mb:6.1f} MB{C_RESET}      {C_BOLD}{C_GREEN}{snap.total_xbot_cpu_percent:5.1f}%{C_RESET}"
    )
    if peak_rss > 0:
        print(f"  {C_GRAY}* Session Peaks: Max RAM {peak_rss:,.1f} MB | Max CPU {peak_cpu:.1f}%{C_RESET}")

    print(
        f"  • {C_BOLD}XBot % of Host Total RAM:{C_RESET} {snap.xbot_ram_percent_of_total:.2f}%  |  "
        f"{C_BOLD}% of Active Host Used RAM:{C_RESET} {snap.xbot_ram_percent_of_used:.2f}%"
    )

    # Detailed process tree breakdown
    print(f"\n{C_BOLD}🔍 Process Tree Breakdown:{C_RESET}")
    for key, c in snap.components.items():
        if not c.is_running:
            continue
        print(f"  {C_CYAN}▸ {c.name}{C_RESET} (PID {c.main_pid or 'N/A'}, Subtotal: {c.rss_mb:.1f} MB):")
        for p in c.processes:
            print(f"    ├─ [PID {p.pid:<7}] {p.rss_mb:6.1f} MB RSS | {p.cpu_percent:4.1f}% CPU | {p.name:<16} | {p.cmdline[:55]}")

    # Advisory
    if snap.advisory:
        print(f"\n{C_BOLD}{C_YELLOW}💡 Resource Tuning & Optimization Advisory:{C_RESET}")
        for tip in snap.advisory:
            print(f"  {C_YELLOW}•{C_RESET} {tip}")

    print(f"{C_BOLD}{C_CYAN}=============================================================================={C_RESET}\n")


def run_continuous_watch(
    monitor: ResourceMonitor,
    interval: float = 3.0,
    csv_file: Optional[Path] = None,
) -> None:
    print(f"{C_BOLD}{C_GREEN}Starting continuous XBot Pro resource monitor (interval: {interval}s). Press Ctrl+C to exit.{C_RESET}")

    csv_writer = None
    csv_f = None
    if csv_file:
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        file_exists = csv_file.exists()
        csv_f = open(csv_file, "a", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_f)
        if not file_exists:
            csv_writer.writerow([
                "timestamp",
                "total_xbot_rss_mb",
                "backend_rss_mb",
                "celery_tasks_rss_mb",
                "celery_browser_rss_mb",
                "chromium_rss_mb",
                "dashboard_rss_mb",
                "redis_rss_mb",
                "total_xbot_cpu_pct",
                "host_used_ram_mb",
                "host_avail_ram_mb",
                "host_cpu_pct",
            ])
            csv_f.flush()

    try:
        while True:
            # Clear terminal for fresh display
            os.system("clear")
            snap = monitor.collect_snapshot()
            print_snapshot_report(snap, monitor.peak_rss_mb, monitor.peak_cpu_percent)

            if csv_writer and csv_f:
                c = snap.components
                csv_writer.writerow([
                    snap.timestamp,
                    snap.total_xbot_rss_mb,
                    c["backend"].rss_mb,
                    c["celery_tasks"].rss_mb,
                    c["celery_browser"].rss_mb,
                    c["chromium"].rss_mb,
                    c["dashboard"].rss_mb,
                    c["redis"].rss_mb,
                    snap.total_xbot_cpu_percent,
                    snap.host.used_ram_mb,
                    snap.host.available_ram_mb,
                    snap.host.host_cpu_percent,
                ])
                csv_f.flush()

            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n{C_BOLD}{C_CYAN}Stopped monitoring. Session summary:{C_RESET}")
        print(f"  • Peak RAM reached: {monitor.peak_rss_mb:.1f} MB")
        print(f"  • Peak CPU reached: {monitor.peak_cpu_percent:.1f}%")
        if csv_file:
            print(f"  • Historical log saved to: {csv_file}")
    finally:
        if csv_f:
            csv_f.close()


def rotate_csv_if_needed(csv_path: Path, max_records: int = MAX_TELEMETRY_RECORDS) -> None:
    """Keeps telemetry CSV capped to max_records (e.g. 7 days of 5m ticks) to guarantee zero disk bloat."""
    if not csv_path.exists():
        return
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Only prune if excess is noticeable (every 50 rows over limit)
        if len(lines) > max_records + 50:
            header = lines[0]
            kept_lines = [header] + lines[-max_records:]
            tmp_path = csv_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.writelines(kept_lines)
            tmp_path.replace(csv_path)
    except Exception:
        pass


def rotate_spikes_log_if_needed(log_path: Path, max_bytes: int = MAX_SPIKES_LOG_BYTES) -> None:
    """Rotates spike forensics log when it exceeds max_bytes, keeping at most 1 backup."""
    if not log_path.exists():
        return
    try:
        if log_path.stat().st_size > max_bytes:
            backup = log_path.with_suffix(".log.1")
            if backup.exists():
                backup.unlink()
            log_path.rename(backup)
    except Exception:
        pass


def record_telemetry_tick(
    monitor: ResourceMonitor,
    prev_snapshot: Optional[ResourceSnapshot] = None,
    csv_path: Path = DEFAULT_TELEMETRY_CSV,
    spikes_path: Path = DEFAULT_SPIKES_LOG,
) -> tuple[ResourceSnapshot, bool]:
    """Records one 5-minute snapshot to CSV and logs detailed forensic root cause if a spike occurs."""
    snap = monitor.collect_snapshot()
    c = snap.components

    # Spike Detection Heuristics:
    # 1. Sudden delta > 200 MB in 5 minutes
    # 2. Total XBot RAM > 1200 MB
    # 3. Chromium footprint > 400 MB
    # 4. Celery Task Worker > 450 MB
    spike_detected = False
    spike_reasons: List[str] = []

    if prev_snapshot is not None:
        delta_ram = snap.total_xbot_rss_mb - prev_snapshot.total_xbot_rss_mb
        if delta_ram > 200.0:
            spike_detected = True
            spike_reasons.append(
                f"Total RAM surged +{delta_ram:.1f} MB in 5m (from {prev_snapshot.total_xbot_rss_mb:.1f} to {snap.total_xbot_rss_mb:.1f} MB)"
            )

    if snap.total_xbot_rss_mb > 1200.0:
        spike_detected = True
        spike_reasons.append(f"Total XBot RAM exceeded 1.2 GB budget ({snap.total_xbot_rss_mb:.1f} MB)")

    if c["chromium"].is_running and c["chromium"].rss_mb > 400.0:
        spike_detected = True
        spike_reasons.append(
            f"Chromium footprint high ({c['chromium'].rss_mb:.1f} MB across {c['chromium'].process_count} procs)"
        )

    if c["celery_tasks"].rss_mb > 450.0:
        spike_detected = True
        spike_reasons.append(f"Celery Task Worker memory elevated ({c['celery_tasks'].rss_mb:.1f} MB)")

    reason_str = "; ".join(spike_reasons) if spike_reasons else ""

    # Append to CSV
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp",
                "total_xbot_rss_mb",
                "backend_rss_mb",
                "celery_tasks_rss_mb",
                "celery_browser_rss_mb",
                "chromium_rss_mb",
                "dashboard_rss_mb",
                "redis_rss_mb",
                "total_xbot_cpu_pct",
                "host_used_ram_mb",
                "host_avail_ram_mb",
                "host_cpu_pct",
                "spike_detected",
                "spike_reason",
            ])
        writer.writerow([
            snap.timestamp,
            snap.total_xbot_rss_mb,
            c["backend"].rss_mb,
            c["celery_tasks"].rss_mb,
            c["celery_browser"].rss_mb,
            c["chromium"].rss_mb,
            c["dashboard"].rss_mb,
            c["redis"].rss_mb,
            snap.total_xbot_cpu_percent,
            snap.host.used_ram_mb,
            snap.host.available_ram_mb,
            snap.host.host_cpu_percent,
            1 if spike_detected else 0,
            reason_str,
        ])

    # Enforce zero disk bloat
    rotate_csv_if_needed(csv_path)

    # Forensic Spike Logging: pinpoint exactly WHAT processes spiked WHAT
    if spike_detected:
        rotate_spikes_log_if_needed(spikes_path)
        with open(spikes_path, "a", encoding="utf-8") as sf:
            sf.write("=" * 80 + "\n")
            sf.write(f"[{snap.timestamp}] ⚠️ RESOURCE SPIKE DETECTED\n")
            sf.write(f"Reason: {reason_str}\n")
            sf.write(
                f"Total XBot RAM: {snap.total_xbot_rss_mb:.1f} MB | Host Avail: {snap.host.available_ram_mb:.0f} MB | Host CPU: {snap.host.host_cpu_percent:.1f}%\n"
            )
            sf.write("Component Breakdown:\n")
            for comp_key, comp in c.items():
                status_txt = "RUNNING" if comp.is_running else "IDLE"
                sf.write(
                    f"  • {comp.name:<30}: {comp.rss_mb:6.1f} MB ({status_txt}, {comp.process_count} procs, PID {comp.main_pid or 'N/A'})\n"
                )
            sf.write("Active Suspicious / Heavy Processes at Spike Time:\n")
            for comp_key, comp in c.items():
                if comp.is_running:
                    for p in comp.processes:
                        sf.write(
                            f"    ├─ [PID {p.pid:<7}] {p.rss_mb:6.1f} MB RSS | {p.cpu_percent:4.1f}% CPU | {p.name:<16} | {p.cmdline}\n"
                        )
            sf.write("=" * 80 + "\n\n")

    return snap, spike_detected


def run_recording_daemon(
    interval: float = 300.0,
    csv_path: Path = DEFAULT_TELEMETRY_CSV,
    spikes_path: Path = DEFAULT_SPIKES_LOG,
    pid_file: Path = MONITOR_PID_FILE,
) -> None:
    """Runs continuous background recorder waking up every 5 minutes."""
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))

    import signal

    running = True

    def _sig_handler(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, _sig_handler)
    signal.signal(signal.SIGINT, _sig_handler)

    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] XBot Resource Telemetry Daemon started (PID {os.getpid()}, interval: {interval}s)."
    )
    monitor = ResourceMonitor()
    prev_snap: Optional[ResourceSnapshot] = None

    try:
        while running:
            try:
                snap, spike = record_telemetry_tick(
                    monitor, prev_snap, csv_path=csv_path, spikes_path=spikes_path
                )
                prev_snap = snap
            except Exception as ex:
                sys.stderr.write(f"Error recording telemetry tick: {ex}\n")

            # Sleep in 1-second chunks for responsive SIGTERM handling
            for _ in range(int(interval)):
                if not running:
                    break
                time.sleep(1.0)
    finally:
        if pid_file.exists():
            try:
                pid_file.unlink()
            except Exception:
                pass
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] XBot Resource Telemetry Daemon stopped."
        )


def show_history(hours: float = 24.0, csv_path: Path = DEFAULT_TELEMETRY_CSV) -> None:
    """Renders historical memory trend and spike analysis from recorded telemetry."""
    if not csv_path.exists():
        print(f"{C_YELLOW}No telemetry history file found at: {csv_path}{C_RESET}")
        print("Telemetry recording runs every 5 minutes when XBot Pro is active.")
        return

    rows: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if not rows:
        print(f"{C_YELLOW}Telemetry log file is empty.{C_RESET}")
        return

    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(hours=hours)

    filtered = []
    for r in rows:
        try:
            dt = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
            if dt >= cutoff:
                filtered.append(r)
        except Exception:
            filtered.append(r)

    if not filtered:
        # Fall back to latest entries if window is empty
        filtered = rows[-min(len(rows), int(hours * 12)):]

    total_rss_list = [float(r["total_xbot_rss_mb"]) for r in filtered]
    chromium_rss_list = [float(r["chromium_rss_mb"]) for r in filtered]
    celery_rss_list = [float(r["celery_tasks_rss_mb"]) for r in filtered]
    browser_rss_list = [float(r["celery_browser_rss_mb"]) for r in filtered]
    backend_rss_list = [float(r["backend_rss_mb"]) for r in filtered]
    dash_rss_list = [float(r["dashboard_rss_mb"]) for r in filtered]
    spikes_count = sum(1 for r in filtered if str(r.get("spike_detected")).strip() in ("1", "True"))

    avg_rss = sum(total_rss_list) / len(total_rss_list)
    min_rss = min(total_rss_list)
    max_rss = max(total_rss_list)

    print(f"\n{C_BOLD}{C_CYAN}=============================================================================={C_RESET}")
    print(f"{C_BOLD}{C_CYAN}         📈 XBot Pro Resource History (Last {hours:.1f}h / {len(filtered)} records)           {C_RESET}")
    print(f"{C_BOLD}{C_CYAN}=============================================================================={C_RESET}")
    print(f"  • {C_BOLD}Total Samples:{C_RESET}     {len(filtered)} records (5-minute interval)")
    print(f"  • {C_BOLD}Average XBot RAM:{C_RESET}  {avg_rss:.1f} MB")
    print(f"  • {C_BOLD}Minimum XBot RAM:{C_RESET}  {min_rss:.1f} MB")
    print(f"  • {C_BOLD}Peak XBot RAM:{C_RESET}     {C_BOLD}{C_YELLOW if max_rss > 1000 else C_GREEN}{max_rss:.1f} MB{C_RESET}")
    print(f"  • {C_BOLD}Spike Incidents:{C_RESET}   {C_BOLD}{C_RED if spikes_count > 0 else C_GREEN}{spikes_count}{C_RESET}")
    print(f"{C_CYAN}------------------------------------------------------------------------------{C_RESET}")

    print(f"{C_BOLD}{'COMPONENT':<28} {'AVG RAM':<14} {'PEAK RAM':<14}{C_RESET}")
    print(f"{C_GRAY}{'-'*28} {'-'*14} {'-'*14}{C_RESET}")
    for name, vals in [
        ("FastAPI Backend", backend_rss_list),
        ("Celery Task Worker", celery_rss_list),
        ("Celery Browser Worker", browser_rss_list),
        ("Chromium Engine", chromium_rss_list),
        ("Dashboard UI", dash_rss_list),
    ]:
        c_avg = sum(vals) / len(vals) if vals else 0.0
        c_max = max(vals) if vals else 0.0
        print(f"{name:<28} {c_avg:6.1f} MB      {c_max:6.1f} MB")

    print(f"{C_CYAN}------------------------------------------------------------------------------{C_RESET}")
    print(f"{C_BOLD}Recent 5-Minute Telemetry Ticks (Latest 10):{C_RESET}")
    print(f"{'TIMESTAMP':<20} {'TOTAL':<10} {'CELERY':<10} {'BROWSER':<10} {'CHROMIUM':<10} {'SPIKE?':<8}")
    print(f"{C_GRAY}{'-'*20} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*8}{C_RESET}")
    for r in filtered[-10:]:
        is_spk = str(r.get("spike_detected")).strip() in ("1", "True")
        spk_str = f"{C_RED}YES ⚠️{C_RESET}" if is_spk else f"{C_GREEN}No{C_RESET}"
        print(
            f"{r['timestamp']:<20} {float(r['total_xbot_rss_mb']):5.1f} MB  {float(r['celery_tasks_rss_mb']):5.1f} MB  {float(r['celery_browser_rss_mb']):5.1f} MB  {float(r['chromium_rss_mb']):5.1f} MB  {spk_str}"
        )

    print(f"{C_BOLD}{C_CYAN}=============================================================================={C_RESET}\n")


def show_spikes(spikes_path: Path = DEFAULT_SPIKES_LOG) -> None:
    """Displays root cause and forensics for all detected resource spikes."""
    if not spikes_path.exists() or spikes_path.stat().st_size == 0:
        print(f"\n{C_BOLD}{C_GREEN}✅ No resource spikes detected. All components have operated within safe RAM boundaries.{C_RESET}\n")
        return

    print(f"\n{C_BOLD}{C_RED}=============================================================================={C_RESET}")
    print(f"{C_BOLD}{C_RED}                 🚨 Recorded Resource Spike Forensics                         {C_RESET}")
    print(f"{C_BOLD}{C_RED}=============================================================================={C_RESET}\n")
    try:
        content = spikes_path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        if len(lines) > 80:
            print(f"{C_GRAY}... (showing latest forensic records) ...{C_RESET}\n")
            print("\n".join(lines[-80:]))
        else:
            print(content)
    except Exception as ex:
        print(f"Error reading spike log: {ex}")
    print(f"{C_BOLD}{C_RED}=============================================================================={C_RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="XBot Pro Resource Monitor & Telemetry Profiler")
    parser.add_argument(
        "--watch", "-w", nargs="?", const=3.0, type=float, help="Run in continuous terminal watch mode (default: 3s)"
    )
    parser.add_argument("--json", action="store_true", help="Output metrics as structured JSON")
    parser.add_argument("--csv", type=str, help="Append monitoring metrics to specified CSV file")
    parser.add_argument("--snapshot", "-s", action="store_true", help="Output a single snapshot (default)")
    parser.add_argument("--record", action="store_true", help="Run in 5-minute background telemetry recording mode")
    parser.add_argument("--interval", type=float, default=300.0, help="Interval in seconds for recorder mode (default: 300s)")
    parser.add_argument("--history", nargs="?", const=24.0, type=float, help="Display telemetry history summary for past N hours (default: 24h)")
    parser.add_argument("--spikes", action="store_true", help="Display all forensic spike incidents")

    args = parser.parse_args()
    monitor = ResourceMonitor()

    if args.json:
        snap = monitor.collect_snapshot()
        print(json.dumps(asdict(snap), indent=2))
        return

    if args.spikes:
        show_spikes()
        return

    if args.history is not None:
        show_history(hours=args.history)
        return

    if args.record:
        run_recording_daemon(interval=args.interval)
        return

    if args.watch is not None:
        csv_path = Path(args.csv) if args.csv else None
        run_continuous_watch(monitor, interval=args.watch, csv_file=csv_path)
    else:
        snap = monitor.collect_snapshot()
        print_snapshot_report(snap, monitor.peak_rss_mb, monitor.peak_cpu_percent)


if __name__ == "__main__":
    main()

