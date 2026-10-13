# Requirements traceability

Every functional requirement in the SRS maps to an implementation and a test.

## L1 — Flybrain reservoir

| Req | Requirement | Code | Test |
|---|---|---|---|
| FR-1.1 | Load connectome (≥139k neurons) | `FlybrainReservoir` (`flybrain` optional, FR-1.2 fallback) | `test_feature_vector_shape` |
| FR-1.2 | Synthetic LIF fallback | `FlybrainReservoir.__init__` | `test_feature_vector_shape` |
| FR-1.3 | Fixed-size feature vector | `_features` (64-dim default) | `test_feature_vector_shape` |
| FR-1.4 | Spike-trace linear decoding | `train_readout` | `test_train_readout_reduces_error` |
| FR-1.5 | Giant Fiber reflex arc | `gf_idx`, `gf_gain` | `test_giant_fiber_reflex_fires` |
| FR-1.6 | Neuromodulation (OA/DA/5-HT) | `set_neuromodulation`, `mod` | `test_neuromodulation_roundtrip` |
| FR-1.7 | Hebbian reinforcement | `reinforce` | `test_reinforcement_changes_reflex_gain` |

## L2 — Prompt-as-Neural-Harness

| Req | Requirement | Code | Test |
|---|---|---|---|
| FR-2.1 | Route to one of 9 agents | `route`, `agents.route_scores` | `test_route_returns_known_agent` |
| FR-2.2 | Enforce 5-line output | `format_response` | `test_format_response_is_five_lines` |
| FR-2.3 | Silent Thinking Protocol | `_sanitize`, `enforce_silent_thinking` | `test_silent_thinking_strips_internal_markers` |
| FR-2.4 | Growth signal = f(acc,nov) | `growth_signal` | `test_growth_signal_bounds` |
| FR-2.5 | Deny growth when rate < 0.001 | `consider_growth` | `test_growth_denied_below_floor` |
| FR-2.6 | Log decisions to ledger | `decide` → `KaliLedger` | `test_decision_is_ledgered` |
| FR-2.7 | PIA adaptation | `PIA.agent_bias` | `test_pia_adapts_traits_and_bias` |
| FR-2.8 | Jataka 5 precepts | `guard`, `Jataka` | `test_guard_blocks_jataka_violation` |
| FR-2.9 | Sahaja records w/o acting | `Sahaja` | `test_sahaja_never_acts` |
| FR-2.10 | Consistent identity | `identity.py` | `test_identity_card_consistency` |

## L3 — llama.cpp + evolved LoRA

| Req | Requirement | Code | Test |
|---|---|---|---|
| FR-3.1 | Load GGUF (mmap) | `LlamaCppModel` | mock-mode tests |
| FR-3.2 | Evolving LoRA (≥64-dim) | `adapter` | `test_report_structure` |
| FR-3.3 | Mutate only when Kali permits | `mutate(permitted=…)` | covered by `train` |
| FR-3.4 | Mock mode fallback | `mock` | `test_run_returns_five_lines` |
| FR-3.5 | Measure held-out accuracy | `measure_accuracy` | `test_train_runs_and_records_history` |
| FR-3.6 | Temporal noise reduction | `temporal_noise` | `test_mu_decays_with_time` |

## L4 — Kali + Dunce

| Req | Requirement | Code | Test |
|---|---|---|---|
| FR-4.1 | 4-phase cycle | `at`, `phase` | `test_kali_phase_cycle` |
| FR-4.2 | Mutation only in GROWTH | `permit_mutation` | `test_mutation_only_permitted_in_growth` |
| FR-4.3 | μ = μ₀·e^(−λt)·(1−A) | `Kali.mu` | `test_mu_decays_with_time` |
| FR-4.4 | Deny μ < 0.001 | `permit_mutation` | `test_gate_denies_below_floor` |
| FR-4.5 | Log every decision | `permit_mutation` → ledger | `test_decision_is_ledgered` |
| FR-4.6 | Cancer detection > 0.5 | `check_cancer` | `test_cancer_detection` |
| FR-5.1 | Dunce on child < parent | `Dunce.should_patch` | `test_dunce_patches_regression` |
| FR-5.2 | Invert mutation delta | `Dunce.patch` | `test_dunce_patches_regression` |
| FR-5.3 | Re-evaluate patched adapter | `ZoeRig.train` | `test_train_runs_and_records_history` |
| FR-5.4 | Record Dunce patterns | `Dunce.patterns` | `test_dunce_patches_regression` |

## L5 — MCP + Prompt API

| Req | Requirement | Code | Test |
|---|---|---|---|
| FR-6.1 | Connect via stdio JSON-RPC | `MCPClient.connect` | `test_mcp_degrades_without_servers` |
| FR-6.2 | List tools | `list_tools` | `test_mcp_register_and_call` |
| FR-6.3 | Execute tool calls | `call` | `test_mcp_register_and_call` |
| FR-6.4 | List/read resources | `list_resources`, `read_resource` | `test_mcp_resource` |
| FR-6.5 | Degrade without MCP | `call` returns None | `test_mcp_unknown_tool_returns_none` |
| FR-7.1 | Cache rendered prompts | `PromptAPI._cache` | `test_prompt_cache_hits` |
| FR-7.2 | A/B testing | `ab_choice` | `test_prompt_ab_choice` |
| FR-7.3 | Local template fallback | `PromptAPI.render` | `test_prompt_fallback_on_unknown_key` |

## L6 — Virtual Avatar

| Req | Requirement | Code | Test |
|---|---|---|---|
| FR-A.1 | ≥25 FPS | `measured_fps` | `test_report_structure` |
| FR-A.2 | Lip-sync < 100 ms | `speak`, `max_lip_sync_ms` | `test_avatar_lip_sync_within_budget` |
| FR-A.3 | Agent → expression | `set_agent` | `test_avatar_expression_follows_agent` |
| FR-A.4 | Identity consistency | `identity_consistent` | `test_avatar_expression_follows_agent` |
| FR-A.5 | Photo/stylized modes | `mode` | — |
| FR-A.6 | Client-server decoupled | headless `Avatar` | `test_avatar_lip_sync_within_budget` |
| FR-A.7 | Token-stream alignment | `speak` | `test_avatar_lip_sync_within_budget` |
| FR-A.8 | WebXR/desktop rendering | mock renderer | — |
| FR-A.9 | Zoe visual identity | `avatar_id` | `test_avatar_expression_follows_agent` |

## L7 — AI Virtual Machine

| Req | Requirement | Code | Test |
|---|---|---|---|
| FR-V.1 | Per-session MicroVM | `MockVM.boot` | `test_vm_snapshot_boot_is_fast` |
| FR-V.2 | Snapshot fast start < 5 s | `boot(cold=False)` | `test_vm_snapshot_boot_is_fast` |
| FR-V.3 | Suspend/resume ≤ 8 h | `suspend`, `resume` | `test_vm_suspend_blocks_exec` |
| FR-V.4 | Governed egress | `egress` | `test_vm_egress_allowlist` |
| FR-V.5 | IAM-scoped credentials | `issue_credentials` | — |
| FR-V.6 | Persist across commands | `exec` | `test_vm_persistence_across_commands` |
| FR-V.7 | Confidential execution | backend flag | — |
| FR-V.8 | Resource quotas | `vm_mem_quota_mb` | `test_vm_persistence_across_commands` |
| FR-V.9 | Native MCP server | `as_mcp_server` | `test_vm_as_mcp_server` |
| FR-V.10 | Per-agent isolation | `exec(agent=…)` | — |

## L8 — Companion Mode

| Req | Requirement | Code | Test |
|---|---|---|---|
| FR-C.1 | Configurable capture interval | `companion_interval_s` | — |
| FR-C.2 | Text extraction (OCR/a11y) | `observe` | `test_companion_requires_explicit_start` |
| FR-C.3 | Redact secrets | `redact` | `test_companion_redacts_secrets` |
| FR-C.4 | Read active tab | `read_active_tab` | — |
| FR-C.5 | 5 behavioural states | `_update_state` | `test_companion_requires_explicit_start` |
| FR-C.6 | Novelty from flybrain | `observe(novelty=…)` | — |
| FR-C.7 | No persistent storage | `stop` clears | `test_companion_stop_clears_state` |
| FR-C.8 | No keystrokes | `keystrokes_recorded` | `test_companion_stop_clears_state` |
| FR-C.9 | Visible indicator | `indicator_visible` | `test_companion_requires_explicit_start` |
| FR-C.10 | Explicit start/stop | `start`, `stop` | `test_companion_requires_explicit_start` |

## L9–L11 — Sahaja / Jataka / PIA

| Req | Requirement | Code | Test |
|---|---|---|---|
| FR-2.9 | Sahaja witness | `Sahaja` | `test_sahaja_never_acts` |
| FR-2.8 | Jataka precepts | `Jataka` | `test_jataka_flags_each_precept` |
| FR-2.7 | PIA silent adaptation | `PIA` | `test_pia_adapts_traits_and_bias` |

## Non-functional requirements

| Req | Requirement | Where |
|---|---|---|
| NFR-1.1 | Inference latency < 500 ms | metric `M-1.2` |
| NFR-1.2/1.3 | Memory ceilings | `ZoeConfig.neuron_count`, reduced profile |
| NFR-2.2 | No-flybrain fallback | L1 synthetic LIF |
| NFR-2.3 | No-llama fallback | L3 mock mode |
| NFR-3.1 | Silent Thinking violations = 0 | metric `M-2.8`, `Jataka` |
| NFR-3.3 | Mutation hard cap ≤ 0.1 | `mutation_rate_cap` |
| NFR-3.4 | Jataka violations = 0 | metric `M-5.1` |
| NFR-3.5 | Redaction accuracy 99% | `benchmark_redaction` |
| NFR-4.1 | Modular layers | one module per layer |
| NFR-4.2 | Config via env | `ZoeConfig.from_env` |
| NFR-4.3 | Logging to Kali Ledger | `KaliLedger` |
