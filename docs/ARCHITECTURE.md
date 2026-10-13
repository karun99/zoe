# Architecture

Zoe is an 11-layer stack plus 2 control mechanisms, integrated by `ZoeRig`
(`zoe/rig.py`). Layers communicate through plain Python dataclasses and NumPy
arrays; there are no hidden channels. The `KaliLedger` is the single source of
truth for every consequential decision.

```
┌─────────────────────────────────────────────────────────────┐
│              COMPANION MODE (L8)  screen | browser | states │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              VIRTUAL AVATAR (L6)  render | expression | lip │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│      PROMPT API (L5)  versioned templates | cache | A/B     │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│      MCP CLIENT (L5)  discover | call tools | resources     │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│         PROMPT-AS-NEURAL-HARNESS (L2)                       │
│  Agent Router · Format Enforcer · Growth Signal · Silent    │
│  Thinking · Jataka (L10) · Sahaja (L9) · PIA (L11)          │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│         LLAMA.CPP + EVOLVED LoRA (L3)                       │
│         frozen GGUF  +  mutating low-rank adapter           │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│         KALI (L4) + DUNCE (L4)                              │
│         temporal gates (WHEN)  +  failure patching          │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│         FLYBRAIN RESERVOIR (L1)                             │
│     LIF population · spike features · Giant Fiber reflex    │
│     · Hebbian reinforcement · neuromodulation               │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│         AI VIRTUAL MACHINE (L7)                             │
│     snapshot boot · egress allowlist · quotas · persistence │
└─────────────────────────────────────────────────────────────┘
```

## Module map

| Path | Responsibility |
|---|---|
| `zoe/config.py` | `ZoeConfig` — all tunables, env overrides |
| `zoe/identity.py` | Zoe's immutable identity anchors (L2, FR-2.10) |
| `zoe/ledger.py` | `KaliLedger` — append-only JSONL decision log |
| `zoe/agents/spectrum.py` | 9 Spectrum agents, conflict matrix (App. F/G) |
| `zoe/layers/l1_flybrain.py` | `FlybrainReservoir` — LIF reservoir + Kundalini |
| `zoe/layers/l2_harness.py` | `PromptHarness` — routing, format, growth, guards |
| `zoe/layers/l3_llm.py` | `LlamaCppModel` — frozen base + evolving LoRA |
| `zoe/layers/l4_kali_dunce.py` | `Kali` temporal gate + `Dunce` patcher |
| `zoe/layers/l5_mcp.py` | `MCPClient` + `PromptAPI` |
| `zoe/layers/l6_avatar.py` | `Avatar` — expression + lip-sync |
| `zoe/layers/l7_vm.py` | `MockVM` / `FirecrackerVM` — sandbox |
| `zoe/layers/l8_companion.py` | `CompanionMode` — awareness + redaction |
| `zoe/layers/l9_sahaja.py` | `Sahaja` — silent witness |
| `zoe/layers/l10_jataka.py` | `Jataka` — 5-precept guardrails |
| `zoe/layers/l11_pia.py` | `PIA` — silent adaptation |
| `zoe/metrics/evaluation.py` | 7-tier metric specs + premortem detectors |
| `zoe/rig.py` | `ZoeRig` — 13-step flow, evolution loop, benchmarks |
| `zoe/cli.py` | `run` / `train` / `report` / `demo` |

## Key data contracts

| Producer | Type | Consumer |
|---|---|---|
| `FlybrainReservoir.step` | `ReservoirReport(feature…​)` | L2 routing, L3 probe |
| `PromptHarness.decide` | `HarnessDecision(agent, growth_signal…)` | `ZoeRig.run` |
| `Kali.permit_mutation` | `KaliState(phase, rate, permitted)` | `ZoeRig.train` |
| `Dunce.patch` | `np.ndarray` (patched adapter) | `LlamaCppModel.set_adapter` |
| `LlamaCppModel.generate` | `Generation(text, tokens, mock)` | `PromptHarness.format_response` |
| `ZoeRig.collect_signals` | `dict` of measured signals | `metrics.evaluate` |

## The control loop

`Kali` divides time into `LEARNING(10) → AUDIT(3) → GROWTH(2) → REST(5)`
(period 20). Mutation is permitted **only** during GROWTH, and only while the
temporal noise rate `μ` is above the `0.001` floor. When a mutation regresses
the objective, `Dunce` inverts a fraction of its delta; if that still fails,
the parent adapter is restored (elitist selection). As generations accumulate,
`μ` decays toward zero, so the system converges and then stops mutating — the
intended "grow without overflowing" behaviour.
