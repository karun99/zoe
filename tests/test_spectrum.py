from zoe.agents import AGENTS, OPPOSITE, blend, resolve_pair, route_scores


def test_nine_spectrum_agents():
    assert len(AGENTS) == 9
    assert set(AGENTS) == {
        "RED", "ORANGE", "YELLOW", "GREEN", "BLUE",
        "INDIGO", "VIOLET", "BLACK", "WHITE",
    }


def test_opposites_cancel():
    assert resolve_pair("RED", "VIOLET") is None
    assert resolve_pair("BLACK", "WHITE") is None
    for a, b in OPPOSITE:
        assert resolve_pair(a, b) is None


def test_same_stacks():
    assert resolve_pair("GREEN", "GREEN") == "GREEN"


def test_adjacent_synergize():
    assert resolve_pair("GREEN", "BLUE") == "GREEN"


def test_blend_three_way_white_integrates():
    assert blend(["GREEN", "BLUE", "WHITE"]) is not None


def test_routing_prefers_matching_agent():
    scores = route_scores("build and implement the module")
    assert scores["GREEN"] == max(scores.values())
    scores = route_scores("warn about the unsafe risk")
    assert scores["YELLOW"] == max(scores.values())
