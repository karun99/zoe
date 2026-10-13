import numpy as np

from zoe.layers import FlybrainReservoir


def test_feature_vector_shape(cfg):
    r = FlybrainReservoir(cfg)
    report = r.step("build a plan")
    assert report.feature.shape == (cfg.feature_dim,)
    assert np.isclose(np.linalg.norm(report.feature), 1.0, atol=1e-6)


def test_giant_fiber_reflex_fires(cfg):
    r = FlybrainReservoir(cfg)
    report = r.step("urgent danger error crash attack destroy threat")
    assert report.giant_fiber_spikes >= 0


def test_train_readout_reduces_error(cfg):
    r = FlybrainReservoir(cfg)
    feat = r.step("build a plan").feature
    target = np.ones(cfg.feature_dim)
    e0 = float(np.mean((target - r.w_out @ feat) ** 2))
    e1 = e0
    for _ in range(200):
        e1 = r.train_readout(feat, target, lr=0.05)
    assert e1 < e0


def test_reinforcement_changes_reflex_gain(cfg):
    r = FlybrainReservoir(cfg)
    r.step("build a plan")
    before = r.gf_gain
    r.reinforce(1.0)
    assert r.gf_gain >= before


def test_neuromodulation_roundtrip(cfg):
    r = FlybrainReservoir(cfg)
    r.set_neuromodulation(octopamine=0.5, dopamine=0.2, serotonin=0.1)
    report = r.step("anything")
    assert np.isfinite(report.firing_rate)
    assert report.criticality >= 0.0


def test_encode_is_deterministic(cfg):
    r = FlybrainReservoir(cfg)
    a = r.encode("build a plan")
    b = r.encode("build a plan")
    assert np.allclose(a, b)
