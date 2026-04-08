"""Linux-specific filters for process ranking (kernel noise vs user workloads)."""

from __future__ import annotations

from typing import List

from self_healing_agent.core.models import ProcessSample

# Parent of kernel threads — rarely a useful “top CPU app” target.
_LINUX_SKIP_NAMES_LOWER = frozenset(
    {
        "kthreadd",
    }
)


def should_skip_linux_ranking(name: str) -> bool:
    n = (name or "").strip().lower()
    return n in _LINUX_SKIP_NAMES_LOWER


def filter_linux_process_ranking(samples: List[ProcessSample]) -> List[ProcessSample]:
    """Drop kernel-only noise; keeps kworkers visible (they can explain I/O wait)."""
    return [s for s in samples if not should_skip_linux_ranking(s.name)]
