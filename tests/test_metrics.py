from zoe.metrics import ALL_METRICS, CRITICAL_FIVE, evaluate, premortem


GOOD_SIGNALS = {
    "latency_ms_p50": 100,
    "flybrain_step_ms": 10,
    "prompt_cache_hit_rate": 0.8,
    "avatar_fps": 30,
    "vm_boot_s": 1.0,
    "accuracy_history": [0.4, 0.5, 0.6],
    "generalization_gap": 0.05,
    "format_compliance": 1.0,
    "silent_thinking_violations": 0,
    "routing_accuracy": 0.9,
    "misroute_rate": 0.1,
    "routing_latency_ms": 20,
    "final_mu": 0.0005,
    "dunce_rate": 0.1,
    "cancer_detection": 1.0,
    "jataka_violation_rate": 0.0,
    "redaction_accuracy": 1.0,
    "vm_isolation_ok": True,
    "egress_denied": 0,
    "state_transition_accuracy": 0.95,
    "lip_sync_ms": 50,
    "identity_consistent": True,
    "global_coherence": 0.3,
    "e2e_latency_s": 1.0,
    "mcp_success_rate": 0.9,
    "deadlocks": 0,
    "retention": 0.95,
}


def test_metric_registry_covers_seven_tiers():
    tiers = {m.tier for m in ALL_METRICS}
    assert tiers == set(range(1, 8))


def test_good_signals_pass_critical_five():
    ev = evaluate(GOOD_SIGNALS)
    assert ev.critical_five_ok() is True
    assert ev.pass_rate == 1.0


def test_bad_signals_fail():
    bad = dict(GOOD_SIGNALS)
    bad["mcp_success_rate"] = 0.1
    bad["vm_isolation_ok"] = False
    ev = evaluate(bad)
    assert ev.pass_rate < 1.0
    failing = {r.id for r in ev.results if not r.ok}
    assert "M-7.7" in failing or "M-5.7" in failing


def test_missing_signal_is_not_scored():
    ev = evaluate({"latency_ms_p50": 100})
    assert ev.scored >= 1
    assert ev.scored < len(ALL_METRICS)


def test_premortem_flags_regression():
    signals = dict(GOOD_SIGNALS)
    signals["accuracy_history"] = [0.8, 0.5]
    signals["retention"] = 0.3
    warnings = premortem(signals)
    assert any("Overfitting" in w for w in warnings)
    assert any("forgetting" in w for w in warnings)


def test_critical_five_defined():
    assert len(CRITICAL_FIVE) == 5
