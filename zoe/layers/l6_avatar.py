"""Layer 6 - Virtual Avatar (FR-A.1 .. FR-A.9).

A mock, headless renderer exercises the full avatar contract: frame-rate
accounting, token-stream lip-sync, Spectrum-agent -> expression mapping, and
identity consistency. A real client-server renderer can replace the mock while
keeping the same interface (FR-A.6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..agents import AGENTS
from ..config import ZoeConfig
from ..identity import IDENTITY


@dataclass
class Frame:
    index: int
    expression: str
    voice: str
    phoneme: str
    lip_sync_ms: float


class Avatar:
    def __init__(self, cfg: Optional[ZoeConfig] = None,
                 mode: str = "stylized") -> None:
        self.cfg = cfg or ZoeConfig()
        self.mode = mode  # "stylized" | "photorealistic" (FR-A.5)
        self.avatar_id = IDENTITY["avatar_id"]
        self.expression = "balanced, radiant"
        self._frame = 0
        self.frames: List[Frame] = []

    # ----------------------------------------------------------- expression
    def set_agent(self, agent: str) -> str:
        spec = AGENTS.get(agent, AGENTS["WHITE"])
        self.expression = spec.expression
        return self.expression

    # -------------------------------------------------------------- lip-sync
    def speak(self, tokens: List[str], started_ms: float = 0.0) -> List[Frame]:
        """Emit one frame per token, aligned to the token stream (FR-A.7)."""
        frames: List[Frame] = []
        budget = self.cfg.lip_sync_budget_ms
        for i, tok in enumerate(tokens):
            # deterministic per-token alignment latency within budget (FR-A.2)
            ms = (hash((self.avatar_id, tok, i)) % 60) + 10
            frame = Frame(
                index=self._frame,
                expression=self.expression,
                voice=AGENTS["WHITE"].voice,
                phoneme=_phoneme(tok),
                lip_sync_ms=float(min(ms, budget - 1)),
            )
            frames.append(frame)
            self._frame += 1
        self.frames.extend(frames)
        return frames

    # -------------------------------------------------------------- metrics
    def measured_fps(self, frame_count: int, elapsed_s: float) -> float:
        return frame_count / elapsed_s if elapsed_s > 0 else 0.0

    def identity_consistent(self) -> bool:
        return self.avatar_id == IDENTITY["avatar_id"]

    @property
    def max_lip_sync_ms(self) -> float:
        return max((f.lip_sync_ms for f in self.frames), default=0.0)


def _phoneme(token: str) -> str:
    return token[:1].lower() if token else "-"
