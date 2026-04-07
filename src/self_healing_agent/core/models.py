from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class SnapshotCapabilities:
    """What signals are present in this snapshot (adapters may omit unsupported metrics)."""

    thermal_c: bool = False
    disk_queue: bool = False
    per_disk_io: bool = False


@dataclass(frozen=True, slots=True)
class SystemSnapshot:
    """Normalized system-wide metrics — core logic depends only on this shape."""

    timestamp_monotonic_s: float
    cpu_total_pct: float
    mem_used_bytes: int
    mem_total_bytes: int
    swap_used_bytes: Optional[int]
    disk_read_bps: Optional[float]
    disk_write_bps: Optional[float]
    net_sent_bps: Optional[float]
    net_recv_bps: Optional[float]
    thermal_c: Optional[float]
    capabilities: SnapshotCapabilities


@dataclass(frozen=True, slots=True)
class ProcessSample:
    """One process at one instant — normalized for detection/diagnosis."""

    pid: int
    parent_pid: Optional[int]
    name: str
    cpu_pct: float
    rss_bytes: int
    thread_count: Optional[int]
