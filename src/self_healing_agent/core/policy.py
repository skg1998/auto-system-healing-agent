"""Policy: map detection + diagnosis to action intents (notify, suggest, soft/hard)."""

from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Sequence

from self_healing_agent.config.models import PolicySettings
from self_healing_agent.core.buffer import TickRecord
from self_healing_agent.core.detection import DetectionSignal
from self_healing_agent.core.diagnosis import DiagnosisHypothesis
from self_healing_agent.core.models import ProcessSample


@dataclass(frozen=True, slots=True)
class NotifySignalsIntent:
    signals: tuple[DetectionSignal, ...]


@dataclass(frozen=True, slots=True)
class NotifyDiagnosisIntent:
    hypotheses: tuple[DiagnosisHypothesis, ...]


@dataclass(frozen=True, slots=True)
class SuggestIntent:
    text: str


@dataclass(frozen=True, slots=True)
class SoftReniceIntent:
    pid: int
    process_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class HardTerminateIntent:
    pid: int
    process_name: str
    reason: str


TickAction = (
    NotifySignalsIntent
    | NotifyDiagnosisIntent
    | SuggestIntent
    | SoftReniceIntent
    | HardTerminateIntent
)


def _norm_name(name: str) -> str:
    return name.strip().lower()


def is_protected_process(
    sample: ProcessSample,
    protected_names: frozenset[str],
) -> bool:
    return _norm_name(sample.name) in protected_names


class PolicyEngine:
    """
    Emits ordered intents per tick. Notifications always flow when inputs exist;
    soft/hard actions are gated by config, confidence, protected lists, and cooldown.
    """

    def __init__(self, settings: PolicySettings) -> None:
        self._settings = settings
        self._protected = frozenset(_norm_name(x) for x in settings.protected_process_names if x)
        self._hard_kill_times: Deque[float] = deque()

    def decide(
        self,
        *,
        signals: Sequence[DetectionSignal],
        hypotheses: Sequence[DiagnosisHypothesis],
        latest: TickRecord | None,
        monotonic_now: float | None = None,
    ) -> List[TickAction]:
        now = monotonic_now if monotonic_now is not None else time.monotonic()
        out: List[TickAction] = []

        if signals:
            out.append(NotifySignalsIntent(tuple(signals)))
        if hypotheses:
            out.append(NotifyDiagnosisIntent(tuple(hypotheses)))

        if not self._settings.enabled:
            return out

        self._append_suggestions(hypotheses, out)

        top = _top_cpu_process(latest.processes if latest is not None else ())
        if top is None:
            return out

        soft: SoftReniceIntent | None = None
        if self._settings.soft_actions_enabled:
            soft = self._maybe_soft_renice(signals, hypotheses, top)
            if soft is not None:
                out.append(soft)

        # Never soft-renice and terminate the same target in one tick; soft wins.
        if self._settings.hard_kill_enabled and soft is None:
            hard = self._maybe_hard_kill(hypotheses, top, now)
            if hard is not None:
                out.append(hard)

        return out

    def _append_suggestions(
        self,
        hypotheses: Sequence[DiagnosisHypothesis],
        out: List[TickAction],
    ) -> None:
        if not hypotheses or not self._settings.suggestions_enabled:
            return
        seen: set[str] = set()
        for h in hypotheses:
            t = _suggestion_for_hypothesis(h.hypothesis_id)
            if t and t not in seen:
                seen.add(t)
                out.append(SuggestIntent(t))

    def _maybe_soft_renice(
        self,
        signals: Sequence[DetectionSignal],
        hypotheses: Sequence[DiagnosisHypothesis],
        top: ProcessSample,
    ) -> SoftReniceIntent | None:
        if not any(s.kind == "high_system_cpu" for s in signals):
            return None
        if top.pid == os.getpid():
            return None
        if is_protected_process(top, self._protected):
            return None
        if top.cpu_pct < self._settings.min_cpu_share_for_soft:
            return None
        best = _best_cpu_hypothesis(hypotheses)
        if best is None or best.confidence < self._settings.min_confidence_for_soft:
            return None
        if not _hypothesis_id_allows_cpu_action(best.hypothesis_id):
            return None
        return SoftReniceIntent(
            pid=top.pid,
            process_name=top.name,
            reason=(
                f"policy soft renice: hypothesis={best.hypothesis_id} "
                f"conf={best.confidence:.2f} cpu_share={top.cpu_pct:.1f}%"
            ),
        )

    def _maybe_hard_kill(
        self,
        hypotheses: Sequence[DiagnosisHypothesis],
        top: ProcessSample,
        now: float,
    ) -> HardTerminateIntent | None:
        if top.pid == os.getpid():
            return None
        if is_protected_process(top, self._protected):
            return None
        if top.cpu_pct < self._settings.min_cpu_share_for_hard:
            return None
        best = _best_cpu_hypothesis(hypotheses)
        if best is None or best.confidence < self._settings.min_confidence_for_hard:
            return None
        if not _hypothesis_id_allows_cpu_action(best.hypothesis_id):
            return None

        window = float(self._settings.hard_kill_cooldown_seconds)
        max_per_window = self._settings.hard_kill_max_per_window
        while self._hard_kill_times and now - self._hard_kill_times[0] > window:
            self._hard_kill_times.popleft()
        if len(self._hard_kill_times) >= max_per_window:
            return None

        return HardTerminateIntent(
            pid=top.pid,
            process_name=top.name,
            reason=(
                f"policy hard terminate: hypothesis={best.hypothesis_id} "
                f"conf={best.confidence:.2f} cpu_share={top.cpu_pct:.1f}%"
            ),
        )

    def record_hard_kill_executed(self, monotonic_now: float | None = None) -> None:
        """Call after a successful terminate() so cooldown windows apply."""
        self._hard_kill_times.append(
            monotonic_now if monotonic_now is not None else time.monotonic()
        )


def _top_cpu_process(processes: tuple[ProcessSample, ...]) -> ProcessSample | None:
    if not processes:
        return None
    return max(processes, key=lambda p: p.cpu_pct)


def _best_cpu_hypothesis(
    hypotheses: Sequence[DiagnosisHypothesis],
) -> DiagnosisHypothesis | None:
    cpu_kinds = (
        "cpu_disk_net",
        "cpu_disk_io",
        "cpu_network",
        "cpu_compute_bound",
        "cpu_memory_combined",
    )
    candidates = [h for h in hypotheses if h.hypothesis_id in cpu_kinds]
    if not candidates:
        return None
    return max(candidates, key=lambda h: h.confidence)


def _hypothesis_id_allows_cpu_action(hypothesis_id: str) -> bool:
    return hypothesis_id in {
        "cpu_disk_net",
        "cpu_disk_io",
        "cpu_network",
        "cpu_compute_bound",
        "cpu_memory_combined",
    }


def _suggestion_for_hypothesis(hypothesis_id: str) -> str | None:
    return {
        "cpu_disk_net": "Heavy disk and network load: pause sync/backup jobs if possible, then retry.",
        "cpu_disk_io": "High disk I/O: wait for indexing/builds to finish or move work off peak hours.",
        "cpu_network": "High network use: check large downloads/sync; pause if the machine is unresponsive.",
        "cpu_compute_bound": "CPU-bound load: close unused apps or restart the top CPU consumer if safe.",
        "cpu_memory_combined": "CPU and memory pressure: close heavy apps/tabs; restart runaway services if needed.",
        "memory_rss": "Memory pressure: close unused tabs/windows or restart the largest application.",
    }.get(hypothesis_id)
