"""The 9 Spectrum agents (Appendix F) and their conflict matrix (Appendix G).

Agents are the routing targets of the L2 harness. Each carries an emotion, a
"thinking hat" verb, a mimic verb, and an avatar expression/voice used by L6.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class SpectrumAgent:
    key: str          # e.g. "RED"
    glyph: str        # e.g. "RED" rendered with a color by the UI
    color: str        # UI color name
    emotion: str
    thinking_hat: str
    mimic: str
    expression: str
    voice: str


AGENTS: Dict[str, SpectrumAgent] = {
    "RED": SpectrumAgent("RED", "RED", "red", "Rage", "anger is truth", "destroy",
                         "tension, furrowed brow", "sharp, urgent"),
    "ORANGE": SpectrumAgent("ORANGE", "ORANGE", "orange", "Avarice", "mine vs yours",
                            "acquire", "grasping gestures", "eager"),
    "YELLOW": SpectrumAgent("YELLOW", "YELLOW", "yellow", "Fear", "fear controls",
                            "intimidate", "alert posture", "cautious"),
    "GREEN": SpectrumAgent("GREEN", "GREEN", "green", "Willpower", "will overcomes",
                           "construct", "steady gaze", "calm, resolute"),
    "BLUE": SpectrumAgent("BLUE", "BLUE", "blue", "Hope", "hope endures",
                          "inspire", "soft eyes, open posture", "warm"),
    "INDIGO": SpectrumAgent("INDIGO", "INDIGO", "indigo", "Compassion",
                            "all deserve mercy", "empathize",
                            "gentle, empathetic tilt", "soft"),
    "VIOLET": SpectrumAgent("VIOLET", "VIOLET", "violet", "Love", "love protects",
                            "bind", "serene, open arms", "loving"),
    "BLACK": SpectrumAgent("BLACK", "BLACK", "black", "Death", "emotion is weakness",
                           "drain", "still, neutral", "flat"),
    "WHITE": SpectrumAgent("WHITE", "WHITE", "white", "Life", "balance of all",
                           "create/heal", "balanced, radiant", "harmonious"),
}

#: Opposites cancel each other out (Appendix G).
OPPOSITE: List[Tuple[str, str]] = [
    ("RED", "VIOLET"),
    ("ORANGE", "INDIGO"),
    ("YELLOW", "BLUE"),
    ("BLACK", "WHITE"),
]

#: Adjacent agents synergize.
ADJACENT: List[Tuple[str, str]] = [
    ("GREEN", "BLUE"),
    ("RED", "YELLOW"),
    ("ORANGE", "RED"),
    ("INDIGO", "VIOLET"),
]

#: Keyword -> agent saliency table used by the deterministic router. Order does
#: not matter; scores accumulate.
_KEYWORDS: Dict[str, List[str]] = {
    "RED": ["destroy", "attack", "threat", "urgent", "danger", "error", "crash"],
    "ORANGE": ["acquire", "buy", "budget", "cost", "money", "optimize", "trade"],
    "YELLOW": ["risk", "warn", "unsafe", "fear", "prevent", "caution"],
    "GREEN": ["build", "construct", "implement", "plan", "fix", "code", "solve"],
    "BLUE": ["help", "hope", "inspire", "guide", "explain", "teach", "support"],
    "INDIGO": ["care", "empathy", "patient", "sorry", "compassion", "listen"],
    "VIOLET": ["love", "protect", "relationship", "together", "trust", "bond"],
    "BLACK": ["stop", "end", "remove", "silence", "ignore", "delete"],
    "WHITE": ["balance", "summarize", "integrate", "overview", "harmonize", "all"],
}


def route_scores(text: str) -> Dict[str, float]:
    """Deterministic keyword saliency over the 9 agents."""
    lower = text.lower()
    scores = {k: 0.0 for k in AGENTS}
    for key, words in _KEYWORDS.items():
        for w in words:
            if w in lower:
                scores[key] += 1.0
    return scores


def resolve_pair(a: str, b: str) -> str | None:
    """Resolve a two-agent blend.

    Returns the winning agent key, ``None`` if the pair cancels (opposites), or
    the synergized higher-salience agent for adjacent pairs. Unknown pairs fall
    back to WHITE (which integrates all).
    """
    if a == b:
        return a  # SAME stacks - power multiplies
    pair = {a, b}
    for x, y in OPPOSITE:
        if {x, y} == pair:
            return None
    for x, y in ADJACENT:
        if {x, y} == pair:
            return a  # caller keeps the higher-salience member of the pair
    return "WHITE"


def blend(keys: List[str]) -> str | None:
    """Reduce an arbitrary set of agent keys to a single resolved agent."""
    keys = [k for k in keys if k in AGENTS]
    if not keys:
        return "WHITE"
    result = keys[0]
    for nxt in keys[1:]:
        r = resolve_pair(result, nxt)
        if r is None:
            return None
        result = r
    return result
