"""Layer 4 - Kali (temporal gate) + Dunce (failure patching).

Kali controls *when* mutation happens (FR-4.1 .. FR-4.6); Dunce repairs bad
mutations by inverting their delta (FR-5.1 .. FR-5.4).

    LEARNING(10) -> AUDIT(3) -> GROWTH(2) -> REST(5)   [period 20]

Mutation is only permitted during GROWTH. The mutation rate follows the
temporal noise-reduction law ``mu = mu0 * exp(-lambda t) * (1 - A)`` and is
denied outright once it falls below 0.001.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from ..config import ZoeConfig
from ..ledger import KaliLedger

PHASES = ("LEARNING", "AUDIT", "GROWTH", "REST")


@dataclass
class KaliState:
    phase: str
    cycle_step: int
    mutation_rate: float
    permitted: bool = False


class Kali:
    def __init__(self, cfg: Optional[ZoeConfig] = None,
                 ledger: Optional[KaliLedger] = None) -> None:
        self.cfg = cfg or ZoeConfig()
        self.ledger = ledger or KaliLedger(self.cfg.ledger_path)
        self.step = 0
        self.decisions: List[Dict] = []
        # lineage tracks per-lineage growth for cancer detection
        self._lineage_growth: Dict[str, float] = {}

    # ------------------------------------------------------------------ phases
    def at(self, step: int) -> str:
        c = self.cfg
        period = c.kali_learning + c.kali_audit + c.kali_growth + c.kali_rest
        pos = step % period
        if pos < c.kali_learning:
            return "LEARNING"
        if pos < c.kali_learning + c.kali_audit:
            return "AUDIT"
        if pos < c.kali_learning + c.kali_audit + c.kali_growth:
            return "GROWTH"
        return "REST"

    @property
    def phase(self) -> str:
        return self.at(self.step)

    @property
    def cycle_step(self) -> int:
        c = self.cfg
        period = c.kali_learning + c.kali_audit + c.kali_growth + c.kali_rest
        return self.step % period

    # --------------------------------------------------------------- mutation
    @staticmethod
    def mu(mu0: float, lam: float, t: int, accuracy: float) -> float:
        return float(max(0.0, mu0 * np.exp(-lam * t) * (1.0 - accuracy)))

    def mutation_rate(self, accuracy: float) -> float:
        c = self.cfg
        return self.mu(c.noise_mu0, c.noise_lambda, self.step, accuracy)

    def permit_mutation(self, accuracy: float, lineage: str = "main") -> KaliState:
        phase = self.phase
        rate = self.mutation_rate(accuracy)
        permitted = phase == "GROWTH" and rate >= self.cfg.growth_min_mutation
        if rate > self.cfg.mutation_rate_cap:
            rate = self.cfg.mutation_rate_cap
            permitted = False
        state = KaliState(phase=phase, cycle_step=self.cycle_step,
                          mutation_rate=rate, permitted=permitted)
        self.decisions.append(
            {"step": self.step, "phase": phase, "rate": rate, "permitted": permitted,
             "lineage": lineage}
        )
        self.ledger.record(
            "kali.gate", step=self.step, phase=phase, rate=rate,
            permitted=permitted, lineage=lineage,
        )
        return state

    def tick(self) -> None:
        self.step += 1

    # ---------------------------------------------------------------- cancer
    def check_cancer(self, lineage: str, growth: float) -> bool:
        """True if a lineage grows faster than the cancer threshold (FR-4.6)."""
        self._lineage_growth[lineage] = growth
        is_cancer = growth > self.cfg.lineage_growth_cancer
        if is_cancer:
            self.ledger.record("kali.cancer", lineage=lineage, growth=growth)
        return is_cancer


class Dunce:
    """Failure patching via mutation inversion (FR-5.1 .. FR-5.4)."""

    def __init__(self, cfg: Optional[ZoeConfig] = None,
                 ledger: Optional[KaliLedger] = None) -> None:
        self.cfg = cfg or ZoeConfig()
        self.ledger = ledger or KaliLedger(self.cfg.ledger_path)
        self.patterns: List[Dict] = []

    def should_patch(self, parent_score: float, child_score: float,
                     lower_is_better: bool = False) -> bool:
        """True when a mutation regressed (accuracy down, or loss up)."""
        if lower_is_better:
            return child_score > parent_score
        return child_score < parent_score

    def patch(
        self,
        parent_adapter: np.ndarray,
        child_adapter: np.ndarray,
        parent_score: float,
        child_score: float,
        lower_is_better: bool = False,
    ) -> np.ndarray:
        """Partially invert the mutation delta: child -> child - s*(child-parent)."""
        if not self.should_patch(parent_score, child_score, lower_is_better):
            return np.array(child_adapter, dtype=float)
        s = self.cfg.dunce_patch_strength
        delta = np.asarray(child_adapter) - np.asarray(parent_adapter)
        patched = np.asarray(child_adapter) - s * delta
        self.patterns.append(
            {
                "parent_score": parent_score,
                "child_score": child_score,
                "delta_norm": float(np.linalg.norm(delta)),
            }
        )
        self.ledger.record(
            "dunce.patch", parent_score=parent_score,
            child_score=child_score, delta_norm=float(np.linalg.norm(delta)),
        )
        return patched

    @property
    def patch_rate(self) -> float:
        return float(len(self.patterns))
