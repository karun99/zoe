"""Layer 8 - Companion Mode (FR-C.1 .. FR-C.10).

Screen/browser awareness for virtual-pet behaviour. Privacy is load-bearing:
secrets are redacted before anything is used (FR-C.3), nothing is persisted
(FR-C.7), keystrokes are never recorded (FR-C.8), activation is explicit and
visible (FR-C.9, FR-C.10).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..config import ZoeConfig
from ..ledger import KaliLedger

# --- redaction patterns (FR-C.3) -------------------------------------------
_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "card": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "api_key": re.compile(r"\b(?:sk|ghp|gho|api|token)[-_][A-Za-z0-9]{12,}\b"),
    "password": re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+"),
}

REDACTION_MASK = "[REDACTED]"

STATE_TRANSITIONS = {
    "idle": {"curious", "resting"},
    "curious": {"focused", "playful", "idle"},
    "focused": {"idle", "curious"},
    "playful": {"focused", "idle"},
    "resting": {"idle", "curious"},
}


@dataclass
class Observation:
    encrypted: bool
    text: str
    state: str
    novelty: float
    active_window: str = ""


class CompanionMode:
    def __init__(self, cfg: Optional[ZoeConfig] = None,
                 ledger: Optional[KaliLedger] = None) -> None:
        self.cfg = cfg or ZoeConfig()
        self.ledger = ledger or KaliLedger(self.cfg.ledger_path)
        self.active = False
        self.indicator_visible = False
        self.state = "idle"
        self._last_window: Optional[str] = None
        self._same_window_count = 0
        self._observations: List[Observation] = []
        self.redactions = 0
        self.keystrokes_recorded = 0  # invariant: always 0

    # ------------------------------------------------------------- lifecycle
    def start(self) -> None:
        self.active = True
        self.indicator_visible = True  # FR-C.9
        self.ledger.record("companion.start")

    def stop(self) -> None:
        self.active = False
        self.indicator_visible = False
        # FR-C.7: nothing persisted.
        self._observations.clear()
        self.ledger.record("companion.stop")

    def observe(self, screen_text: str, active_window: str = "",
                novelty: float = 0.0) -> Observation:
        if not self.active:
            raise RuntimeError("companion mode is not active")
        redacted = self.redact(screen_text)
        self._update_state(active_window, novelty)
        obs = Observation(
            encrypted=False,
            text=redacted,
            state=self.state,
            novelty=novelty,
            active_window=active_window,
        )
        # Store only transiently; stop() clears this (FR-C.7).
        self._observations.append(obs)
        self.ledger.record("companion.observe", window=active_window,
                           state=self.state, novelty=novelty)
        return obs

    def _update_state(self, active_window: str, novelty: float) -> None:
        if active_window != self._last_window:
            self._same_window_count = 0
            next_state = "curious"
        else:
            self._same_window_count += 1
            if self._same_window_count >= 120:  # >10 min at 5s intervals
                next_state = "focused"
            elif novelty > 0.7:
                next_state = "playful"
            else:
                next_state = self.state
        if next_state in STATE_TRANSITIONS.get(self.state, set()) or next_state == self.state:
            self.state = next_state
        else:
            self.state = "curious"
        self._last_window = active_window

    # -------------------------------------------------------------- privacy
    def redact(self, text: str) -> str:
        result = text
        for name, pat in _PATTERNS.items():
            result, n = pat.subn(REDACTION_MASK, result)
            self.redactions += n
        return result

    # --------------------------------------------------------- browser read
    def read_active_tab(self, tab_title: str) -> str:
        """Return a redacted, non-persistent summary of the active tab."""
        return self.redact(tab_title)
