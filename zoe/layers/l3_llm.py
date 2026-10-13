"""Layer 3 - llama.cpp + evolved LoRA (FR-3.1 .. FR-3.6).

A *frozen* GGUF base model with an *evolving* low-rank adapter. The base model
never changes; only the adapter mutates, and only when Kali permits (FR-3.3).

If ``llama-cpp-python`` and a GGUF file are unavailable, Zoe runs in mock mode
(FR-3.4): generation is a deterministic function of the reservoir feature and
the adapter, so the full evolution loop can still be exercised and measured.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from ..config import ZoeConfig

try:  # pragma: no cover - optional dependency
    from llama_cpp import Llama as _Llama  # type: ignore

    _HAS_LLAMA = True
except Exception:  # pragma: no cover
    _Llama = None
    _HAS_LLAMA = False


@dataclass
class Generation:
    text: str
    tokens: int
    mock: bool


class LlamaCppModel:
    def __init__(self, cfg: Optional[ZoeConfig] = None) -> None:
        self.cfg = cfg or ZoeConfig()
        c = self.cfg
        self.frozen = True
        self.base = None
        self.mock = c.mock_mode or not (_HAS_LLAMA and c.gguf_path)
        if not self.mock:
            self.base = _Llama(model_path=c.gguf_path, n_ctx=c.context_tokens)  # pragma: no cover

        rng = np.random.default_rng(c.lif_seed + 7)
        self.lora_dim = int(c.lora_dim)
        # Evolving adapter: a low-rank matrix; starts near a no-op (FR-3.2).
        scale = c.lora_init_scale if c.lora_init_scale > 0 else 0.02
        self.adapter = rng.normal(0.0, scale, size=(self.lora_dim, self.lora_dim))
        self.generation = 0
        self.history: List[float] = []

        # Fixed, hidden ground-truth mapping. The model must *evolve* its
        # adapter to recover it - this is what makes accuracy a real signal.
        self._truth = rng.normal(0.0, 1.0, size=(self.lora_dim, self.lora_dim))

    # ------------------------------------------------------------------- task
    @staticmethod
    def _pad(features: np.ndarray, dim: int) -> np.ndarray:
        f = np.asarray(features, dtype=float)
        return f[:dim] if f.size >= dim else np.pad(f, (0, dim - f.size))

    def _logits_with(self, adapter: np.ndarray, features: np.ndarray) -> np.ndarray:
        f = self._pad(features, self.lora_dim)
        h = np.tanh(adapter @ f)
        return np.array([g.sum() for g in np.array_split(h, 4)])

    def _probe(self, features: np.ndarray) -> np.ndarray:
        """Project a feature vector through the adapter to 4 logits."""
        return self._logits_with(self.adapter, features)

    def _true_label(self, features: np.ndarray) -> int:
        return int(np.argmax(self._logits_with(self._truth, features)))

    def measure_accuracy(self, features: List[np.ndarray]) -> float:
        if not features:
            return 0.0
        correct = sum(
            1 for f in features
            if int(np.argmax(self._probe(f))) == self._true_label(f)
        )
        return correct / len(features)

    def measure_loss(self, features: List[np.ndarray]) -> float:
        """Mean cross-entropy against the hidden ground truth (smooth fitness)."""
        if not features:
            return float("inf")
        total = 0.0
        for f in features:
            logits = self._probe(f)
            logits = logits - logits.max()
            p = np.exp(logits)
            p = p / p.sum()
            total += -np.log(p[self._true_label(f)] + 1e-9)
        return float(total / len(features))

    # ------------------------------------------------------------- generation
    def generate(self, prompt: str, feature: Optional[np.ndarray] = None,
                 agent: str = "WHITE", task: str = "") -> Generation:
        if not self.mock:
            out = self.base(prompt, max_tokens=128)  # pragma: no cover
            text = out["choices"][0]["text"].strip()
            return Generation(text=text, tokens=len(text.split()), mock=False)

        chosen = 0
        if feature is not None:
            chosen = int(np.argmax(self._probe(feature)))
        task_line = (task.strip()[:60] or "your request")
        lines = [
            f"I hear: {task_line}.",
            f"Routing through this path; salience {chosen + 1} of 4.",
            f"Holding steady, attending to what matters here.",
            "Ready for the next step whenever you are.",
        ]
        text = "\n".join(lines)
        return Generation(text=text, tokens=len(text.split()), mock=True)

    # --------------------------------------------------------------- evolution
    def temporal_noise(self, accuracy: float, generation: Optional[int] = None) -> float:
        """mu(t, A) = mu0 * exp(-lambda t) * (1 - A)  (Appendix B, FR-3.6)."""
        t = self.generation if generation is None else generation
        c = self.cfg
        mu = c.noise_mu0 * np.exp(-c.noise_lambda * t) * (1.0 - accuracy)
        return float(max(0.0, mu))

    def mutate(self, accuracy: float, permitted: bool, strength: float = 1.0) -> float:
        """Apply one adapter mutation; returns the mutation magnitude.

        Mutation is a no-op unless ``permitted`` (i.e. Kali is in GROWTH).
        """
        if not permitted:
            return 0.0
        mu = self.temporal_noise(accuracy) * strength
        if mu <= 0:
            return 0.0
        rng = np.random.default_rng(self.cfg.lif_seed + 1000 + self.generation)
        delta = rng.normal(0.0, mu, size=self.adapter.shape)
        self.adapter = self.adapter + delta
        self.generation += 1
        self.history.append(float(np.abs(delta).mean()))
        return float(np.abs(delta).mean())

    def set_adapter(self, adapter: np.ndarray) -> None:
        self.adapter = np.array(adapter, dtype=float)
