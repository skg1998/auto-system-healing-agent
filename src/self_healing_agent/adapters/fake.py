from __future__ import annotations

from typing import List

from self_healing_agent.core.models import ProcessSample, SnapshotCapabilities, SystemSnapshot


class FakeMetricsAdapter:
    """Test double: deterministic metrics without touching the OS."""

    def __init__(
        self,
        snapshot: SystemSnapshot | None = None,
        processes: List[ProcessSample] | None = None,
    ) -> None:
        self._snapshot = snapshot or SystemSnapshot(
            timestamp_monotonic_s=0.0,
            cpu_total_pct=10.0,
            mem_used_bytes=4_000_000_000,
            mem_total_bytes=8_000_000_000,
            swap_used_bytes=0,
            disk_read_bps=1.0,
            disk_write_bps=2.0,
            net_sent_bps=3.0,
            net_recv_bps=4.0,
            thermal_c=None,
            capabilities=SnapshotCapabilities(),
        )
        self._processes = tuple(processes or ())

    def collect_system(self) -> SystemSnapshot:
        return self._snapshot

    def list_processes(self) -> List[ProcessSample]:
        return list(self._processes)
