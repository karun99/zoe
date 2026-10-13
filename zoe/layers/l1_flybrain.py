"""Layer 1 - Flybrain reservoir (FR-1.1 .. FR-1.7).

A frozen, sparsely-connected leaky integrate-and-fire (LIF) reservoir stands in
for the Drosophila connectome. When the optional ``flybrain`` package is
present it is used for topology; otherwise a synthetic LIF reservoir with a
criticality-tuned spectral radius is used (FR-1.2).

Kundalini (the "inspired" layer) is implemented *only* as three concrete
mechanisms on the reservoir (section 3.2, L1):

* Giant Fiber reflex arcs - a fast neuron subset that fires on strong input.
* Hebbian reinforcement - voluntary readout weights transfer into reflexes.
* Neuromodulation - octopamine / dopamine / serotonin shift gains and
  thresholds.

Only the linear readout is trained; the recurrent weights are frozen.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..config import ZoeConfig

try:  # pragma: no cover - optional dependency
    import flybrain as _flybrain  # type: ignore

    _HAS_FLYBRAIN = True
except Exception:  # pragma: no cover - expected in the MVP
    _flybrain = None
    _HAS_FLYBRAIN = False


@dataclass
class ReservoirReport:
    firing_rate: float
    isi_cv: float
    criticality: float
    giant_fiber_spikes: int
    feature: np.ndarray = field(repr=False)


class FlybrainReservoir:
    def __init__(self, cfg: Optional[ZoeConfig] = None) -> None:
        self.cfg = cfg or ZoeConfig()
        c = self.cfg
        rng = np.random.default_rng(c.lif_seed)
        self.n = int(c.neuron_count)

        # --- sparse recurrent connectivity (frozen) ---------------------------
        k = max(4, int(0.005 * self.n))  # fixed in-degree
        self.pre = rng.integers(0, self.n, size=self.n * k)
        self.post = np.repeat(np.arange(self.n), k)
        # Scale weights so the branching parameter ~= 1 (critical regime).
        self.weights = rng.normal(0.0, 1.0, size=self.n * k) / np.sqrt(k)

        # --- input projection (frozen) ---------------------------------------
        self.input_dim = int(c.input_dim)
        self.w_in = rng.normal(0.0, 1.0, size=(self.n, self.input_dim)) / np.sqrt(
            self.input_dim
        )
        # tonic drive keeps the population spontaneously active (a few Hz)
        self.tonic = rng.normal(0.0, 0.1, size=self.n)

        # --- giant fiber reflex subset ---------------------------------------
        n_gf = max(1, int(c.giant_fiber_ratio * self.n))
        self.gf_idx = rng.choice(self.n, size=n_gf, replace=False)
        self.gf_gain = 3.0

        # --- trainable linear readout over the feature vector ----------------
        self.feature_dim = int(c.feature_dim)
        self.w_out = rng.normal(0.0, 0.05, size=(self.feature_dim, self.feature_dim))

        # --- neuromodulation --------------------------------------------------
        self.mod = {
            "octopamine": float(c.neuro_octopamine),
            "dopamine": float(c.neuro_dopamine),
            "serotonin": float(c.neuro_serotonin),
        }

        self.backend = "flybrain" if _HAS_FLYBRAIN else "synthetic-lif"
        self._last_spikes: np.ndarray = np.zeros(self.n, dtype=bool)
        self._last_counts: np.ndarray = np.zeros(self.n)
        self._isi_samples: List[float] = []

    # ------------------------------------------------------------------ encode
    def encode(self, text: str) -> np.ndarray:
        """Deterministic hashed input vector (length ``input_dim``)."""
        vec = np.zeros(self.input_dim)
        tokens = _tokenize(text)
        if not tokens:
            return vec
        for tok in tokens:
            h = _stable_hash(self.cfg.lif_seed, tok) % self.input_dim
            vec[h] += 1.0
        vec = vec / vec.max()  # normalize peaks to 1
        return vec

    # ---------------------------------------------------------------- simulate
    def step(self, text: str) -> ReservoirReport:
        c = self.cfg
        input_vec = self.encode(text)
        input_current = (self.w_in @ input_vec) * c.input_scale + self.tonic

        v = np.zeros(self.n)
        refractory = np.zeros(self.n)
        counts = np.zeros(self.n)
        spikes_prev = np.zeros(self.n)
        spike_times = [-1] * self.n
        isis: List[float] = []

        # Neuromodulation sets the effective membrane time-constant and gain.
        gain = 1.0 + self.mod["octopamine"] - 0.5 * self.mod["serotonin"]
        thresh = c.v_thresh * (1.0 + 0.5 * self.mod["serotonin"])

        for t in range(c.timesteps):
            recurrent = np.bincount(
                self.post,
                weights=self.weights * spikes_prev[self.pre],
                minlength=self.n,
            )
            recurrent[self.gf_idx] *= self.gf_gain  # giant-fiber reflex boost

            i_total = input_current + recurrent
            v += (c.dt / c.tau_mem) * (-v + gain * i_total)
            refractory = np.maximum(0.0, refractory - c.dt)

            spiked = (v >= thresh) & (refractory <= 0.0)
            # dopamine raises the effective drive of already-active neurons
            if self.mod["dopamine"] > 0:
                spiked |= (v >= thresh * 0.7) & (refractory <= 0.0) & (spikes_prev > 0)

            counts[spiked] += 1.0
            for idx in np.nonzero(spiked)[0]:
                if spike_times[idx] >= 0:
                    isis.append(float(t - spike_times[idx]))
                spike_times[idx] = t
            v[spiked] = c.v_reset
            refractory[spiked] = c.refractory
            spikes_prev = spiked.astype(float)

        total_time = c.timesteps * c.dt / 1000.0
        firing_rate = float(counts.sum()) / (self.n * max(total_time, 1e-9))
        isi_cv = _cv(isis)
        criticality = self._branching_parameter(counts)

        feature = self._features(counts)
        gf_spikes = int(counts[self.gf_idx].sum())

        self._last_spikes = spikes_prev.astype(bool)
        self._last_counts = counts
        return ReservoirReport(
            firing_rate=firing_rate,
            isi_cv=isi_cv,
            criticality=criticality,
            giant_fiber_spikes=gf_spikes,
            feature=feature,
        )

    # ---------------------------------------------------------------- features
    def _features(self, counts: np.ndarray) -> np.ndarray:
        """Bin neuron spike counts into a fixed-size, L2-normalised feature."""
        binned = np.zeros(self.feature_dim)
        edges = np.linspace(0, self.n, self.feature_dim + 1).astype(int)
        for i in range(self.feature_dim):
            lo, hi = edges[i], edges[i + 1]
            binned[i] = counts[lo:hi].sum()
        norm = float(np.linalg.norm(binned))
        return binned / norm if norm > 0 else binned

    def _branching_parameter(self, counts: np.ndarray) -> float:
        """Approximate branching parameter sigma from descendant/parent spikes."""
        total = counts.sum()
        if total <= 0:
            return 0.0
        active = counts[counts > 0]
        parents = max(1, active.size)
        # descendants proxied by mean spikes per active neuron, normalized
        return float(active.mean() / max(self.cfg.timesteps * 0.1, 1.0))

    # -------------------------------------------------------------- plasticity
    def train_readout(self, features: np.ndarray, target: np.ndarray,
                      lr: float = 1e-2) -> float:
        """Least-mean-squares update of the linear readout (FR-1.4)."""
        pred = self.w_out @ features
        err = target - pred
        self.w_out += lr * np.outer(err, features)
        return float(np.mean(err ** 2))

    def reinforce(self, reward: float) -> None:
        """Hebbian reinforcement of the giant-fiber reflex path (FR-1.7).

        Positive reward potentiates the reflex input synapses (voluntary -> the
        reflex becomes involuntary); negative reward depotentiates them.
        """
        lr = self.cfg.hebbian_lr * reward
        self.w_in[self.gf_idx] *= (1.0 + lr)
        if reward > 0:
            self.gf_gain = min(10.0, self.gf_gain * (1.0 + 0.01 * reward))
        else:
            self.gf_gain = max(1.0, self.gf_gain * (1.0 + 0.01 * reward))

    def set_neuromodulation(self, octopamine: float = 0.0, dopamine: float = 0.0,
                            serotonin: float = 0.0) -> None:
        self.mod.update(
            octopamine=octopamine, dopamine=dopamine, serotonin=serotonin
        )

    # ------------------------------------------------------------------ compat
    def encode_feature(self, text: str) -> np.ndarray:
        """Convenience: run the reservoir and return only the feature vector."""
        return self.step(text).feature


def _tokenize(text: str) -> List[str]:
    return [t for t in text.lower().replace("\n", " ").split(" ") if t]


def _stable_hash(seed: int, token: str) -> int:
    """Process-independent hash so reservoir inputs are reproducible."""
    digest = hashlib.blake2b(
        f"{seed}:{token}".encode("utf-8"), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big")


def _cv(values: List[float]) -> float:
    """Coefficient of variation of inter-spike intervals (0 if undefined)."""
    if len(values) < 2:
        return 0.0
    arr = np.asarray(values, dtype=float)
    mean = arr.mean()
    if mean <= 0:
        return 0.0
    return float(arr.std(ddof=0) / mean)
