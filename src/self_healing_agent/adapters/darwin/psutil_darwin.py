"""macOS (Darwin) psutil adapter: same ports + thermal when psutil can read sensors."""

from __future__ import annotations

from dataclasses import replace

from self_healing_agent.adapters.psutil_adapter import PsutilAdapter
from self_healing_agent.adapters.thermal_psutil import first_cpu_thermal_celsius
from self_healing_agent.core.models import SystemSnapshot


class DarwinPsutilAdapter(PsutilAdapter):
    """
    psutil on Darwin: adds CPU thermal when available.

    Limitations: ``sensors_temperatures`` may be empty without extra setup, inside VMs,
    or due to macOS permissions; ``kernel_task`` CPU can reflect memory pressure — we do
    not hide it from rankings.
    """

    def collect_system(self) -> SystemSnapshot:
        snap = super().collect_system()
        t = first_cpu_thermal_celsius()
        if t is None:
            return snap
        caps = replace(snap.capabilities, thermal_c=True)
        return replace(snap, thermal_c=t, capabilities=caps)
