"""Shared best-effort CPU thermal (°C) via psutil — Linux/macOS when sensors work."""

from __future__ import annotations

from typing import Optional

import psutil


def first_cpu_thermal_celsius() -> Optional[float]:
    try:
        temps = psutil.sensors_temperatures()  # type: ignore[attr-defined]
    except (NotImplementedError, AttributeError, OSError, RuntimeError):
        return None
    if not temps:
        return None
    for _label, entries in temps.items():
        for e in entries:
            cur = getattr(e, "current", None)
            if cur is not None and cur > 0:
                return float(cur)
    return None
