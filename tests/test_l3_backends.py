"""Layer 3 backend tests - no network, no model, no GPU.

The HTTP engines are exercised against a throwaway local server; the subprocess
engine against a two-line shell script. Everything runs in well under a second.
"""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import pytest

from zoe.backends import (
    BackendUnavailable,
    LlamaCliBackend,
    OllamaBackend,
    build_backend,
    resolve_backend,
)
from zoe.config import ZoeConfig
from zoe.layers.l3_llm import LlamaCppModel

# --------------------------------------------------------------------- helpers


class _StubHandler(BaseHTTPRequestHandler):
    """Tiny fake for Ollama and llama-server."""

    routes: dict = {}
    requests: list = []

    def log_message(self, *args):  # silence test output
        return

    def _reply(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        route = self.routes.get(("GET", self.path))
        if route is None:
            return self._reply(404, {"error": "not found"})
        self._reply(200, route)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        self.requests.append(json.loads(raw or b"{}"))
        route = self.routes.get(("POST", self.path))
        if route is None:
            return self._reply(404, {"error": "not found"})
        code, payload = route
        self._reply(code, payload)


@pytest.fixture()
def stub_server():
    _StubHandler.routes = {}
    _StubHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base, _StubHandler
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _closed_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _cfg(**kwargs) -> ZoeConfig:
    defaults = dict(
        neuron_count=64,
        feature_dim=8,
        timesteps=4,
        eval_held_out=4,
        ledger_path="/tmp/zoe-test-ledger.jsonl",
        llm_probe_timeout_s=0.25,
        llm_timeout_s=2.0,
        llm_retry_after_s=30.0,
    )
    defaults.update(kwargs)
    return ZoeConfig(**defaults)


def _feature(cfg: ZoeConfig) -> np.ndarray:
    return np.linspace(-1.0, 1.0, cfg.feature_dim)


# ------------------------------------------------------------------- selection


def test_default_is_mock_and_never_touches_network():
    model = LlamaCppModel(_cfg())
    gen = model.generate("system", feature=_feature(_cfg()), task="hello")
    assert gen.mock is True
    assert gen.backend == "mock"
    assert gen.degraded is False
    assert model.degraded is False
    assert len(gen.text.splitlines()) == 4


def test_unknown_backend_name_is_rejected():
    with pytest.raises(BackendUnavailable):
        build_backend("definitely-not-an-engine", _cfg())


def test_explicit_ollama_that_is_down_raises():
    cfg = _cfg(llm_backend="ollama",
               ollama_host=f"http://127.0.0.1:{_closed_port()}")
    with pytest.raises(BackendUnavailable):
        resolve_backend(cfg)


def test_auto_falls_through_to_mock_when_nothing_runs():
    cfg = _cfg(llm_backend="auto",
               ollama_host=f"http://127.0.0.1:{_closed_port()}",
               llama_server_url=f"http://127.0.0.1:{_closed_port()}",
               gguf_path="")
    model = LlamaCppModel(cfg)
    gen = model.generate("system", feature=_feature(cfg), task="hi")
    assert gen.mock is True
    assert model.degraded is True
    assert model.last_error


# ---------------------------------------------------------------------- ollama


def test_ollama_generates_and_cleans_output(stub_server):
    base, handler = stub_server
    handler.routes[("GET", "/api/tags")] = {
        "models": [{"name": "qwen2.5:0.5b"}]
    }
    handler.routes[("POST", "/api/chat")] = (200, {
        "model": "qwen2.5:0.5b",
        "message": {"role": "assistant",
                    "content": "Zoe: I hear you.\n\n- Steady.\nReady."},
        "eval_count": 9,
        "done_reason": "stop",
    })
    cfg = _cfg(llm_backend="ollama", ollama_host=base,
               ollama_model="qwen2.5:0.5b")
    model = LlamaCppModel(cfg)

    gen = model.generate("You are Zoe.", feature=_feature(cfg),
                         agent="GREEN", task="build a plan")

    assert gen.mock is False
    assert gen.backend == "ollama"
    assert gen.tokens == 9
    assert gen.text.splitlines() == ["I hear you.", "Steady.", "Ready."]
    assert model.backend_name == "ollama"
    assert model.degraded is False

    sent = handler.requests[-1]
    assert sent["model"] == "qwen2.5:0.5b"
    assert sent["stream"] is False
    assert "build a plan" in sent["messages"][0]["content"]
    assert "Agent: GREEN" in sent["messages"][0]["content"]
    assert sent["options"]["num_predict"] == cfg.llm_max_tokens


def test_ollama_http_error_falls_back_to_mock(stub_server):
    base, handler = stub_server
    handler.routes[("GET", "/api/tags")] = {"models": [{"name": "m"}]}
    handler.routes[("POST", "/api/chat")] = (500, {"error": "boom"})
    cfg = _cfg(llm_backend="ollama", ollama_host=base, ollama_model="m")
    model = LlamaCppModel(cfg)

    gen = model.generate("system", feature=_feature(cfg), task="hi")

    assert gen.mock is True
    assert model.fallback_events == 1
    assert "HTTP 500" in model.last_error


def test_ollama_backend_reports_installed_models(stub_server):
    base, handler = stub_server
    handler.routes[("GET", "/api/tags")] = {
        "models": [{"name": "qwen2.5:0.5b"}, {"name": "llama3.2:1b"}]
    }
    info = OllamaBackend(host=base, model="qwen2.5:0.5b").describe()
    assert info["available"] is True
    assert info["model_present"] is True
    assert "llama3.2:1b" in info["models"]


def test_ollama_missing_model_is_reported_not_hidden(stub_server):
    base, handler = stub_server
    handler.routes[("GET", "/api/tags")] = {"models": [{"name": "other:1b"}]}
    info = OllamaBackend(host=base, model="qwen2.5:0.5b").describe()
    assert info["available"] is True
    assert info["model_present"] is False


# --------------------------------------------------------------- llama-server


def test_llama_server_openai_compatible(stub_server):
    base, handler = stub_server
    handler.routes[("GET", "/health")] = {"status": "ok"}
    handler.routes[("POST", "/v1/chat/completions")] = (200, {
        "model": "zoe",
        "choices": [{"message": {"role": "assistant", "content": "Hello there."}}],
        "usage": {"completion_tokens": 3},
    })
    cfg = _cfg(llm_backend="llama-server", llama_server_url=base)
    gen = LlamaCppModel(cfg).generate("system", feature=_feature(cfg), task="hi")

    assert gen.backend == "llama-server"
    assert gen.text == "Hello there."
    assert gen.tokens == 3
    assert handler.requests[-1]["max_tokens"] == cfg.llm_max_tokens


# ------------------------------------------------------------------ llama-cli


def test_llama_cli_subprocess_backend(tmp_path):
    script = tmp_path / "fake-llama-cli"
    script.write_text("#!/bin/sh\necho 'Line one.'\necho 'Line two.'\n")
    script.chmod(0o755)
    model_file = tmp_path / "model.gguf"
    model_file.write_bytes(b"not a real model")

    cfg = _cfg(llm_backend="llama-cli", gguf_path=str(model_file),
               llama_cli_binary=str(script))
    gen = LlamaCppModel(cfg).generate("system", feature=_feature(cfg), task="hi")

    assert gen.mock is False
    assert gen.backend == "llama-cli"
    assert gen.text.splitlines() == ["Line one.", "Line two."]


def test_llama_cli_requires_a_model_file(tmp_path):
    script = tmp_path / "fake-llama-cli"
    script.write_text("#!/bin/sh\necho nope\n")
    script.chmod(0o755)
    backend = LlamaCliBackend(model_path=str(tmp_path / "missing.gguf"),
                              binary=str(script))
    assert backend.available() is False
    with pytest.raises(BackendUnavailable):
        backend.complete("hello")


# --------------------------------------------------------------- adapter steer


def test_steer_derives_temperature_from_adapter():
    cfg = _cfg(llm_temperature=0.7)
    model = LlamaCppModel(cfg)
    steer = model.steer(_feature(cfg))
    assert 1 <= steer["salience"] <= 4
    assert 0.0 <= steer["intensity"] <= 1.0
    assert 0.05 <= steer["temperature"] <= 1.5


def test_compose_prompt_enforces_short_reply_and_agent():
    cfg = _cfg(output_lines=5)
    model = LlamaCppModel(cfg)
    steer = model.steer(_feature(cfg))
    prompt = model.compose_prompt("You are Zoe.", "do the thing", "VIOLET", steer)
    assert "Agent: VIOLET." in prompt
    assert "at most 4 short lines" in prompt
    assert "Task: do the thing." in prompt


def test_evolved_adapter_changes_the_steering_signal():
    cfg = _cfg()
    model = LlamaCppModel(cfg)
    feature = _feature(cfg)
    before = model.steer(feature)
    model.set_adapter(model.adapter + 5.0)
    after = model.steer(feature)
    assert before != after


# ----------------------------------------------------------------------- doctor


def test_doctor_with_mock_is_ready(tmp_path):
    from zoe.doctor import FAIL, run_checks

    cfg = _cfg(ledger_path=str(tmp_path / "ledger.jsonl"))
    checks = run_checks(cfg, probe=False)
    assert all(c.status != FAIL for c in checks)
    assert any(c.name == "numpy" for c in checks)


def test_doctor_json_shape(tmp_path):
    from zoe.doctor import report_dict, run_checks

    cfg = _cfg(ledger_path=str(tmp_path / "ledger.jsonl"))
    payload = report_dict(run_checks(cfg, probe=False))
    assert payload["ok"] is True
    assert isinstance(payload["checks"], list)
    assert "termux" in payload


def test_doctor_no_probe_skips_backend_resolution(tmp_path):
    from zoe.doctor import WARN, run_checks

    cfg = _cfg(
        llm_backend="ollama",
        ollama_host=f"http://127.0.0.1:{_closed_port()}",
        ledger_path=str(tmp_path / "ledger.jsonl"),
    )
    checks = run_checks(cfg, probe=False)
    backend = next(c for c in checks if c.name == "backend")
    assert backend.status == WARN
    assert "not probed" in backend.detail


def test_backends_and_doctor_import_without_numpy():
    """`zoe doctor` must be able to diagnose a broken numpy, not need it."""
    import pathlib
    import subprocess
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    code = (
        "import sys; sys.modules['numpy'] = None; "
        "import zoe.backends, zoe.doctor, zoe.config, zoe.cli; "
        "print('ok')"
    )
    proc = subprocess.run([sys.executable, "-c", code], cwd=str(root),
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"
