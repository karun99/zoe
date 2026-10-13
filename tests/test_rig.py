from zoe.rig import ZoeRig


def test_run_returns_five_lines(cfg):
    rig = ZoeRig(cfg)
    result = rig.run("build and implement a plan", novelty=0.5)
    assert len(result.output_lines) == cfg.output_lines
    assert result.agent
    assert result.e2e_latency_s >= 0.0


def test_run_uses_ledger(cfg):
    rig = ZoeRig(cfg)
    rig.run("help me understand")
    assert rig.ledger.count("run.start") == 1
    assert rig.ledger.count("run.end") == 1


def test_train_runs_and_records_history(cfg):
    rig = ZoeRig(cfg)
    history = rig.train(generations=30)
    assert len(history) == 31
    assert all(0.0 <= h <= 1.0 for h in history)


def test_report_structure(cfg):
    rig = ZoeRig(cfg)
    report = rig.report(train_generations=20)
    assert "signals" in report
    assert "evaluation" in report
    assert report["summary"]["scored"] > 0
    assert isinstance(report["premortem"], list)
    assert report["signals"]["peak_memory_mb"] >= 0.0
    assert "M-1.4" in {r.id for r in report["evaluation"].results}


def test_companion_mode_integration(cfg):
    rig = ZoeRig(cfg)
    rig.companion.start()
    try:
        result = rig.run("please help and explain")
        assert result.output_lines
    finally:
        rig.companion.stop()


def test_vm_snapshot_after_run(cfg):
    rig = ZoeRig(cfg)
    rig.run("optimize the budget")
    assert rig._vm_handle.state.get("last_command", "").startswith("snapshot:")
