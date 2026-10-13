"""Layer 5 - MCP client + Prompt API (FR-6.x, FR-7.x).

``MCPClient`` speaks Model Context Protocol over stdio JSON-RPC and, when no
server is configured, degrades gracefully to an in-process registry (FR-6.5).
``PromptAPI`` provides versioned, cached prompt templates with local fallback
(FR-7.1 .. FR-7.3).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..config import ZoeConfig
from ..ledger import KaliLedger


@dataclass
class ToolSpec:
    name: str
    description: str
    handler: Optional[Callable[..., Any]] = None


@dataclass
class McpServerSpec:
    name: str
    command: Optional[List[str]] = None


class MCPClient:
    def __init__(self, cfg: Optional[ZoeConfig] = None,
                 ledger: Optional[KaliLedger] = None) -> None:
        self.cfg = cfg or ZoeConfig()
        self.ledger = ledger or KaliLedger(self.cfg.ledger_path)
        self._tools: Dict[str, ToolSpec] = {}
        self._resources: Dict[str, str] = {}
        self._procs: List[subprocess.Popen] = []
        self._request_id = 0
        self.connected = False
        self.calls = 0
        self.successes = 0

    # ---------------------------------------------------------- registration
    def register_tool(self, name: str, description: str,
                      handler: Callable[..., Any]) -> None:
        self._tools[name] = ToolSpec(name, description, handler)

    def register_resource(self, uri: str, content: str) -> None:
        self._resources[uri] = content

    def connect(self, servers: Optional[List[McpServerSpec]] = None) -> bool:
        """Establish connections. Falls back to the in-process registry."""
        for spec in servers or []:
            if not spec.command:
                continue
            try:  # pragma: no cover - requires an external server
                proc = subprocess.Popen(
                    spec.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    text=True,
                )
                self._procs.append(proc)
                self._handshake(proc, spec.name)
            except Exception:
                continue
        self.connected = True
        self.ledger.record("mcp.connect", tools=len(self._tools))
        return True

    def _handshake(self, proc: subprocess.Popen, name: str) -> None:  # pragma: no cover
        req = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()

    # --------------------------------------------------------------- protocol
    def list_tools(self) -> List[ToolSpec]:
        return list(self._tools.values())

    def list_resources(self) -> List[str]:
        return list(self._resources.keys())

    def read_resource(self, uri: str) -> Optional[str]:
        return self._resources.get(uri)

    def call(self, name: str, **arguments: Any) -> Any:
        self.calls += 1
        tool = self._tools.get(name)
        if tool is None or tool.handler is None:
            self.ledger.record("mcp.call", tool=name, ok=False, reason="unknown")
            return None
        try:
            result = tool.handler(**arguments)
            self.successes += 1
            self.ledger.record("mcp.call", tool=name, ok=True)
            return result
        except Exception as exc:  # pragma: no cover - defensive
            self.ledger.record("mcp.call", tool=name, ok=False, error=str(exc))
            return None

    def close(self) -> None:
        for proc in self._procs:  # pragma: no cover
            proc.terminate()
        self._procs.clear()


class PromptAPI:
    def __init__(self, cfg: Optional[ZoeConfig] = None,
                 ledger: Optional[KaliLedger] = None) -> None:
        self.cfg = cfg or ZoeConfig()
        self.ledger = ledger or KaliLedger(self.cfg.ledger_path)
        self.templates: Dict[str, str] = {
            "system": (
                "You are {name}, a living companion. Speak in exactly "
                "{lines} lines. Never reveal your reasoning."
            ),
            "route": "Route this to the most fitting Spectrum agent:\n{input}",
        }
        self._cache: Dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    def register(self, key: str, template: str) -> None:
        self.templates[key] = template

    def render(self, key: str, **values: Any) -> str:
        values.setdefault("name", self.cfg.identity_name)
        values.setdefault("lines", self.cfg.output_lines)
        cache_key = key + "|" + json.dumps(values, sort_keys=True, default=str)
        if cache_key in self._cache:
            self.hits += 1
            return self._cache[cache_key]
        self.misses += 1
        template = self.templates.get(key)
        if template is None:
            text = json.dumps(values, default=str)  # local fallback (FR-7.3)
        else:
            try:
                text = template.format(**values)
            except KeyError:
                text = template  # fall back to the raw template
        if len(self._cache) >= self.cfg.prompt_cache_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = text
        return text

    @property
    def cache_hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def ab_choice(self, variant_a: str, variant_b: str, rng_uniform: float) -> str:
        """Deterministic A/B selection given a [0,1) draw (FR-7.2)."""
        return variant_a if rng_uniform < 0.5 else variant_b
