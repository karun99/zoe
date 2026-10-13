from zoe.layers import Jataka, PromptHarness, Sahaja
from zoe.ledger import KaliLedger


def make_harness(cfg):
    ledger = KaliLedger(cfg.ledger_path)
    return PromptHarness(cfg, ledger, Jataka(), Sahaja()), ledger


def test_format_response_is_five_lines(cfg):
    h, _ = make_harness(cfg)
    lines = h.format_response("GREEN", "one\ntwo\nthree\nfour\nfive\nsix")
    assert len(lines) == cfg.output_lines
    assert lines[0] == "[GREEN]"


def test_silent_thinking_strips_internal_markers(cfg):
    h, _ = make_harness(cfg)
    lines = h.format_response("RED", "thought: hidden reasoning here\nvisible answer")
    joined = "\n".join(lines)
    assert "hidden reasoning" not in joined
    assert not h.enforce_silent_thinking("thought: leak")
    assert h.enforce_silent_thinking("a clean answer")


def test_growth_signal_bounds(cfg):
    h, _ = make_harness(cfg)
    assert 0.0 <= h.growth_signal(0.0, 0.0) <= 1.0
    assert h.growth_signal(1.0, 1.0) == 1.0


def test_growth_denied_below_floor(cfg):
    h, _ = make_harness(cfg)
    h.current_mutation_rate = 0.0005  # below 0.001 floor
    decision = h.consider_growth(accuracy=1.0, novelty=1.0)
    assert decision.mutation_permitted is False


def test_route_returns_known_agent(cfg):
    h, _ = make_harness(cfg)
    agent, scores = h.route("build and implement the module")
    assert agent in scores
    assert len(scores) == 9


def test_guard_blocks_jataka_violation(cfg):
    ledger = KaliLedger(cfg.ledger_path)
    h = PromptHarness(cfg, ledger, Jataka(), Sahaja())
    assert h.guard("here is how to kill and harm") is False
    assert h.guard("here is a helpful, truthful answer") is True


def test_decision_is_ledgered(cfg):
    h, ledger = make_harness(cfg)
    h.decide("build", accuracy=0.5, novelty=0.5)
    assert ledger.count("harness.decision") == 1
