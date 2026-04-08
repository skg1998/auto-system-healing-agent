"""OS actions via psutil (soft renice / terminate)."""

from __future__ import annotations

import logging
import os

import psutil

from self_healing_agent.core.policy import HardTerminateIntent, SoftReniceIntent

log = logging.getLogger(__name__)


class PsutilActionExecutor:
    """Best-effort process actions; failures are logged, not raised."""

    def soft_renice(self, intent: SoftReniceIntent, *, dry_run: bool) -> bool:
        if intent.pid in (0, 4) or intent.pid == os.getpid():
            return False
        if dry_run:
            log.warning(
                "[DRY] would lower CPU priority pid=%s (%s)",
                intent.pid,
                intent.process_name,
            )
            return True
        try:
            p = psutil.Process(intent.pid)
            if os.name == "nt":
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            else:
                cur = p.nice()
                p.nice(min(cur + 5, 19))
            log.warning(
                "lowered CPU priority pid=%s (%s) — %s",
                intent.pid,
                intent.process_name,
                intent.reason,
            )
            return True
        except (psutil.Error, PermissionError, OSError) as e:
            log.warning("soft renice failed pid=%s: %s", intent.pid, e)
            return False

    def hard_terminate(self, intent: HardTerminateIntent, *, dry_run: bool) -> bool:
        if intent.pid in (0, 4) or intent.pid == os.getpid():
            return False
        if dry_run:
            log.warning(
                "[DRY] would terminate pid=%s (%s)",
                intent.pid,
                intent.process_name,
            )
            return True
        try:
            psutil.Process(intent.pid).terminate()
            log.warning(
                "terminated pid=%s (%s) — %s",
                intent.pid,
                intent.process_name,
                intent.reason,
            )
            return True
        except (psutil.Error, PermissionError, OSError) as e:
            log.warning("terminate failed pid=%s: %s", intent.pid, e)
            return False
