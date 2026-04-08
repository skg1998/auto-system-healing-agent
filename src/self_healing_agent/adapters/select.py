"""Composition root: pick psutil-backed adapter for the current OS."""

from __future__ import annotations

import sys

from self_healing_agent.adapters.psutil_adapter import PsutilAdapter


def build_psutil_adapter() -> PsutilAdapter:
    """
    OS-specific psutil adapters: Linux (thermal + ranking), macOS (thermal), else baseline.
    """
    if sys.platform.startswith("linux"):
        from self_healing_agent.adapters.linux.psutil_linux import LinuxPsutilAdapter

        return LinuxPsutilAdapter()
    if sys.platform == "darwin":
        from self_healing_agent.adapters.darwin.psutil_darwin import DarwinPsutilAdapter

        return DarwinPsutilAdapter()
    return PsutilAdapter()
