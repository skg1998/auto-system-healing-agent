"""Multi-signal diagnosis: hypotheses with confidence and evidence (pure core)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from self_healing_agent.config.models import DiagnosisSettings
from self_healing_agent.core.buffer import TickBuffer, TickRecord
from self_healing_agent.core.detection import DetectionSignal
from self_healing_agent.core.models import ProcessSample


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """Pointer to a metric, process, or detection signal used in reasoning."""

    ref_id: str
    description: str


@dataclass(frozen=True, slots=True)
class DiagnosisHypothesis:
    """Ranked explanation for current signals; confidence is 0.0–1.0 (heuristic)."""

    hypothesis_id: str
    summary: str
    confidence: float
    evidence: tuple[EvidenceRef, ...]


class DiagnosisEngine:
    """
    Correlates detection signals with recent metrics (latest tick) and process list.
    Notify-first: produces structured hypotheses, no actions.
    """

    def __init__(self, settings: DiagnosisSettings) -> None:
        self._settings = settings

    def diagnose(
        self,
        buffer: TickBuffer,
        signals: Sequence[DetectionSignal],
    ) -> List[DiagnosisHypothesis]:
        if not self._settings.enabled or not signals:
            return []
        latest = buffer.latest()
        if latest is None:
            return []

        kinds = {s.kind for s in signals}
        out: List[DiagnosisHypothesis] = []

        if "high_system_cpu" in kinds:
            out.append(self._hypothesis_cpu(latest, signals))

        if "high_memory_pressure" in kinds:
            out.append(self._hypothesis_memory(latest, signals))

        if "high_system_cpu" in kinds and "high_memory_pressure" in kinds:
            out.append(self._hypothesis_cpu_memory_combo(signals))

        out.sort(key=lambda h: h.confidence, reverse=True)
        return out

    def _hypothesis_cpu(
        self,
        latest: TickRecord,
        signals: Sequence[DetectionSignal],
    ) -> DiagnosisHypothesis:
        snap = latest.snapshot
        d_floor = self._settings.disk_io_high_bps
        n_floor = self._settings.net_io_high_bps

        disk_total = (snap.disk_read_bps or 0.0) + (snap.disk_write_bps or 0.0)
        net_total = (snap.net_sent_bps or 0.0) + (snap.net_recv_bps or 0.0)

        sig = next(s for s in signals if s.kind == "high_system_cpu")
        evidence: List[EvidenceRef] = [
            EvidenceRef("detection:high_system_cpu", sig.message),
            EvidenceRef(
                "metric:disk_rw_bps",
                f"Disk read+write total ≈ {disk_total:.0f} B/s",
            ),
            EvidenceRef(
                "metric:net_bps",
                f"Net sent+recv total ≈ {net_total:.0f} B/s",
            ),
        ]

        top = _top_process_by_cpu(latest.processes)
        if top is not None:
            evidence.append(
                EvidenceRef(
                    f"process:{top.pid}",
                    f"Largest CPU share: {top.name} ({top.cpu_pct:.1f}%)",
                )
            )

        if disk_total > d_floor and net_total > n_floor:
            summary = (
                "High CPU with elevated disk and network throughput — "
                "possible build, sync, backup, or data-heavy workload."
            )
            conf = 0.58
            hid = "cpu_disk_net"
        elif disk_total > d_floor:
            summary = (
                "High CPU with elevated disk I/O — "
                "indexing, build, or large file operations are plausible."
            )
            conf = 0.56
            hid = "cpu_disk_io"
        elif net_total > n_floor:
            summary = (
                "High CPU with elevated network traffic — "
                "streaming, sync, or network-bound work is plausible."
            )
            conf = 0.52
            hid = "cpu_network"
        else:
            summary = (
                "High CPU with relatively low disk/network in the latest sample — "
                "compute-bound work or a tight loop is plausible."
            )
            conf = 0.45
            hid = "cpu_compute_bound"

        if top is not None:
            summary = f"{summary} Dominant CPU consumer: {top.name} (pid {top.pid})."

        return DiagnosisHypothesis(
            hypothesis_id=hid,
            summary=summary,
            confidence=conf,
            evidence=tuple(evidence),
        )

    def _hypothesis_memory(
        self,
        latest: TickRecord,
        signals: Sequence[DetectionSignal],
    ) -> DiagnosisHypothesis:
        snap = latest.snapshot
        mem_pct = 0.0
        if snap.mem_total_bytes > 0:
            mem_pct = 100.0 * snap.mem_used_bytes / float(snap.mem_total_bytes)

        sig = next(s for s in signals if s.kind == "high_memory_pressure")
        evidence: List[EvidenceRef] = [
            EvidenceRef("detection:high_memory_pressure", sig.message),
            EvidenceRef("metric:mem_pct", f"Memory use ≈ {mem_pct:.1f}%"),
        ]

        top = _top_process_by_rss(latest.processes)
        if top is not None:
            evidence.append(
                EvidenceRef(
                    f"process:{top.pid}",
                    f"Largest RSS: {top.name} (~{top.rss_bytes // 1_000_000} MB)",
                )
            )

        summary = "Sustained memory pressure."
        if top is not None:
            summary = (
                f"Sustained memory pressure; largest resident set: {top.name} (pid {top.pid})."
            )

        return DiagnosisHypothesis(
            hypothesis_id="memory_rss",
            summary=summary,
            confidence=0.52,
            evidence=tuple(evidence),
        )

    def _hypothesis_cpu_memory_combo(
        self, signals: Sequence[DetectionSignal]
    ) -> DiagnosisHypothesis:
        evidence = [
            EvidenceRef("signal:high_system_cpu", "CPU threshold sustained"),
            EvidenceRef("signal:high_memory_pressure", "Memory threshold sustained"),
        ]
        for s in signals:
            evidence.append(EvidenceRef(f"detection:{s.kind}", s.message))

        return DiagnosisHypothesis(
            hypothesis_id="cpu_memory_combined",
            summary=(
                "CPU and memory alerts together — "
                "check for memory-heavy compute, browser tabs, or runaway services."
            ),
            confidence=0.62,
            evidence=tuple(evidence),
        )


def _top_process_by_cpu(
    processes: tuple[ProcessSample, ...],
) -> ProcessSample | None:
    if not processes:
        return None
    return max(processes, key=lambda p: p.cpu_pct)


def _top_process_by_rss(
    processes: tuple[ProcessSample, ...],
) -> ProcessSample | None:
    if not processes:
        return None
    return max(processes, key=lambda p: p.rss_bytes)
