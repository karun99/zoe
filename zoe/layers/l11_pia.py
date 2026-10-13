"""Layer 11 - PIA: Personal Intelligence & Adaptation (FR-2.7).

PIA adapts silently: it nudges agent-routing bias and the evolvable traits
(``identity.EVOLVABLE_TRAITS``) in response to user feedback. It never speaks
about what it is doing - the harness consumes its outputs silently.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..identity import EVOLVABLE_TRAITS


class PIA:
    def __init__(self, learning_rate: float = 0.05) -> None:
        self.lr = learning_rate
        self._bias: Dict[str, float] = {}
        self.traits: Dict[str, float] = {t: 0.5 for t in EVOLVABLE_TRAITS}
        self.observations: List[Dict] = []

    def agent_bias(self) -> Dict[str, float]:
        """Additive routing biases, clamped to keep routing stable."""
        return {k: max(-0.4, min(0.4, v)) for k, v in self._bias.items()}

    def reward_agent(self, agent: str, reward: float) -> None:
        """Positive reward reinforces an agent's routing preference."""
        self._bias[agent] = self._bias.get(agent, 0.0) + self.lr * reward
        self.observations.append({"kind": "agent", "agent": agent, "reward": reward})

    def reward_trait(self, trait: str, reward: float) -> None:
        if trait not in self.traits:
            return
        self.traits[trait] = max(0.0, min(1.0, self.traits[trait] + self.lr * reward))
        self.observations.append({"kind": "trait", "trait": trait, "reward": reward})

    def observe(self, feedback: Dict[str, float], agent: Optional[str] = None) -> None:
        """Batch adaptation from a feedback dict of trait -> reward."""
        for trait, reward in feedback.items():
            if trait in self.traits:
                self.reward_trait(trait, reward)
        if agent is not None and "overall" in feedback:
            self.reward_agent(agent, feedback["overall"])
