from __future__ import annotations

from typing import Tuple

from self_healing_agent.core.buffer import TickBuffer, TickRecord
from self_healing_agent.core.models import ProcessSample, SystemSnapshot
from self_healing_agent.ports.collectors import IMetricsCollector, IProcessInspector


class Pipeline:
    """
    One tick: collect system snapshot + processes, append to buffer.
    Detection/diagnosis/policy plug in later without changing adapters.
    """

    def __init__(
        self,
        metrics: IMetricsCollector,
        processes: IProcessInspector,
        buffer: TickBuffer,
    ) -> None:
        self._metrics = metrics
        self._processes = processes
        self._buffer = buffer

    def tick(self) -> TickRecord:
        snapshot = self._metrics.collect_system()
        plist = self._processes.list_processes()
        record = TickRecord(snapshot=snapshot, processes=tuple(plist))
        self._buffer.append(record)
        return record

    def tick_raw(self) -> Tuple[SystemSnapshot, Tuple[ProcessSample, ...]]:
        """Same as tick but returns plain tuples (handy for tests)."""
        rec = self.tick()
        return rec.snapshot, rec.processes
