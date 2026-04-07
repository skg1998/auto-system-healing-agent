from __future__ import annotations

from typing import List, Protocol

from self_healing_agent.core.models import ProcessSample, SystemSnapshot


class IMetricsCollector(Protocol):
    """Port: system-wide metrics (CPU, memory, disk/net aggregates, optional thermal)."""

    def collect_system(self) -> SystemSnapshot:
        """Return a normalized snapshot for the current instant."""
        ...


class IProcessInspector(Protocol):
    """Port: per-process samples (CPU, RSS, threads, etc.)."""

    def list_processes(self) -> List[ProcessSample]:
        """Return process rows; may be capped by adapter for performance."""
        ...
