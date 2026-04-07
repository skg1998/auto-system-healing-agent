from __future__ import annotations

import time
from typing import List, Optional, Tuple

import psutil

from self_healing_agent.core.models import ProcessSample, SnapshotCapabilities, SystemSnapshot


class PsutilAdapter:
    """
    Baseline metrics via psutil (Windows / Linux / macOS).

    Disk and network rates need a previous sample; first tick may report None for bps.
    Process CPU% uses a short two-phase sample (prime + sleep) — see list_processes.
    """

    def __init__(self, process_limit: int = 256) -> None:
        self._process_limit = max(1, process_limit)
        self._prev_t: Optional[float] = None
        self._prev_disk: Optional[Tuple[int, int]] = None  # read_bytes, write_bytes
        self._prev_net: Optional[Tuple[int, int]] = None  # bytes_sent, bytes_recv

    def collect_system(self) -> SystemSnapshot:
        now = time.monotonic()
        # Block briefly so CPU% is meaningful (psutil contract).
        cpu_total_pct = float(psutil.cpu_percent(interval=0.1))
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        disk_read_bps: Optional[float] = None
        disk_write_bps: Optional[float] = None
        d = psutil.disk_io_counters()
        if d is not None:
            pair = (int(d.read_bytes), int(d.write_bytes))
            if self._prev_disk is not None and self._prev_t is not None:
                dt = now - self._prev_t
                if dt > 0:
                    disk_read_bps = (pair[0] - self._prev_disk[0]) / dt
                    disk_write_bps = (pair[1] - self._prev_disk[1]) / dt
            self._prev_disk = pair

        net_sent_bps: Optional[float] = None
        net_recv_bps: Optional[float] = None
        n = psutil.net_io_counters()
        if n is not None:
            pair = (int(n.bytes_sent), int(n.bytes_recv))
            if self._prev_net is not None and self._prev_t is not None:
                dt = now - self._prev_t
                if dt > 0:
                    net_sent_bps = (pair[0] - self._prev_net[0]) / dt
                    net_recv_bps = (pair[1] - self._prev_net[1]) / dt
            self._prev_net = pair

        self._prev_t = now

        return SystemSnapshot(
            timestamp_monotonic_s=now,
            cpu_total_pct=cpu_total_pct,
            mem_used_bytes=int(vm.used),
            mem_total_bytes=int(vm.total),
            swap_used_bytes=int(swap.used),
            disk_read_bps=disk_read_bps,
            disk_write_bps=disk_write_bps,
            net_sent_bps=net_sent_bps,
            net_recv_bps=net_recv_bps,
            thermal_c=None,
            capabilities=SnapshotCapabilities(thermal_c=False, disk_queue=False, per_disk_io=False),
        )

    def list_processes(self) -> List[ProcessSample]:
        """Prime CPU counters, short sleep, then read per-process CPU%."""
        procs = []
        for p in psutil.process_iter(["pid", "name", "ppid", "num_threads"]):
            try:
                p.cpu_percent(interval=None)
                procs.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        time.sleep(0.1)

        out: List[ProcessSample] = []
        for p in procs:
            try:
                cpu = float(p.cpu_percent(interval=None))
                mem = p.memory_info()
                rss = int(mem.rss)
                pid = int(p.pid)
                name = str(p.name() or "")
                ppid = p.ppid() if p.ppid() is not None else None
                nt = p.num_threads()
                out.append(
                    ProcessSample(
                        pid=pid,
                        parent_pid=int(ppid) if ppid is not None else None,
                        name=name,
                        cpu_pct=cpu,
                        rss_bytes=rss,
                        thread_count=int(nt) if nt is not None else None,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        out.sort(key=lambda s: s.cpu_pct, reverse=True)
        return out[: self._process_limit]
