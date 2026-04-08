"""Helpers for per-process CPU semantics (psutil vs multi-core vs OS quirks)."""

from __future__ import annotations

# Windows: not a real workload — idle time is attributed here and dominates rankings.
_SKIP_PROCESS_NAMES_LOWER = frozenset(
    {
        "system idle process",
    }
)


def should_skip_process_for_ranking(pid: int, name: str) -> bool:
    """Exclude pseudo/idle processes from 'top by CPU' lists."""
    n = (name or "").strip().lower()
    if n in _SKIP_PROCESS_NAMES_LOWER:
        return True
    # Windows idle is typically PID 0 with the name above; keep explicit for safety.
    if pid == 0 and "idle" in n:
        return True
    return False


def normalize_cpu_to_machine_share(raw_percent: float, logical_cpu_count: int) -> float:
    """
    psutil per-process cpu_percent can exceed 100 on multi-core hosts: it sums
    usage across logical CPUs. Divide by logical CPU count to get an approximate
    'share of total machine' in the 0–100 range (like Task Manager's default column).
    """
    n = logical_cpu_count if logical_cpu_count and logical_cpu_count > 0 else 1
    return float(raw_percent) / float(n)
