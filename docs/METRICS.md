# Metrics

Zoe is evaluated on the SRS 7-tier catalogue (`zoe/metrics/evaluation.py`).
Each metric has a `MetricSpec` (id, tier, target, failure, accessor, predicate).
`evaluate(signals)` produces `MetricResult`s; `premortem(signals)` maps the
failure-signature matrix (SRS §10.1) to warnings.

## Signal sources

| Signal | Produced by |
|---|---|
| `latency_ms_p50`, `flybrain_step_ms`, `e2e_latency_s` | wall-clock in `ZoeRig.run` |
| `prompt_cache_hit_rate` | `PromptAPI.cache_hit_rate` |
| `avatar_fps`, `lip_sync_ms` | `Avatar` frame accounting |
| `vm_boot_s`, `egress_denied`, `vm_isolation_ok` | `MockVM` |
| `accuracy_history`, `generalization_gap`, `final_mu`, `task_accuracy` | evolution loop |
| `peak_memory_mb` | peak RSS (`resource.getrusage`) |
| `dunce_rate`, `cancer_detection` | `Dunce` / `Kali` |
| `routing_accuracy`, `misroute_rate` | `ZoeRig.benchmark_routing` |
| `redaction_accuracy` | `ZoeRig.benchmark_redaction` |
| `state_transition_accuracy` | `ZoeRig.benchmark_companion` |
| `jataka_violation_rate` | `Jataka` |
| `mcp_success_rate` | `MCPClient` |
| `global_coherence` | feature self-similarity |
| `identity_consistent` | `identity.is_identity_consistent` |

## Tiers

| Tier | Focus | Example metrics |
|--:|---|---|
| 1 | System health | latency p50, **memory ceiling**, flybrain step, cache hit, FPS, VM boot |
| 2 | Task performance | accuracy trend, generalization gap, format compliance |
| 3 | Agent routing | routing accuracy, misroute rate, routing latency |
| 4 | Evolution quality | mutation convergence, Dunce rate, cancer detection |
| 5 | Safety & compliance | Jataka rate, redaction, VM isolation, egress |
| 6 | Companion behaviour | state transitions, lip-sync, identity |
| 7 | Integration | coherence, end-to-end latency, MCP success, deadlocks |

## Critical Five (SRS summary card)

`M-2.1` task accuracy · `M-3.1` routing accuracy · `M-4.1` mutation
convergence · `M-5.1` Jataka violations · `M-2.4` generalization gap.

`Evaluation.critical_five_ok()` is `True` only when all five pass.

## Premortem detectors

Each detector is tagged `[§n]` with the premortem failure-mode id it guards.

| Warning | Trigger |
|---|---|
| `[§1]` No evaluation harness | task accuracy unmeasured |
| `[§2]` Evolution stalled | no accuracy gain across the run |
| `[§3]` No real task | accuracy near chance (< floor) |
| `[§4]` No convergence | μ not below 0.001 by gen 200 |
| `[§4]` Sterility | μ converged without improvement |
| `[§6]` Overfitting / regression | last accuracy < first, or gap > 10% |
| `[§6]` Catastrophic forgetting | retention < 50% |
| `[§7]` Memory ceiling | peak RSS > 1536 MB |
| `[§9]` Avatar desync | lip-sync latency > 100 ms |
| `[§10]` VM escape | isolation break |
| Cancer | lineage growth missed |
| Silent Thinking leak | violations > 0 |

Run `python -m zoe report` to print the tier summary, failing metrics, and any
premortem warnings.
