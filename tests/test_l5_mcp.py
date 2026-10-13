from zoe.layers import MCPClient, PromptAPI
from zoe.ledger import KaliLedger


def test_mcp_register_and_call(cfg):
    c = MCPClient(cfg, KaliLedger(cfg.ledger_path))
    c.register_tool("clock", "now", lambda: 42)
    assert c.call("clock") == 42
    assert c.successes == 1


def test_mcp_unknown_tool_returns_none(cfg):
    c = MCPClient(cfg, KaliLedger(cfg.ledger_path))
    assert c.call("missing") is None
    assert c.successes == 0


def test_mcp_degrades_without_servers(cfg):
    c = MCPClient(cfg, KaliLedger(cfg.ledger_path))
    assert c.connect([]) is True
    assert c.list_tools() == []


def test_mcp_resource(cfg):
    c = MCPClient(cfg, KaliLedger(cfg.ledger_path))
    c.register_resource("zoe://x", "hello")
    assert c.read_resource("zoe://x") == "hello"


def test_prompt_cache_hits(cfg):
    p = PromptAPI(cfg, KaliLedger(cfg.ledger_path))
    a = p.render("system", name="Zoe")
    b = p.render("system", name="Zoe")
    assert a == b
    assert p.hits == 1 and p.misses == 1
    assert p.cache_hit_rate == 0.5


def test_prompt_fallback_on_unknown_key(cfg):
    p = PromptAPI(cfg, KaliLedger(cfg.ledger_path))
    out = p.render("does-not-exist", foo="bar")
    assert "bar" in out


def test_prompt_ab_choice(cfg):
    p = PromptAPI(cfg, KaliLedger(cfg.ledger_path))
    assert p.ab_choice("A", "B", 0.1) == "A"
    assert p.ab_choice("A", "B", 0.9) == "B"
