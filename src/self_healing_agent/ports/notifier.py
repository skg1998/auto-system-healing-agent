from __future__ import annotations

from typing import Protocol, Sequence

from self_healing_agent.core.detection import DetectionSignal
from self_healing_agent.core.diagnosis import DiagnosisHypothesis


class INotifier(Protocol):
    """Port: surface alerts to the user (log, toast, tray, etc.)."""

    def notify(self, signal: DetectionSignal) -> None: ...

    def notify_diagnosis(self, hypotheses: Sequence[DiagnosisHypothesis]) -> None: ...
