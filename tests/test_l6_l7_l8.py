import pytest

from zoe.layers import Avatar, CompanionMode, EgressViolation, MockVM
from zoe.ledger import KaliLedger


# --- L6 Avatar --------------------------------------------------------------
def test_avatar_lip_sync_within_budget(cfg):
    a = Avatar(cfg)
    a.set_agent("GREEN")
    frames = a.speak("hello world from zoe".split())
    assert len(frames) == 4
    assert a.max_lip_sync_ms < cfg.lip_sync_budget_ms


def test_avatar_expression_follows_agent(cfg):
    a = Avatar(cfg)
    assert a.set_agent("BLUE") == "soft eyes, open posture"
    assert a.identity_consistent()


# --- L7 AI VM ---------------------------------------------------------------
def test_vm_snapshot_boot_is_fast(cfg):
    vm = MockVM(cfg, KaliLedger(cfg.ledger_path))
    h = vm.boot(cold=False)
    assert h.snapshot is True
    assert h.boot_time_s < cfg.vm_boot_budget_s


def test_vm_egress_allowlist(cfg):
    vm = MockVM(cfg, KaliLedger(cfg.ledger_path))
    assert vm.egress("api.github.com") is True
    with pytest.raises(EgressViolation):
        vm.egress("evil.example.com")
    assert vm.egress_denied == 1


def test_vm_persistence_across_commands(cfg):
    vm = MockVM(cfg, KaliLedger(cfg.ledger_path))
    h = vm.boot()
    vm.exec(h, "a")
    vm.exec(h, "b")
    assert h.state["processes"] == ["a", "b"]


def test_vm_suspend_blocks_exec(cfg):
    vm = MockVM(cfg, KaliLedger(cfg.ledger_path))
    h = vm.boot()
    vm.suspend(h)
    with pytest.raises(RuntimeError):
        vm.exec(h, "x")
    vm.resume(h)
    assert vm.exec(h, "x")["ok"] is True


def test_vm_as_mcp_server(cfg):
    vm = MockVM(cfg, KaliLedger(cfg.ledger_path))
    client = vm.as_mcp_server()
    assert client.call("vm.run", command="echo hi")["ok"] is True


# --- L8 Companion Mode ------------------------------------------------------
def test_companion_requires_explicit_start(cfg):
    c = CompanionMode(cfg, KaliLedger(cfg.ledger_path))
    with pytest.raises(RuntimeError):
        c.observe("hello")
    c.start()
    assert c.indicator_visible
    assert c.observe("hello", active_window="a").state == "curious"


def test_companion_redacts_secrets(cfg):
    c = CompanionMode(cfg, KaliLedger(cfg.ledger_path))
    text = "password: hunter2 email a@b.com card 4111 1111 1111 1111"
    out = c.redact(text)
    assert "hunter2" not in out
    assert "a@b.com" not in out
    assert "4111" not in out
    assert out.count("[REDACTED]") >= 3


def test_companion_stop_clears_state(cfg):
    c = CompanionMode(cfg, KaliLedger(cfg.ledger_path))
    c.start()
    c.observe("x", active_window="a")
    c.stop()
    assert c._observations == []
    assert c.keystrokes_recorded == 0
