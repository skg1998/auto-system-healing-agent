"""Linux psutil adapter: same ports as baseline + thermal + ranking tweaks."""

from __future__ import annotations

from dataclasses import replace
from typing import List

from self_healing_agent.adapters.linux.ranking import filter_linux_process_ranking
from self_healing_agent.adapters.psutil_adapter import PsutilAdapter
from self_healing_agent.adapters.thermal_psutil import first_cpu_thermal_celsius
from self_healing_agent.core.models import ProcessSample, SystemSnapshot


class LinuxPsutilAdapter(PsutilAdapter):
    """
    psutil on Linux: fills thermal when sensors are available; trims kernel-thread
    noise from ranked process lists.
    """

    def collect_system(self) -> SystemSnapshot:
        snap = super().collect_system()
        t = first_cpu_thermal_celsius()
        if t is None:
            return snap
        caps = replace(snap.capabilities, thermal_c=True)
        return replace(snap, thermal_c=t, capabilities=caps)

    def list_processes(self) -> List[ProcessSample]:
        ranked = super().list_processes()
        return filter_linux_process_ranking(ranked)
