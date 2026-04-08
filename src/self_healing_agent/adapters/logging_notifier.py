from __future__ import annotations

import logging

from typing import Sequence

from self_healing_agent.core.detection import DetectionSignal
from self_healing_agent.core.diagnosis import DiagnosisHypothesis


class LoggingNotifier:
    """Default notifier: structured log lines (works everywhere)."""

    def __init__(self, dry_run: bool = False) -> None:
        self._dry_run = dry_run
        self._log = logging.getLogger("self_healing_agent.notify")

    def notify(self, signal: DetectionSignal) -> None:
        prefix = "[DRY] would notify: " if self._dry_run else ""
        self._log.warning("%s[%s] %s", prefix, signal.kind, signal.message)

    def notify_diagnosis(self, hypotheses: Sequence[DiagnosisHypothesis]) -> None:
        prefix = "[DRY] would notify diagnosis: " if self._dry_run else ""
        for h in hypotheses:
            ev = "; ".join(f"{e.ref_id}={e.description}" for e in h.evidence)
            self._log.warning(
                "%s[diagnosis] %s conf=%.2f — %s | evidence: %s",
                prefix,
                h.hypothesis_id,
                h.confidence,
                h.summary,
                ev,
            )
