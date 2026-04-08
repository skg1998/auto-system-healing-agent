"""Sustained-condition detection over TickBuffer (pure core logic)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from self_healing_agent.config.models import DetectionSettings
from self_healing_agent.core.buffer import TickBuffer, TickRecord


@dataclass(frozen=True, slots=True)
class DetectionSignal:
    """Emitted when a sustained threshold is first crossed (edge per episode)."""

    kind: str
    message: str
    severity: str = "warning"


class DetectionEngine:
    """
    Evaluates sustained CPU / memory pressure.
    Notifies once per episode: when condition clears, the next crossing can notify again.
    """

    def __init__(self, settings: DetectionSettings) -> None:
        self._settings = settings
        self._cpu_episode: bool = False
        self._mem_episode: bool = False

    def evaluate(self, buffer: TickBuffer) -> List[DetectionSignal]:
        if not self._settings.enabled:
            return []

        out: List[DetectionSignal] = []
        out.extend(self._eval_cpu(buffer))
        out.extend(self._eval_memory(buffer))
        return out

    def _eval_cpu(self, buffer: TickBuffer) -> List[DetectionSignal]:
        d = self._settings
        thresh = d.system_cpu_pct_above
        if thresh is None:
            return []
        k = d.system_cpu_sustained_ticks
        sustained = self._last_k_all(buffer, k, self._cpu_above(thresh))
        if sustained:
            if not self._cpu_episode:
                self._cpu_episode = True
                cur = 0.0
                latest = buffer.latest()
                if latest is not None:
                    cur = latest.snapshot.cpu_total_pct
                return [
                    DetectionSignal(
                        kind="high_system_cpu",
                        message=(
                            f"System CPU above {thresh}% for {k} consecutive ticks "
                            f"(current {cur:.1f}%)"
                        ),
                        severity="warning",
                    )
                ]
            return []
        self._cpu_episode = False
        return []

    def _eval_memory(self, buffer: TickBuffer) -> List[DetectionSignal]:
        d = self._settings
        thresh = d.memory_pct_above
        if thresh is None:
            return []
        k = d.memory_sustained_ticks

        def mem_above(rec: TickRecord) -> bool:
            t = rec.snapshot.mem_total_bytes
            if t <= 0:
                return False
            pct = 100.0 * rec.snapshot.mem_used_bytes / float(t)
            return pct > thresh

        sustained = self._last_k_all(buffer, k, mem_above)
        if sustained:
            if not self._mem_episode:
                self._mem_episode = True
                latest = buffer.latest()
                pct_s = ""
                if latest is not None and latest.snapshot.mem_total_bytes > 0:
                    p = (
                        100.0
                        * latest.snapshot.mem_used_bytes
                        / float(latest.snapshot.mem_total_bytes)
                    )
                    pct_s = f" (current {p:.1f}%)"
                return [
                    DetectionSignal(
                        kind="high_memory_pressure",
                        message=f"Memory use above {thresh}% for {k} consecutive ticks{pct_s}",
                        severity="warning",
                    )
                ]
            return []
        self._mem_episode = False
        return []

    @staticmethod
    def _last_k_all(
        buffer: TickBuffer,
        k: int,
        pred: Callable[[TickRecord], bool],
    ) -> bool:
        if len(buffer) < k:
            return False
        recent = list(buffer.iter_recent(last_n=k))
        return all(pred(r) for r in recent)

    @staticmethod
    def _cpu_above(threshold: float):
        def f(rec: TickRecord) -> bool:
            return rec.snapshot.cpu_total_pct > threshold

        return f
