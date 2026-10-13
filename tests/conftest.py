import pytest

from zoe.config import ZoeConfig


@pytest.fixture()
def cfg(tmp_path):
    """A fast, isolated config for tests."""
    return ZoeConfig(
        neuron_count=300,
        feature_dim=16,
        timesteps=25,
        eval_held_out=8,
        ledger_path=str(tmp_path / "ledger.jsonl"),
    )
