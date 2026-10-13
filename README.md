# Project Zoe — ζωή <sub>(“life”)</sub>

[![M8ven Score](https://m8ven.ai/badge/mcp/karun99/zoe)](https://m8ven.ai/mcp/karun99/zoe?s=readme)

**A connectome-based reservoir computing companion** with biologically-inspired
control layers, an evolving LoRA adapter, embodied through a virtual avatar,
sandboxed in a MicroVM, with companion mode.

> **Honest claim.** Zoe is a connectome-based reservoir computing system with
> biologically-inspired control layers, an evolving LoRA adapter, embodied
> through a virtual avatar, sandboxed in a MicroVM, with companion mode.
> Zoe is **not** a superintelligence, and the conceptual layers (Shatkona,
> Kundalini‑as‑a‑layer, Sri Chakra as literal architecture, 80B scaling) are
> implemented only as metaphor or inspiration — never as literal architecture.

This repository is a **working MVP** of the requirements in the
[Software Requirements Specification](docs/SRS.md) (IEEE 830 / ISO/IEC/IEEE
29148, v4.0). Every layer has a real implementation with a deterministic
**mock / simulation fallback**, so the whole rig runs — and is fully tested —
without a GPU, a GGUF model, KVM, or a display.

```
L1  Flybrain Reservoir    → pattern detection (LIF; frozen)
L2  Prompt-as-Harness     → routing + 5-line output + growth signal
L3  llama.cpp + LoRA      → generation (frozen base, evolving adapter)
L4  Kali + Dunce          → temporal gates (WHEN) + failure patching
L5  MCP + Prompt API      → tools + versioned, cached prompts
L6  Virtual Avatar        → embodied expression + lip-sync
L7  AI Virtual Machine    → isolated execution (Firecracker-shaped)
L8  Companion Mode        → screen/browser awareness + pet states
L9  Sahaja                → silent witness (never acts)
L10 Jataka                → karmic guardrails (5 precepts)
L11 PIA                   → silent adaptation
```

## Quick start

```bash
git clone https://github.com/karun99/zoe.git
cd zoe
pip install -e .            # core needs only numpy

python -m zoe demo          # short scripted demonstration
python -m zoe run "build and implement a plan to fix the code"
python -m zoe train --generations 200
python -m zoe report        # evolution + 7-tier evaluation
```

Example:

```console
$ python -m zoe run "warn me about the unsafe risk before we proceed"
[YELLOW]
I hear: warn me about the unsafe risk before we proceed.
Routing through this path; salience 3 of 4.
Holding steady, attending to what matters here.
Ready for the next step whenever you are.

agent=YELLOW growth=0.500 mutated=False frames=31
```

`python -m zoe report` on the mock rig currently passes **26 of 27** scored
metrics across all 7 tiers and all **Critical Five** checks:

```console
=== Zoe 7-tier evaluation ===
scored=27 passed=26 pass_rate=0.963 critical_five_ok=True
  tier1: 6/6   tier2: 4/4   tier3: 3/3   tier4: 2/3
  tier5: 4/4   tier6: 3/3   tier7: 4/4
```

The one honest failure is `M-4.2 Dunce rate` (see
[Known limitations](#known-limitations)).

## The 13-step execution flow

Every interaction (`ZoeRig.run`) walks the SRS execution flow:

| # | Step | Component |
|--:|---|---|
| 1 | Input arrives | `rig` |
| 2 | AI VM boots / reuses session | L7 `MockVM` |
| 3 | Companion observes screen (if active) | L8 `CompanionMode` |
| 4 | Flybrain processes → features | L1 `FlybrainReservoir` |
| 5 | Harness routes + computes growth signal | L2 `PromptHarness` |
| 6 | Kali checks phase → permits/denies mutation | L4 `Kali` |
| 7 | LoRA adapter mutated (if permitted) | L3 `LlamaCppModel` |
| 8 | LLM generates output | L3 |
| 9 | Dunce patches failures | L4 `Dunce` |
| 10 | MCP executes tools (if requested) | L5 `MCPClient` |
| 11 | Prompt API supplies templates | L5 `PromptAPI` |
| 12 | Avatar renders output with expression | L6 `Avatar` |
| 13 | VM snapshots state for next session | L7 |

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the layer diagram and the
data contracts between layers, and [`docs/METRICS.md`](docs/METRICS.md) for the
7-tier metric catalogue and how each signal is measured.

### Layer 1 — Flybrain reservoir

A frozen, sparsely-connected leaky integrate-and-fire (LIF) population stands in
for the Drosophila connectome. Only the readout is trainable. If the optional
[`flybrain`](https://pypi.org/project/flybrain/) package is installed it is used
for topology; otherwise the synthetic LIF reservoir is used (FR-1.2). The
**Kundalini** inspiration is realised only as three concrete mechanisms:

* **Giant Fiber reflex arcs** — a fast neuron subset that fires on strong input.
* **Hebbian reinforcement** — voluntary readout transfer into reflexes (FR-1.7).
* **Neuromodulation** — octopamine / dopamine / serotonin shift gain & threshold.

### Layer 3 — evolving LoRA

The base model is frozen; only a low-rank adapter mutates, and only in Kali's
GROWTH phase. Mutation rate follows the temporal noise-reduction law
`μ = μ₀ · e^(−λt) · (1 − A)`. The mock task has a hidden ground-truth mapping,
so evolution is a *real* hill-climb: accuracy rises from `~0.31` to `~0.56`
over 200 generations on the mock rig.

## MCP server

Zoe ships its **own Model Context Protocol server** (L5), so an editor or another
agent can drive the rig. It speaks newline-delimited JSON-RPC over **stdio**
(`initialize` / `tools/list` / `tools/call`, `resources/list` / `resources/read`),
is dependency-free, and exposes four tools plus an identity resource:

| Tool | Purpose |
|---|---|
| `zoe_run` | Run one 13-step interaction; returns her answer, routed agent and growth signal |
| `zoe_report` | Run the evolution loop + 7-tier evaluation; returns the pass/fail summary |
| `zoe_layers` | List the eleven layers and their roles |
| `zoe_identity` | Return Zoe's persistent identity card |

```bash
zoe-mcp                      # or: python -m zoe.mcp_server
```

It is registered per-project through a committed [`.mcp.json`](.mcp.json) —
alongside the shared **`glama-gateway`** server that fronts the
[Glama AI gateway](https://glama.ai) (`https://gateway.glama.ai/v1`,
OpenAI-compatible, 100+ models). Zoe is listed on the **M8ven Trust Index** as a
verified publisher (badge above).

## Requirements coverage

Every functional requirement in the SRS has a corresponding implementation and
test. See [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) for the full
requirement-to-code traceability matrix.

## Configuration

All knobs are `ZOE_*` environment variables (NFR-4.2):

```bash
ZOE_NEURON_COUNT=139000 ZOE_GGUF_PATH=/models/qwen.gguf python -m zoe run "hello"
ZOE_MOCK_MODE=true python -m zoe report
```

Dynamic `*_allowlist` / `mcp_servers` fields are set in code
(`ZoeConfig`), not via env.

## Testing

```bash
pip install -e ".[dev]"
pytest -q
```

84 tests cover all 11 layers, the 9-agent conflict matrix, the Kali phase
cycle, Dunce patching, MCP client + server (stdio JSON-RPC), the Prompt API,
VM isolation & egress, companion redaction, the 7-tier evaluation harness, the
premortem detectors, and the integrated rig.

## Premortem guardrails

Zoe is evaluated against a written **premortem** (assume-failure / work-backward).
Each failure mode has a code-level detector or mitigation, surfaced by the
7-tier harness and by `premortem(signals)` in `zoe.metrics`:

| # | Failure mode | Guardrail | Signal / metric |
|--:|---|---|---|
| 1 | No evaluation harness | 7-tier harness runs every `report`; held-out accuracy is always measured | M-2.1, §1 detector |
| 2 | Evolution slower than SFT | Documented trade-off; elitist selector keeps the best adapter; μ decays | M-2.1 trend, §2 detector |
| 3 | No real task | Hidden ground-truth task (real hill-climb); accuracy floor | M-2.9, §3 detector |
| 4 | No convergence | Temporal noise-reduction law `μ = μ₀·e^(−λt)·(1−A)`; elitism | M-4.1, §4 detector |
| 5 | LoRA won't attach to GGUF | Frozen base + in-process adapter; mock/prompt-evolution fallback | L3 mock mode |
| 6 | Overfitting | Train/held-out split; generalization-gap gate | M-2.4, §6 detector |
| 7 | Memory exceeds 2 GB | Peak-RSS monitor with 1.5 GB ceiling | M-1.4, §7 detector |
| 8 | GGUF version lock-in | Pin `ZOE_GGUF_PATH` + adapter hash; upgrade path documented | L3 config |
| 9 | Avatar desync | Lip-sync latency budget | M-6.4, §9 detector |
| 10 | VM escape | VM isolation check + egress allowlist (deny-by-default) | M-5.7, M-5.8 |
| 11 | Audit false negative | Jataka guardrails (L10) + Bio-Audit Jataka in the profile repo | M-5.1 |
| 12 | Soul drift undetected | Sahaja witness (L9) + Bio-Audit Soul | M-6.6 |
| 13 | Kill switch failure | Bio-Audit Dunce circuit breaker + `automation_lock` (profile repo) | Bio-Audit |

`python -m zoe report` prints the active premortem warnings, so a regression in
any of these shows up as a tagged `[§n]` line rather than a silent failure.

## Known limitations

* **M-4.2 Dunce rate (0.375 vs target < 0.20).** On the mock task roughly a
  third of random mutations regress. Elitist selection means this never harms
  the model, but a production system would use a guided mutation proposal
  (e.g. SPSA) to bring this under 20%. Documented honestly rather than tuned
  away.
* **Mock LLM / reservoir.** L1 uses a synthetic LIF reservoir and L3 a mock
  generator by default. Point `ZOE_GGUF_PATH` at a real GGUF with
  `llama-cpp-python` installed to use a real base model.
* **Conceptual layers.** L9/L11 and the “+ peripheral awareness” and
  “+ thought blend” mechanisms are implemented as control logic, in line with
  the SRS scope table.

## License

MIT — see [LICENSE](LICENSE).
