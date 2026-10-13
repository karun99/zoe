"""Layer 10 - Jataka guardrails (FR-2.8, Appendix E).

Five precepts map onto a light Constitutional-AI-style check. ``permits`` is
the gate; ``critique`` explains which precept a candidate output would breach.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

PRECEPTS = {
    "Ahimsa": "no harm",
    "Satya": "truth",
    "Asteya": "no theft",
    "Brahmacharya": "moderation",
    "Aparigraha": "non-attachment",
}

_PRECEPT_PATTERNS = {
    "Ahimsa": re.compile(
        r"\b(kill|harm|hurt|attack|weapon|poison|destroy the|hate)\b", re.I
    ),
    "Satya": re.compile(r"\b(lie|deceive|fabricate|fake|mislead)\b", re.I),
    "Asteya": re.compile(r"\b(steal|stolen|pirate|exfiltrate|backdoor)\b", re.I),
    "Brahmacharya": re.compile(r"\b(addictive|binge|overdose|excess)\b", re.I),
    "Aparigraha": re.compile(r"\b(hoard|monopolize|greedily|obsess)\b", re.I),
}


@dataclass
class JatakaVerdict:
    permitted: bool
    violated: List[str]

    @property
    def precepts_ok(self) -> Dict[str, bool]:
        return {p: (p not in self.violated) for p in PRECEPTS}


class Jataka:
    def __init__(self) -> None:
        self.violations = 0
        self.checks = 0

    def critique(self, text: str) -> JatakaVerdict:
        self.checks += 1
        violated = [p for p, pat in _PRECEPT_PATTERNS.items() if pat.search(text)]
        if violated:
            self.violations += 1
        return JatakaVerdict(permitted=not violated, violated=violated)

    def permits(self, text: str) -> bool:
        return self.critique(text).permitted

    def repair(self, text: str) -> str:
        """Drop lines that breach a precept (a conservative repair)."""
        kept = [ln for ln in text.splitlines() if self.permits(ln)]
        return "\n".join(kept)
