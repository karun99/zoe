"""Central configuration for Zoe.

Every knob is overridable through ``ZOE_*`` environment variables so the rig can
be retargeted without code changes (NFR-4.2). Defaults match the *reduced*
resource profile described in SRS section 11.2.
"""

from __future__ import annotations

import os
from dataclasses import MISSING, dataclass, field, fields
from typing import Any, Dict


def _env(name: str, default: Any) -> Any:
    raw = os.environ.get(f"ZOE_{name.upper()}")
    if raw is None:
        return default
    if isinstance(default, (list, dict)):
        return default
    if isinstance(default, bool):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(default, int):
        return int(raw)
    if isinstance(default, float):
        return float(raw)
    return raw


@dataclass
class ZoeConfig:
    """Runtime configuration for the complete Zoe rig."""

    # --- Identity (FR-2.10, section 3.4) -------------------------------------
    identity_name: str = "Zoe"

    # --- L1 Flybrain reservoir (FR-1.x) --------------------------------------
    neuron_count: int = 2_000  # reduced profile; 139_000 in full profile
    input_dim: int = 128
    input_scale: float = 6.0
    feature_dim: int = 64
    timesteps: int = 25
    dt: float = 1.0
    tau_mem: float = 20.0
    v_thresh: float = 1.0
    v_reset: float = 0.0
    refractory: float = 2.0
    lif_seed: int = 1729
    giant_fiber_ratio: float = 0.05  # fast-reflex neuron fraction (Gi fiber)
    hebbian_lr: float = 0.01
    neuro_octopamine: float = 0.0
    neuro_dopamine: float = 0.0
    neuro_serotonin: float = 0.0

    # --- L2 Prompt-as-Neural-Harness (FR-2.x) --------------------------------
    output_lines: int = 5
    silent_thinking: bool = True
    growth_min_mutation: float = 0.001
    routing_confidence_floor: float = 0.5

    # --- L3 llama.cpp + LoRA (FR-3.x) ----------------------------------------
    gguf_path: str = ""
    lora_dim: int = 64
    lora_init_scale: float = 0.0  # start from a no-op adapter
    mock_mode: bool = False
    context_tokens: int = 2048
    noise_mu0: float = 0.1
    noise_lambda: float = 0.05

    # --- L4 Kali + Dunce (FR-4.x, FR-5.x) ------------------------------------
    kali_learning: int = 10
    kali_audit: int = 3
    kali_growth: int = 2
    kali_rest: int = 5
    mutation_rate_cap: float = 0.1
    lineage_growth_cancer: float = 0.5
    dunce_patch_strength: float = 0.5

    # --- L5 MCP + Prompt API (FR-6.x, FR-7.x) --------------------------------
    mcp_servers: list = field(default_factory=list)
    prompt_cache_size: int = 128

    # --- L6 Avatar (FR-A.x) --------------------------------------------------
    avatar_fps_target: int = 25
    lip_sync_budget_ms: float = 100.0

    # --- L7 AI VM (FR-V.x) ---------------------------------------------------
    vm_backend: str = "mock"  # "mock" | "firecracker"
    vm_boot_budget_s: float = 5.0
    vm_suspend_budget_h: float = 8.0
    vm_egress_allowlist: list = field(default_factory=lambda: ["api.github.com"])
    vm_cpu_quota: int = 2
    vm_mem_quota_mb: int = 256
    vm_disk_quota_mb: int = 100

    # --- L8 Companion Mode (FR-C.x) ------------------------------------------
    companion_interval_s: float = 5.0
    companion_states: list = field(
        default_factory=lambda: ["idle", "curious", "focused", "playful", "resting"]
    )

    # --- Ledger / metrics ----------------------------------------------------
    ledger_path: str = ".kali-ledger/ledger.jsonl"
    eval_held_out: int = 32

    def to_dict(self) -> Dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_env(cls, **overrides: Any) -> "ZoeConfig":
        """Build a config from environment variables, then apply overrides."""
        kwargs: Dict[str, Any] = {}
        for f in fields(cls):
            default = f.default
            if default is MISSING and f.default_factory is not MISSING:  # type: ignore[misc]
                default = f.default_factory()  # type: ignore[misc]
            kwargs[f.name] = _env(f.name, default)
        kwargs.update(overrides)
        return cls(**kwargs)
