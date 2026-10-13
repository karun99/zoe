"""Layer 5 - Zoe MCP server (stdio, JSON-RPC).

Project Zoe ships a Model Context Protocol server so an editor or another
agent can drive the rig directly. It speaks newline-delimited JSON-RPC over
stdio and supports the ``initialize`` / ``tools/list`` / ``tools/call`` and
``resources/list`` / ``resources/read`` handshakes.

Tools
    zoe_run       run one 13-step interaction and return Zoe's answer
    zoe_report    run the evolution loop + 7-tier evaluation, return the summary
    zoe_layers    list the 11 layers and the mechanisms
    zoe_identity  return Zoe's persistent identity card

Run it with ``zoe-mcp`` or ``python -m zoe.mcp_server``.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional, TextIO

from .config import ZoeConfig
from .identity import identity_card
from .rig import ZoeRig
from .version import __version__

PROTOCOL_VERSION = "2024-11-05"

#: (id, name, role) for the eleven layers, mirroring the SRS scope table.
LAYERS: List[tuple] = [
    ("L1", "Flybrain Reservoir", "pattern detection (LIF; frozen)"),
    ("L2", "Prompt-as-Harness", "routing + 5-line output + growth signal"),
    ("L3", "llama.cpp + LoRA", "generation (frozen base, evolving adapter)"),
    ("L4", "Kali + Dunce", "temporal gates (WHEN) + failure patching"),
    ("L5", "MCP + Prompt API", "tools + versioned, cached prompts"),
    ("L6", "Virtual Avatar", "embodied expression + lip-sync"),
    ("L7", "AI Virtual Machine", "isolated execution (Firecracker-shaped)"),
    ("L8", "Companion Mode", "screen/browser awareness + pet states"),
    ("L9", "Sahaja", "silent witness (never acts)"),
    ("L10", "Jataka", "karmic guardrails (5 precepts)"),
    ("L11", "PIA", "silent adaptation"),
]

_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "zoe_run": {
        "description": (
            "Run one 13-step interaction through the full Zoe rig and return "
            "her answer, the routed agent, and the growth signal."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "input for Zoe"},
                "novelty": {
                    "type": "number",
                    "description": "optional novelty in [0,1] (auto if omitted)",
                },
            },
            "required": ["text"],
        },
    },
    "zoe_report": {
        "description": (
            "Run the evolution loop and the 7-tier evaluation harness, then "
            "return the pass/fail summary across all tiers."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "generations": {
                    "type": "integer",
                    "description": "evolution generations to run (default 200)",
                },
            },
        },
    },
    "zoe_layers": {
        "description": "List the eleven Zoe layers and their roles.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "zoe_identity": {
        "description": "Return Zoe's persistent identity card.",
        "inputSchema": {"type": "object", "properties": {}},
    },
}


class ZoeMCPServer:
    """A minimal, dependency-free MCP server over stdio."""

    def __init__(self, cfg: Optional[ZoeConfig] = None,
                 rig: Optional[ZoeRig] = None) -> None:
        self.cfg = cfg or ZoeConfig.from_env()
        self.rig = rig or ZoeRig(self.cfg)
        self.initialized = False

    # ------------------------------------------------------------- dispatch
    def list_tools(self) -> List[Dict[str, Any]]:
        return [{"name": name, **spec} for name, spec in _TOOL_SCHEMAS.items()]

    def list_resources(self) -> List[Dict[str, str]]:
        return [{
            "uri": "zoe://identity",
            "name": "Zoe identity card",
            "mimeType": "application/json",
        }]

    def _tool_result(self, text: str, is_error: bool = False) -> Dict[str, Any]:
        return {"content": [{"type": "text", "text": text}], "isError": is_error}

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}
        if name == "zoe_run":
            text = str(arguments.get("text", ""))
            novelty = arguments.get("novelty")
            result = self.rig.run(text, novelty=novelty)
            body = "\n".join(result.output_lines)
            body += (f"\n\nagent={result.agent} "
                     f"growth={result.growth_signal:.3f} "
                     f"mutated={result.mutation_permitted} "
                     f"frames={result.frames}")
            return self._tool_result(body)
        if name == "zoe_report":
            generations = int(arguments.get("generations", 200))
            summary = self.rig.report(train_generations=generations)["summary"]
            lines = [f"scored={summary['scored']} passed={summary['passed']} "
                     f"pass_rate={summary['pass_rate']} "
                     f"critical_five_ok={summary['critical_five_ok']}"]
            for tier, stats in summary["by_tier"].items():
                lines.append(f"{tier}: {stats['passed']}/{stats['scored']}")
            return self._tool_result("\n".join(lines))
        if name == "zoe_layers":
            lines = [f"{lid}  {nm:<22} -> {role}" for lid, nm, role in LAYERS]
            return self._tool_result("\n".join(lines))
        if name == "zoe_identity":
            return self._tool_result(json.dumps(identity_card(), indent=2))
        return self._tool_result(f"unknown tool: {name}", is_error=True)

    def read_resource(self, uri: str) -> Dict[str, Any]:
        if uri == "zoe://identity":
            return {"contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(identity_card(), indent=2),
            }]}
        raise KeyError(uri)

    def handle(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle one JSON-RPC message. Returns a response, or None for
        notifications."""
        method = request.get("method")
        req_id = request.get("id")

        if req_id is None and method and method.startswith("notifications/"):
            if method == "notifications/initialized":
                self.initialized = True
            return None

        def ok(result: Any) -> Dict[str, Any]:
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        def err(code: int, message: str) -> Dict[str, Any]:
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": code, "message": message}}

        if method == "initialize":
            params = request.get("params") or {}
            self.initialized = True
            return ok({
                "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "zoe", "version": __version__},
            })
        if method == "ping":
            return ok({})
        if method == "tools/list":
            return ok({"tools": self.list_tools()})
        if method == "tools/call":
            params = request.get("params") or {}
            try:
                return ok(self.call_tool(params.get("name", ""),
                                         params.get("arguments") or {}))
            except Exception as exc:  # pragma: no cover - defensive
                return err(-32603, f"tool error: {exc}")
        if method == "resources/list":
            return ok({"resources": self.list_resources()})
        if method == "resources/read":
            params = request.get("params") or {}
            try:
                return ok(self.read_resource(params.get("uri", "")))
            except KeyError:
                return err(-32602, f"unknown resource: {params.get('uri')}")
        return err(-32601, f"method not found: {method}")

    # --------------------------------------------------------------- stdio
    def serve(self, stdin: Optional[TextIO] = None,
              stdout: Optional[TextIO] = None) -> None:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                stdout.write(json.dumps({
                    "jsonrpc": "2.0", "id": None,
                    "error": {"code": -32700, "message": "parse error"},
                }) + "\n")
                stdout.flush()
                continue
            response = self.handle(request)
            if response is not None:
                stdout.write(json.dumps(response) + "\n")
                stdout.flush()


def main() -> int:
    ZoeMCPServer().serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
