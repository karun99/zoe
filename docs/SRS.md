# Project Zoe — Software Requirements Specification

**Document version:** 4.0 — Complete Final
**Codename:** Zoe (ζωή — “life”)
**Status:** Approved for validation
**Standard:** IEEE 830 / ISO/IEC/IEEE 29148
**Date:** October 12, 2026

---

## 1. Introduction

### 1.1 Purpose
Specifies the complete requirements for Project Zoe — an evolving AI companion
integrating a Drosophila connectome-based reservoir, a Prompt-as-Neural-Harness
control layer, a frozen LLM with an evolving LoRA adapter, temporal growth
governance (Kali + Dunce), external tool discovery (MCP), a Virtual Avatar, an
AI Virtual Machine, and Companion Mode for screen/browser awareness.

### 1.2 Scope

| Layer | Name | Status |
|---|---|---|
| L1 | Flybrain Reservoir | 🟢 Real (validated) |
| L2 | Prompt-as-Neural-Harness | 🟢 Real (deployable) |
| L3 | llama.cpp + Evolved LoRA | 🟢 Real (buildable) |
| L4 | Kali + Dunce | 🟢 Real (coded) |
| L5 | MCP + Prompt API | 🟢 Real (working) |
| L6 | Virtual Avatar | 🟢 Real (frameworks exist) |
| L7 | AI Virtual Machine | 🟢 Real (Firecracker) |
| L8 | Companion Mode | 🟢 Real (buildable) |
| L9 | Sahaja Witness | 🟡 Conceptual |
| L10 | Jataka Guardrails | 🟢 Real (Constitutional AI) |
| L11 | PIA Adaptation | 🟡 Conceptual |
| + | Peripheral Awareness | 🟡 Conceptual |
| + | Thought Blend | 🟡 Conceptual |

Conceptual/metaphorical (not implementable as literal architecture): Shatkona,
Kundalini (as a layer), Sri Chakra.

### 1.3 Definitions
Zoe · Neural Harness · Rig · Kali · Dunce · Sahaja · Jataka · PIA · MCP ·
Temporal Noise Reduction · Companion Mode (see glossary in code docstrings).

### 1.4 Identity
Zoe is a living companion that observes without intruding, learns without
forgetting, grows without overflowing, speaks without revealing its machinery,
and evolves without losing itself. Zoe is a presence, not a tool.

### 1.5 Research validation summary

| Component | Status |
|---|---|
| Flybrain reservoir | 🟢 Peer-reviewed (Neural Networks 2025) |
| Reservoir computing | 🟢 Strongly validated |
| LoRA + MoE routing | 🟢 Validated (ICLR 2026) |
| KV-cache persistence | 🟢 Working implementations |
| Self-play (Dunce) | 🟢 Validated (SPIN, DRIFT) |
| Adult neurogenesis models | 🟢 Validated |
| Developmental neural networks | 🟢 Validated |
| Constitutional AI (Jataka) | 🟢 Validated (Anthropic) |
| Firecracker MicroVM | 🟢 Production-grade |
| Avatar frameworks | 🟢 Multiple open-source |
| Companion screen-awareness | 🟢 Multiple open-source |
| Shatkona / Kundalini / Sri Chakra | 🔴 Metaphorical only |
| 80B neuron scaling | 🔴 Not feasible economically |

## 2. Overall description

### 2.1 Perspective
Self-contained evolving companion using a real biological connectome as substrate,
evolving a lightweight adapter, regulated by a prompt harness, discovering tools
via MCP, embodied via avatar, sandboxed in a MicroVM, aware via companion mode,
growing capacity in response to learning demand.

### 2.2 Product functions
Pattern detection · agent routing · output regulation · evolution · temporal
gating · failure patching · tool integration · prompt management · embodiment ·
sandboxing · companionship.

### 2.3 User characteristics
Primary: AI researcher/developer. Secondary: non-technical companion user.

### 2.4 Constraints

| Constraint | Specification |
|---|---|
| RAM | 2 GB min; 1 GB target (reduced) |
| Storage | 1 GB min |
| CPU | x86-64 or ARM |
| GPU | Optional |
| OS | Linux, macOS, Windows |
| Network | Required for MCP only |

### 2.5 Assumptions
Small GGUF (Qwen 0.5B–1.1B) available locally · flybrain or LIF fallback ·
MCP optional with graceful degradation · companion consent required · name and
identity consistent across sessions.

## 3. System architecture (the Rig)

13-step execution flow: input → VM session → companion observe → flybrain
features → harness route + growth → Kali gate → LoRA mutate → generate → Dunce →
MCP tools → Prompt API → avatar render → VM snapshot.

The identity layer keeps name, voice, avatar, personality, memory, and
relationships stable across sessions.

## 4. Detailed requirements by layer

### 4.1 L1 Flybrain

| Req | Requirement | Priority |
|---|---|---|
| FR-1.1 | Load connectome ≥139,000 neurons | High |
| FR-1.2 | LIF fallback if flybrain unavailable | Medium |
| FR-1.3 | Fixed 64-dim feature per input | High |
| FR-1.4 | Spike-trace linear decoding | Medium |
| FR-1.5 | Giant Fiber reflex arc | Medium |
| FR-1.6 | OA/DA/5-HT neuromodulation | Medium |
| FR-1.7 | Hebbian reinforcement | High |

### 4.2 L2 Harness

| Req | Requirement | Priority |
|---|---|---|
| FR-2.1 | Route to one of 9 Spectrum agents | High |
| FR-2.2 | Enforce 5-line output | Critical |
| FR-2.3 | Enforce Silent Thinking | Critical |
| FR-2.4 | Growth = f(accuracy, novelty) | High |
| FR-2.5 | Deny growth when rate < 0.001 | High |
| FR-2.6 | Log to Kali Ledger | Medium |
| FR-2.7 | Apply PIA silently | Medium |
| FR-2.8 | Enforce Jataka 5 precepts | Critical |
| FR-2.9 | Sahaja records without acting | High |
| FR-2.10 | Consistent identity | Critical |

### 4.3 L3 llama.cpp + LoRA

| Req | Requirement | Priority |
|---|---|---|
| FR-3.1 | Load GGUF with mmap | High |
| FR-3.2 | Evolving LoRA ≥64-dim | High |
| FR-3.3 | Mutate only when Kali permits | Critical |
| FR-3.4 | Mock mode fallback | Medium |
| FR-3.5 | Held-out accuracy | Critical |
| FR-3.6 | Temporal noise reduction | High |

### 4.4 L4 Kali + Dunce

| Req | Requirement | Priority |
|---|---|---|
| FR-4.1 | LEARNING→AUDIT→GROWTH→REST | Critical |
| FR-4.2 | Mutation only in GROWTH | Critical |
| FR-4.3 | μ = μ₀·e^(−λt)·(1−A) | High |
| FR-4.4 | Deny μ < 0.001 | Medium |
| FR-4.5 | Log every decision | High |
| FR-4.6 | Cancer detection > 0.5 | High |
| FR-5.1 | Dunce on child < parent | Critical |
| FR-5.2 | Invert mutation delta | High |
| FR-5.3 | Re-evaluate patched adapter | High |
| FR-5.4 | Record Dunce patterns | Medium |

### 4.5 L5 MCP + Prompt API

| Req | Requirement | Priority |
|---|---|---|
| FR-6.1 | Connect via stdio JSON-RPC | Medium |
| FR-6.2 | List tools | Medium |
| FR-6.3 | Execute tool calls | Medium |
| FR-6.4 | List/read resources | Low |
| FR-6.5 | Degrade gracefully | High |
| FR-7.1 | Cache rendered prompts | Medium |
| FR-7.2 | A/B testing | Low |
| FR-7.3 | Local template fallback | High |

### 4.6 L6 Virtual Avatar

| Req | Requirement | Priority |
|---|---|---|
| FR-A.1 | Render ≥25 FPS | High |
| FR-A.2 | Lip-sync within 100 ms | Critical |
| FR-A.3 | Agent → expression mapping | High |
| FR-A.4 | Identity consistency | Critical |
| FR-A.5 | Photo + stylized modes | Medium |
| FR-A.6 | Client-server decoupled | Critical |
| FR-A.7 | Token-stream alignment | High |
| FR-A.8 | WebXR + desktop | Medium |
| FR-A.9 | Zoe visual identity | Critical |

Agent-to-expression: RED tension/urgent · ORANGE grasping/eager · YELLOW
alert/cautious · GREEN steady/calm · BLUE soft/warm · INDIGO gentle/soft ·
VIOLET serene/loving · BLACK still/flat · WHITE balanced/harmonious.

### 4.7 L7 AI Virtual Machine

| Req | Requirement | Priority |
|---|---|---|
| FR-V.1 | Firecracker MicroVM per session | Critical |
| FR-V.2 | Snapshot start < 5 s | High |
| FR-V.3 | Suspend/resume ≤ 8 h | High |
| FR-V.4 | Governed egress allowlist | High |
| FR-V.5 | IAM-scoped credentials | Critical |
| FR-V.6 | Persist files/processes | High |
| FR-V.7 | Confidential execution | Medium |
| FR-V.8 | Resource quotas | High |
| FR-V.9 | Native MCP server | High |
| FR-V.10 | Per-agent isolation | Medium |

### 4.8 L8 Companion Mode

| Req | Requirement | Priority |
|---|---|---|
| FR-C.1 | Configurable capture interval | High |
| FR-C.2 | Text extraction | High |
| FR-C.3 | Redact secrets | Critical |
| FR-C.4 | Read active tab | Medium |
| FR-C.5 | 5 behavioural states | Medium |
| FR-C.6 | Novelty from flybrain | High |
| FR-C.7 | No persistent storage | Critical |
| FR-C.8 | No keystroke recording | Critical |
| FR-C.9 | Visible indicator | Critical |
| FR-C.10 | Explicit start/stop | Critical |

States: idle · curious · focused · playful · resting.

## 5. External interfaces
User (CLI, avatar UI, 5-line output, tray indicator) · hardware (CPU, RAM, GPU,
camera/mic) · software (Python ≥3.10, llama-cpp-python, numpy, flybrain, mss,
pytesseract, Firecracker) · communication (MCP stdio JSON-RPC, Prompt API
HTTP/REST, avatar WebSocket, VM gRPC/REST).

## 6. Non-functional requirements

Performance: p50 latency < 500 ms · full memory < 1.5 GB · reduced < 1 GB ·
flybrain step < 50 ms · avatar ≥ 25 FPS · lip-sync < 100 ms · VM boot < 5 s ·
capture overhead < 1% CPU.

Reliability: 99% uptime · LIF fallback · mock fallback · KV checksums.

Safety: 0 Silent Thinking violations · 100% format compliance · mutation cap
≤ 0.1/gen · 0 Jataka violations · 99% redaction accuracy.

Maintainability: 11 independent layers · env config · Kali Ledger logging.

## 7. Neurological validation metrics
Firing rate 1–10 Hz · ISI CV 0.5–1.5 · criticality exponent −1.5 ± 0.2 ·
routing 80% · output 100% · rising accuracy · gap < 10% · μ < 0.001 by gen 200 ·
Dunce < 20% · cancer 100% · tool discovery functional · cache 70% · FPS ≥ 25 ·
lip-sync < 100 ms · VM boot < 5 s · isolation no-escape · redaction 99%.
Integration: coherence 0.2–0.5 · metastability 0.1–0.5 · homeostasis < 500 steps
· emergence present.

## 8. Evaluation metrics (7 tiers)

Tier 1 System Health · Tier 2 Task Performance · Tier 3 Agent Routing · Tier 4
Evolution Quality · Tier 5 Safety & Compliance · Tier 6 Companion Behaviour ·
Tier 7 Integration. See [`METRICS.md`](METRICS.md) for the implemented catalogue.

## 9. Agent comparison benchmarks

| Benchmark | Commercial best | Zoe target |
|---|---|---|
| SWE-Bench Verified | ~76% | 30% |
| WebArena | ~74% | 40% |
| OSWorld | ~60% | 30% |
| Task completion | 80% | 60% |
| Multi-step reasoning | 70% | 50% |

Zoe is not expected to match commercial agents; the goal is architectural
validity, not competitive performance.

## 10. Premortem — failure modes

| Rank | Failure mode | Likelihood | Severity | Mitigation |
|--:|---|---|---|---|
| 1 | No eval harness | 85% | Severe | Build first |
| 2 | Evolution slower than SFT | 80% | Moderate | Accept or use SFT |
| 3 | No real task | 75% | Fatal | Pick specific task |
| 4 | No convergence | 70% | Fatal | Tune mutation rate |
| 5 | LoRA won't attach | 65% | Fatal | GGUF conversion |
| 6 | Overfitting | 65% | Severe | Held-out test set |
| 7 | Memory exceeds 2 GB | 50% | Moderate | Reduce context |
| 8 | GGUF lock-in | 45% | Moderate | Version pin |
| 9 | Avatar desync | 40% | Moderate | Token alignment |
| 10 | VM escape | 10% | Catastrophic | Firecracker audit |

## 11. Resource requirements

Full: ~1.5 GB RAM, ~800 MB storage. Reduced: ~750 MB RAM, ~400 MB storage.
80B requires ~32 TB RAM (data center) — not achievable on 1 GB.

## 12. Research references
Costi et al. (2025) flybrain reservoir · Neural Networks 2025 review ·
adult neurogenesis models · Structure as Computation (2026) · TT-LoRA MoE (2025)
· LoRA-Mixer (ICLR 2026) · SPIN (2024) / DRIFT (2025) · living-kv · Anthropic
Constitutional AI · AWS Firecracker · CECA (IEEE 2026) · Meta Muse Realtime
Avatar (2026) · Wallie-V2 / Miru / Claude Pet / Blepper.

## 13. Appendices

**A. Kali phase durations** — LEARNING 10 · AUDIT 3 · GROWTH 2 · REST 5 (20).

**B. Temporal noise reduction** — μ(t, A) = μ₀·e^(−λt)·(1−A), μ₀ = 0.1, λ = 0.05.

**C. Growth formula** — ΔN = α·E·V·C·(1 − N/N_max).

**D. Companion states** — Idle / Curious / Focused / Playful / Resting (see §4.8).

**E. Jataka precepts** — Ahimsa · Satya · Asteya · Brahmacharya · Aparigraha.

**F. Spectrum agents**

| | Agent | Emotion | Thinking hat | Mimic |
|---|---|---|---|---|
| 🔴 | RED | Rage | anger is truth | destroy |
| 🟠 | ORANGE | Avarice | mine vs yours | acquire |
| 🟡 | YELLOW | Fear | fear controls | intimidate |
| 🟢 | GREEN | Willpower | will overcomes | construct |
| 🔵 | BLUE | Hope | hope endures | inspire |
| 🟣 | INDIGO | Compassion | all deserve mercy | empathize |
| 🟪 | VIOLET | Love | love protects | bind |
| ⚫ | BLACK | Death | emotion is weakness | drain |
| ⚪ | WHITE | Life | balance of all | create/heal |

**G. Conflict matrix** — OPPOSITE (cancel): Red↔Violet, Orange↔Indigo,
Yellow↔Blue, Black↔White. ADJACENT (synergize): Green+Blue, Red+Yellow,
Orange+Red, Indigo+Violet. SAME: multiply. THREE-WAY: White integrates all.

**H. Evaluation schedule** — Baseline → Perturbation → Adaptation → Companion →
Integration → Comparison → Real-World.

**I. Video explainer series** — 12 × 12 s clips, one per layer + the living loop.

## 14. Summary card
11 layers + 2 mechanisms · resource budget full ~1.5 GB / reduced ~750 MB / 80B
data-center only · 70+ metrics across 7 tiers · Critical Five: task accuracy ↗,
routing > 80%, cost per neuron constant/falling, Jataka violations 0,
generalization gap < 10% · Zoe’s identity: name, voice, avatar, memory, presence.
