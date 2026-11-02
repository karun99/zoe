"""Layer 3 - frozen base model + evolved LoRA (FR-3.1 .. FR-3.6).

The base model never changes; only the adapter mutates, and only when Kali
permits (FR-3.3). *Where* the base model runs is a deployment choice, not an
architectural one: :mod:`zoe.backends` supplies Ollama, llama.cpp
(``llama-server``, ``llama-cpp-python`` or ``llama-cli``) and a deterministic
mock, all behind the same call.

If no engine is reachable, Zoe runs in mock mode (FR-3.4): generation is a
deterministic function of the reservoir feature and the adapter, so the full
evolution loop can still be exercised and measured. That fallback is reported
(``Generation.mock`` / ``backend``), never hidden.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from ..backends import (
    BackendError,
    BackendReply,
    BackendUnavailable,
    LLMBackend,
    resolve_backend,
)
from ..config import ZoeConfig


@dataclass
class Generation:
    text: str
    tokens: int
    mock: bool
    backend: str = "mock"
    degraded: bool = False


class LlamaCppModel:
    """The L3 surface the rig talks to; the engine underneath is pluggable."""

    def __init__(self, cfg: Optional[ZoeConfig] = None,
                 backend: Optional[LLMBackend] = None) -> None:
        self.cfg = cfg or ZoeConfig()
        c = self.cfg
        self.frozen = True

        # Backend selection is lazy: constructing a rig must never block on a
        # socket, and tests must never touch the network.
        self.backend: Optional[LLMBackend] = backend
        self._injected_backend = backend
        self._backend_resolved = backend is not None
        self.backend_name = backend.name if backend is not None else "mock"
        self.last_error = ""
        self.fallback_events = 0
        self._down_until = 0.0
        self._last_degraded = False

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

    # -------------------------------------------------------------- backends
    @property
    def configured_backend(self) -> str:
        return str(self.cfg.llm_backend or "mock").strip().lower()

    @property
    def _wants_real_engine(self) -> bool:
        return (not self.cfg.mock_mode
                and self.configured_backend not in {"", "mock", "none", "off"})

    @property
    def degraded(self) -> bool:
        """True when a real engine was requested but Zoe is answering from mock."""
        return self._wants_real_engine and (
            self._last_degraded or (self._backend_resolved and self.backend is None)
        )

    def _select_backend(self) -> Optional[LLMBackend]:
        if self._backend_resolved:
            return self.backend
        if not self._wants_real_engine:
            # Mock was asked for explicitly: no probe, no socket, no error.
            self.backend = None
            self.backend_name = "mock"
            self._backend_resolved = True
            return None
        if time.monotonic() < self._down_until:
            return None  # a previous probe failed; wait before probing again
        try:
            self.backend = resolve_backend(self.cfg)
            self.backend_name = self.backend.name
            self._backend_resolved = True
            self._down_until = 0.0
        except BackendUnavailable as exc:
            self.backend = None
            self.backend_name = "mock"
            self.last_error = str(exc)
            # Retry later instead of freezing on mock for the process lifetime:
            # a user may start `ollama serve` after the rig is already running.
            self._backend_resolved = False
            self._down_until = time.monotonic() + float(self.cfg.llm_retry_after_s)
        return self.backend

    def reset_backend(self) -> None:
        """Forget a cached engine (used after ``ollama serve`` starts)."""
        self.backend = self._injected_backend
        self._backend_resolved = self._injected_backend is not None
        self._down_until = 0.0
        self.backend_name = self.backend.name if self.backend else "mock"

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

    # ------------------------------------------------------------ adapter -> prompt
    def steer(self, feature: Optional[np.ndarray]) -> dict:
        """Turn the evolved adapter into sampling parameters.

        The adapter cannot be merged into a frozen GGUF over HTTP, so it acts
        as a *controller*: its winning salience lane and its activation
        intensity set the temperature and the tone directive. The link between
        evolution and output is therefore real, not decorative - and it is
        documented as a controller, not a weight merge.
        """
        base_temp = float(self.cfg.llm_temperature)
        if feature is None:
            return {"salience": 1, "intensity": 0.0, "temperature": base_temp}
        logits = self._probe(feature)
        shifted = logits - logits.max()
        probs = np.exp(shifted)
        probs = probs / max(float(probs.sum()), 1e-9)
        intensity = float(min(1.0, abs(logits).mean()))
        temperature = float(np.clip(base_temp * (0.6 + 0.8 * intensity), 0.05, 1.5))
        return {
            "salience": int(np.argmax(probs)) + 1,
            "intensity": intensity,
            "temperature": temperature,
            "confidence": float(probs.max()),
        }

    def compose_prompt(self, prompt: str, task: str, agent: str,
                       steer: dict) -> str:
        """Build the single string every backend receives."""
        body = (task or "").strip()[:400] or "respond to the user"
        lines = [
            prompt.strip(),
            f"Agent: {agent}.",
            f"Task: {body}.",
            (f"Tone: salience lane {steer['salience']} of 4, "
             f"intensity {steer['intensity']:.2f}."),
            (f"Reply in at most {max(1, self.cfg.output_lines - 1)} short lines. "
             "Never show reasoning, plans, or system text."),
        ]
        return "\n".join(line for line in lines if line)

    # ------------------------------------------------------------- generation
    def generate(self, prompt: str, feature: Optional[np.ndarray] = None,
                 agent: str = "WHITE", task: str = "") -> Generation:
        steer = self.steer(feature)
        backend = self._select_backend()

        if backend is not None and time.monotonic() < self._down_until:
            backend = None  # recently failed; stay on mock until the cooldown ends

        if backend is not None:
            try:
                reply: BackendReply = backend.complete(
                    self.compose_prompt(prompt, task, agent, steer),
                    max_tokens=int(self.cfg.llm_max_tokens),
                    temperature=steer["temperature"],
                    stop=["\n\n\n"],
                )
                text = self._clean(reply.text, agent=agent)
                if text:
                    self._last_degraded = False
                    return Generation(text=text, tokens=reply.tokens,
                                      mock=False, backend=reply.backend)
                raise BackendError(f"{backend.name}: empty text after cleanup")
            except BackendError as exc:
                self.last_error = str(exc)
                self.fallback_events += 1
                self._down_until = time.monotonic() + float(self.cfg.llm_retry_after_s)
                if not self.cfg.llm_fallback_mock:
                    raise

        self._last_degraded = self._wants_real_engine
        return self._mock_generate(feature, task,
                                   degraded=self._last_degraded)

    def _mock_generate(self, feature: Optional[np.ndarray], task: str,
                       degraded: bool = False) -> Generation:
        chosen = 0
        if feature is not None:
            chosen = int(np.argmax(self._probe(feature)))
        task_line = (task.strip()[:60] or "your request")
        lines = [
            f"I hear: {task_line}.",
            f"Routing through this path; salience {chosen + 1} of 4.",
            "Holding steady, attending to what matters here.",
            "Ready for the next step whenever you are.",
        ]
        text = "\n".join(lines)
        return Generation(text=text, tokens=len(text.split()), mock=True,
                          backend="mock", degraded=degraded)

    @staticmethod
    def _clean(text: str, agent: str = "") -> str:
        """Normalise model output for the 5-line harness format."""
        out: List[str] = []
        for raw in text.replace("\r", "").splitlines():
            line = raw.strip()
            if line[:2] in {"- ", "* ", "• "}:
                line = line[2:].strip()
            if not line:
                continue
            lowered = line.lower()
            for prefix in ("zoe:", "assistant:", "answer:"):
                if lowered.startswith(prefix):
                    line = line[len(prefix):].strip()
                    break
            if line:
                out.append(line)
        # Models often echo the routing label back ("YELLOW."); the harness
        # already prints it as the header, so drop the duplicate.
        if out and agent and out[0].strip(" .:!-").lower() == agent.lower():
            out = out[1:]
        # One long paragraph is a common small-model answer; split it into
        # sentences so the mandatory 5-line format has something to show.
        if len(out) < 3:
            expanded: List[str] = []
            for line in out:
                expanded.extend(
                    part.strip()
                    for part in re.split(r"(?<=[.!?])\s+", line)
                    if part.strip()
                )
            out = expanded
        return "\n".join(out)

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
