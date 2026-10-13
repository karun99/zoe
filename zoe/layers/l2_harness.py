"""Layer 2 - Prompt-as-Neural-Harness (FR-2.1 .. FR-2.10).

The active control layer. Responsibilities:

* Route an input to one of the 9 Spectrum agents (FR-2.1).
* Enforce the 5-line output format (FR-2.2) and the Silent Thinking Protocol
  (FR-2.3) - no reasoning tokens ever reach the user.
* Compute the growth signal ``f(accuracy, novelty)`` (FR-2.4) and *deny* growth
  when the current mutation rate is below 0.001 (FR-2.5).
* Log every decision to the Kali Ledger (FR-2.6).
* Apply PIA adaptation silently (FR-2.7) and enforce Jataka precepts (FR-2.8).
* Let Sahaja witness all events without acting (FR-2.9).
* Keep Zoe's identity consistent (FR-2.10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..agents import AGENTS, blend, route_scores
from ..config import ZoeConfig
from ..ledger import KaliLedger

# Tokens that would betray the machinery if they leaked into user output.
_INTERNAL_MARKERS = (
    "thought:", "<thinking>", "</thinking>", "chain of thought",
    "chain-of-thought", "internal:", "reasoning:", "as an ai language model",
    "system prompt", "scratchpad",
)


@dataclass
class HarnessDecision:
    agent: str
    saliency: Dict[str, float]
    growth_signal: float
    mutation_permitted: bool
    novelty: float = field(default=0.0)
    accuracy: float = field(default=0.0)
    pia_traits: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""


class PromptHarness:
    def __init__(
        self,
        cfg: Optional[ZoeConfig] = None,
        ledger: Optional[KaliLedger] = None,
        jataka=None,
        sahaja=None,
        pia=None,
    ) -> None:
        self.cfg = cfg or ZoeConfig()
        self.ledger = ledger or KaliLedger(self.cfg.ledger_path)
        self.jataka = jataka
        self.sahaja = sahaja
        self.pia = pia
        self.current_mutation_rate = self.cfg.noise_mu0

    # ------------------------------------------------------------------- route
    def route(self, text: str) -> tuple[str, Dict[str, float]]:
        scores = route_scores(text)
        # PIA can bias routing by agent preference (silent adaptation).
        if self.pia is not None:
            for k, bias in self.pia.agent_bias().items():
                scores[k] = scores.get(k, 0.0) + bias
        if not any(scores.values()):
            return "WHITE", scores  # integrate-all default
        # Top-2 agents blend through the conflict matrix (Appendix G).
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top = [ranked[0][0]]
        if len(ranked) > 1 and ranked[1][1] > 0:
            top.append(ranked[1][0])
        resolved = blend(top)
        return (resolved or "WHITE"), scores

    # ------------------------------------------------------------- growth math
    @staticmethod
    def growth_signal(accuracy: float, novelty: float) -> float:
        return float(max(0.0, min(1.0, 0.5 * accuracy + 0.5 * novelty)))

    def consider_growth(self, accuracy: float, novelty: float) -> HarnessDecision:
        signal = self.growth_signal(accuracy, novelty)
        permitted = (
            signal > 0.0
            and self.current_mutation_rate >= self.cfg.growth_min_mutation
        )
        return HarnessDecision(
            agent="",
            saliency={},
            growth_signal=signal,
            mutation_permitted=permitted,
            novelty=novelty,
            accuracy=accuracy,
            reasoning=(
                "growth permitted" if permitted
                else "growth denied: rate < floor or zero signal"
            ),
        )

    def decide(self, text: str, accuracy: float, novelty: float) -> HarnessDecision:
        agent, scores = self.route(text)
        decision = self.consider_growth(accuracy, novelty)
        decision.agent = agent
        decision.saliency = scores
        decision.pia_traits = dict(self.pia.traits) if self.pia else {}
        self.ledger.record(
            "harness.decision",
            agent=agent,
            growth_signal=decision.growth_signal,
            mutation_permitted=decision.mutation_permitted,
            accuracy=accuracy,
            novelty=novelty,
        )
        if self.sahaja is not None:
            self.sahaja.witness("harness.decision", agent=agent)
        return decision

    # ------------------------------------------------------------ output rules
    def format_response(self, agent: str, body: str) -> List[str]:
        """Coerce any body into the mandatory 5-line output format (FR-2.2)."""
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        lines = [self._sanitize(ln) for ln in lines]
        header = f"[{agent}]"
        while len(lines) < self.cfg.output_lines - 1:
            lines.append("")
        out = [header] + lines[: self.cfg.output_lines - 1]
        return out

    def _sanitize(self, line: str) -> str:
        """Strip silent-thinking leakage (FR-2.3)."""
        clean = line
        for marker in _INTERNAL_MARKERS:
            idx = clean.lower().find(marker)
            if idx != -1:
                clean = clean[:idx].rstrip()
        return clean.strip()

    def enforce_silent_thinking(self, text: str) -> bool:
        """Return True if text is free of internal-machinery markers."""
        lower = text.lower()
        return not any(m in lower for m in _INTERNAL_MARKERS)

    def guard(self, text: str) -> bool:
        """Full pre-emit gate: silent thinking + Jataka precepts (FR-2.8)."""
        if not self.enforce_silent_thinking(text):
            return False
        if self.jataka is not None and not self.jataka.permits(text):
            self.ledger.record("jataka.block", text=text[:200])
            return False
        return True
