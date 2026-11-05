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
│         FROZEN BASE MODEL + EVOLVED LoRA (L3)               │
│  frozen GGUF  +  mutating low-rank adapter                  │
│ engines: ollama · llama-server · llamacpp · llama-cli · mock│
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
| `zoe/emoja/lexicon.py` | Emoja text-only lexicons, distress salience, crisis patterns |
| `zoe/emoja/agents.py` | Emoja agents (SUNO, DRISHTI, MUDRA, RANG, BINDU, KATHA, SETU) + card |
| `zoe/emoja/session.py` | Emoja routing, commands, consent, integration |
| `zoe/emoja/storage.py` | Opt-in card store; `/drop` deletion |
| `zoe/emoja/cli.py` | `zoe emoja` / `zoe-emoja` |
| `zoe/metrics/evaluation.py` | 7-tier metric specs + premortem detectors |
| `zoe/rig.py` | `ZoeRig` — 13-step flow, evolution loop, benchmarks |
| `zoe/cli.py` | `run` / `train` / `report` / `demo` / `doctor` / `backends` |
| `zoe/doctor.py` | environment diagnostics (`zoe doctor`) |
| `zoe/backends.py` | Ollama / llama.cpp / mock engines behind one interface |

## Key data contracts

| Producer | Type | Consumer |
|---|---|---|
| `FlybrainReservoir.step` | `ReservoirReport(feature…​)` | L2 routing, L3 probe |
| `PromptHarness.decide` | `HarnessDecision(agent, growth_signal…)` | `ZoeRig.run` |
| `Kali.permit_mutation` | `KaliState(phase, rate, permitted)` | `ZoeRig.train` |
| `Dunce.patch` | `np.ndarray` (patched adapter) | `LlamaCppModel.set_adapter` |
| `LlamaCppModel.generate` | `Generation(text, tokens, mock)` | `PromptHarness.format_response` |
| `ZoeRig.collect_signals` | `dict` of measured signals | `metrics.evaluate` |

## Emoja sub-pipeline

Emoja is a module of Zoe, not an L-numbered layer. It sits on top of the
companion stack and reads only the user's own text:

```
SUNO (perception) → DRISHTI (policy) → MUDRA/RANG/BINDU (representation)
                  → KATHA (optional) → SETU (orchestrator)
```

| Contract | Type | Consumer |
|---|---|---|
| `Suno.listen` | `SunoReading(words, tokens, cluster, categories, distress, crisis)` | DRISHTI + representation agents |
| `Drishti.precheck` | `DrishtiVerdict(consent, crisis, max_rung, veto, shatkona, skews)` | SETU |
| `Mudra/Rang/Bindu.render` | typed aesthetic outputs or `None` | SETU |
| `Katha.maybe_offer` | `KathaOutput` or `None` | SETU |
| `Setu.assemble` | `EmojaTurn(card, sentence, audit, …)` | CLI / MCP |

Raw user text never reaches the aesthetic agents. DRISHTI's veto is enforced by
`Setu.assemble`: a veto leaves the aesthetic fields empty rather than asking a
model to comply. See [`EMOJA.md`](EMOJA.md) and [`ENFORCEMENT.md`](ENFORCEMENT.md).

## The control loop

`Kali` divides time into `LEARNING(10) → AUDIT(3) → GROWTH(2) → REST(5)`
(period 20). Mutation is permitted **only** during GROWTH, and only while the
temporal noise rate `μ` is above the `0.001` floor. When a mutation regresses
the objective, `Dunce` inverts a fraction of its delta; if that still fails,
the parent adapter is restored (elitist selection). As generations accumulate,
`μ` decays toward zero, so the system converges and then stops mutating — the
intended "grow without overflowing" behaviour.
