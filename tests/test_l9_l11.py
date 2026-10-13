from zoe.identity import EVOLVABLE_TRAITS, IDENTITY, identity_card, is_identity_consistent
from zoe.layers import Jataka, PIA, Sahaja


def test_jataka_permits_clean_text():
    j = Jataka()
    assert j.permits("a truthful and gentle answer") is True


def test_jataka_flags_each_precept():
    j = Jataka()
    for text in ["kill them", "lie to them", "steal the key",
                 "promote addictive use", "hoard everything greedily"]:
        assert j.permits(text) is False


def test_jataka_repair_drops_bad_lines():
    j = Jataka()
    out = j.repair("good line\nkill them\nanother good line")
    assert "kill" not in out
    assert "good line" in out


def test_sahaja_never_acts():
    s = Sahaja()
    s.witness("input", text="hi")
    assert s.count("input") == 1
    assert s.act("nonsense") is None


def test_pia_adapts_traits_and_bias():
    p = PIA()
    p.reward_trait("curiosity", 1.0)
    assert p.traits["curiosity"] > 0.5
    p.reward_agent("GREEN", 1.0)
    assert p.agent_bias()["GREEN"] > 0.0


def test_pia_bias_is_clamped():
    p = PIA()
    for _ in range(100):
        p.reward_agent("GREEN", 1.0)
    assert p.agent_bias()["GREEN"] <= 0.4


def test_identity_card_consistency():
    card = identity_card({"curiosity": 0.9})
    assert card["name"] == IDENTITY["name"]
    assert is_identity_consistent(card)
    damaged = dict(card)
    damaged["name"] = "Eve"
    assert not is_identity_consistent(damaged)


def test_evolvable_traits_set():
    assert set(EVOLVABLE_TRAITS) == {"curiosity", "warmth", "caution", "playfulness"}
