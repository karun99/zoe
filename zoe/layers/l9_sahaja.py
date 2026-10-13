"""Layer 9 - Sahaja, the silent witness (FR-2.9).

Sahaja observes and records every event, but never acts. It has no write path
into routing, growth, or generation - the ``witness`` method is the entire API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class WitnessRecord:
    event: str
    detail: Dict[str, Any] = field(default_factory=dict)


class Sahaja:
    def __init__(self) -> None:
        self.records: List[WitnessRecord] = []

    def witness(self, event: str, **detail: Any) -> None:
        self.records.append(WitnessRecord(event=event, detail=detail))

    def count(self, event: str | None = None) -> int:
        if event is None:
            return len(self.records)
        return sum(1 for r in self.records if r.event == event)

    def events(self) -> List[str]:
        return [r.event for r in self.records]

    # Sahaja never influences the system; this method exists to make that
    # contract explicit in tests and reviews.
    def act(self, *_args: Any, **_kwargs: Any) -> None:
        return None
