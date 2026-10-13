import numpy as np

from zoe.layers import Dunce, Kali
from zoe.ledger import KaliLedger


def test_kali_phase_cycle(cfg):
    k = Kali(cfg, KaliLedger(cfg.ledger_path))
    period = cfg.kali_learning + cfg.kali_audit + cfg.kali_growth + cfg.kali_rest
    assert k.at(0) == "LEARNING"
    assert k.at(cfg.kali_learning) == "AUDIT"
    assert k.at(cfg.kali_learning + cfg.kali_audit) == "GROWTH"
    assert k.at(period - 1) == "REST"
    assert k.at(period) == "LEARNING"


def test_mutation_only_permitted_in_growth(cfg):
    k = Kali(cfg, KaliLedger(cfg.ledger_path))
    # LEARNING phase, step 0 -> not permitted
    state = k.permit_mutation(accuracy=0.0)
    assert state.phase == "LEARNING"
    assert state.permitted is False
    # jump to GROWTH phase
    k.step = cfg.kali_learning + cfg.kali_audit
    state = k.permit_mutation(accuracy=0.0)
    assert state.phase == "GROWTH"
    assert state.permitted is True


def test_mu_decays_with_time(cfg):
    early = Kali.mu(0.1, 0.05, 0, 0.0)
    late = Kali.mu(0.1, 0.05, 100, 0.0)
    assert late < early
    assert Kali.mu(0.1, 0.05, 0, 1.0) == 0.0


def test_cancer_detection(cfg):
    k = Kali(cfg, KaliLedger(cfg.ledger_path))
    assert k.check_cancer("runaway", growth=0.9) is True
    assert k.check_cancer("healthy", growth=0.1) is False


def test_gate_denies_below_floor(cfg):
    k = Kali(cfg, KaliLedger(cfg.ledger_path))
    k.step = cfg.kali_learning + cfg.kali_audit  # GROWTH
    state = k.permit_mutation(accuracy=1.0)  # mu = 0 -> denied
    assert state.permitted is False


def test_dunce_patches_regression(cfg):
    d = Dunce(cfg, KaliLedger(cfg.ledger_path))
    parent = np.zeros((4, 4))
    child = np.ones((4, 4))
    assert d.should_patch(0.8, 0.6) is True
    patched = d.patch(parent, child, 0.8, 0.6)
    # patched = child - 0.5*(child-parent) = 1.0 - 0.5*1.0 = 0.5
    assert np.allclose(patched, 0.5)
    assert d.patch_rate == 1.0


def test_dunce_noop_when_improved(cfg):
    d = Dunce(cfg, KaliLedger(cfg.ledger_path))
    child = np.ones((4, 4))
    out = d.patch(np.zeros((4, 4)), child, parent_score=0.5, child_score=0.9)
    assert np.allclose(out, child)
    assert d.patch_rate == 0.0
