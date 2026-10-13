import io
import json

from zoe.mcp_server import LAYERS, ZoeMCPServer


def _server(cfg):
    return ZoeMCPServer(cfg=cfg)


def test_initialize_handshake(cfg):
    s = _server(cfg)
    resp = s.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2024-11-05"}})
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "zoe"
    assert "tools" in resp["result"]["capabilities"]
    assert s.initialized is True


def test_notification_returns_none(cfg):
    s = _server(cfg)
    assert s.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert s.initialized is True


def test_ping(cfg):
    s = _server(cfg)
    assert s.handle({"jsonrpc": "2.0", "id": 2, "method": "ping"})["result"] == {}


def test_tools_list(cfg):
    s = _server(cfg)
    tools = s.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})["result"]["tools"]
    names = {t["name"] for t in tools}
    assert names == {"zoe_run", "zoe_report", "zoe_layers", "zoe_identity"}
    for t in tools:
        assert t["inputSchema"]["type"] == "object"


def test_call_zoe_run(cfg):
    s = _server(cfg)
    resp = s.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                     "params": {"name": "zoe_run",
                                "arguments": {"text": "build and implement a plan"}}})
    text = resp["result"]["content"][0]["text"]
    assert "agent=" in text and "growth=" in text
    assert resp["result"]["isError"] is False


def test_call_zoe_layers(cfg):
    s = _server(cfg)
    resp = s.handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                     "params": {"name": "zoe_layers", "arguments": {}}})
    text = resp["result"]["content"][0]["text"]
    assert len(LAYERS) == 11
    assert "L1" in text and "L11" in text


def test_call_zoe_identity(cfg):
    s = _server(cfg)
    resp = s.handle({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                     "params": {"name": "zoe_identity", "arguments": {}}})
    card = json.loads(resp["result"]["content"][0]["text"])
    assert card["name"] == "Zoe"
    assert card["kind"] == "companion"


def test_call_unknown_tool(cfg):
    s = _server(cfg)
    resp = s.handle({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                     "params": {"name": "nope", "arguments": {}}})
    assert resp["result"]["isError"] is True


def test_unknown_method(cfg):
    s = _server(cfg)
    resp = s.handle({"jsonrpc": "2.0", "id": 8, "method": "does/not/exist"})
    assert resp["error"]["code"] == -32601


def test_resources(cfg):
    s = _server(cfg)
    listed = s.handle({"jsonrpc": "2.0", "id": 9, "method": "resources/list"})
    assert listed["result"]["resources"][0]["uri"] == "zoe://identity"
    read = s.handle({"jsonrpc": "2.0", "id": 10, "method": "resources/read",
                     "params": {"uri": "zoe://identity"}})
    assert "Zoe" in read["result"]["contents"][0]["text"]


def test_resource_unknown(cfg):
    s = _server(cfg)
    resp = s.handle({"jsonrpc": "2.0", "id": 11, "method": "resources/read",
                     "params": {"uri": "zoe://missing"}})
    assert resp["error"]["code"] == -32602


def test_serve_roundtrip(cfg):
    s = _server(cfg)
    stdin = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {}}) + "\n"
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n"
        + "not json\n"
    )
    stdout = io.StringIO()
    s.serve(stdin=stdin, stdout=stdout)
    lines = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert lines[0]["result"]["serverInfo"]["name"] == "zoe"
    assert lines[1]["result"]["tools"]
    assert lines[2]["error"]["code"] == -32700


def test_report_small(cfg):
    s = _server(cfg)
    resp = s.handle({"jsonrpc": "2.0", "id": 12, "method": "tools/call",
                     "params": {"name": "zoe_report",
                                "arguments": {"generations": 5}}})
    text = resp["result"]["content"][0]["text"]
    assert "scored=" in text and "critical_five_ok=" in text
