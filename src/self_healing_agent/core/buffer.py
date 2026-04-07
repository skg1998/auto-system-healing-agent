from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterator, List, Optional

from self_healing_agent.core.models import ProcessSample, SystemSnapshot


@dataclass(frozen=True, slots=True)
class TickRecord:
    """One pipeline tick: system snapshot + process list at that instant."""

    snapshot: SystemSnapshot
    processes: tuple[ProcessSample, ...]


class TickBuffer:
    """Rolling history of recent ticks for sustained-condition detection (bounded memory)."""

    def __init__(self, maxlen: int = 120) -> None:
        if maxlen < 1:
            raise ValueError("maxlen must be >= 1")
        self._maxlen = maxlen
        self._ticks: Deque[TickRecord] = deque(maxlen=maxlen)

    def __len__(self) -> int:
        return len(self._ticks)

    @property
    def maxlen(self) -> int:
        return self._maxlen

    def append(self, record: TickRecord) -> None:
        self._ticks.append(record)

    def latest(self) -> Optional[TickRecord]:
        if not self._ticks:
            return None
        return self._ticks[-1]

    def iter_recent(self, last_n: Optional[int] = None) -> Iterator[TickRecord]:
        """Oldest → newest among the last `last_n` ticks (default: all)."""
        items: List[TickRecord] = list(self._ticks)
        if last_n is not None:
            items = items[-last_n:]
        yield from items
