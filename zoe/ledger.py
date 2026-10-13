"""Kali Ledger - append-only decision log (FR-2.6, FR-4.5, NFR-4.3).

Every consequential decision (routing, growth permit/deny, mutation, Dunce
patch, guardrail event) is written to a newline-delimited JSON ledger. The
ledger is the single source of truth for post-hoc audit and the premortem
detectors in the evaluation harness.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional


class KaliLedger:
    """Append-only JSONL ledger with an in-memory mirror for fast reads."""

    def __init__(self, path: str = ".kali-ledger/ledger.jsonl") -> None:
        self.path = path
        self._entries: List[Dict[str, Any]] = []
        directory = os.path.dirname(os.path.abspath(path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        # Truncate any stale ledger so a run starts clean.
        with open(self.path, "w", encoding="utf-8"):
            pass

    def record(self, event: str, **payload: Any) -> Dict[str, Any]:
        entry = {
            "ts": time.time(),
            "event": event,
            "payload": {k: _jsonable(v) for k, v in payload.items()},
        }
        self._entries.append(entry)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        return entry

    def entries(self, event: Optional[str] = None) -> List[Dict[str, Any]]:
        if event is None:
            return list(self._entries)
        return [e for e in self._entries if e["event"] == event]

    def count(self, event: Optional[str] = None) -> int:
        return len(self.entries(event))

    def tail(self, n: int = 5) -> List[Dict[str, Any]]:
        return self._entries[-n:]


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)
