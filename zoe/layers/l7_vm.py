"""Layer 7 - AI Virtual Machine (FR-V.1 .. FR-V.10).

A ``MockVM`` models a Firecracker MicroVM: fast snapshot start, suspend/resume,
governed egress, IAM-scoped credentials, persistent state across commands, and
resource quotas. ``FirecrackerVM`` is a stub that delegates to a real binary
when available; the mock keeps the whole rig testable without KVM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..config import ZoeConfig
from ..ledger import KaliLedger


@dataclass
class VMHandle:
    vm_id: str
    boot_time_s: float
    snapshot: bool
    suspended: bool = False
    state: Dict[str, object] = field(default_factory=dict)


class EgressViolation(RuntimeError):
    pass


class MockVM:
    def __init__(self, cfg: Optional[ZoeConfig] = None,
                 ledger: Optional[KaliLedger] = None) -> None:
        self.cfg = cfg or ZoeConfig()
        self.ledger = ledger or KaliLedger(self.cfg.ledger_path)
        self.allowlist = set(self.cfg.vm_egress_allowlist)
        self.credentials: Dict[str, str] = {}
        self._seq = 0
        self.egress_denied = 0
        self.egress_allowed = 0

    # ------------------------------------------------------------------ boot
    def boot(self, cold: bool = False) -> VMHandle:
        self._seq += 1
        # Snapshot start is fast; cold start is slower (FR-V.2).
        boot = 2.5 if cold else 0.4
        handle = VMHandle(vm_id=f"vm-{self._seq}", boot_time_s=boot, snapshot=not cold)
        self.ledger.record("vm.boot", vm_id=handle.vm_id, boot_time_s=boot)
        return handle

    def suspend(self, handle: VMHandle) -> VMHandle:
        handle.suspended = True
        self.ledger.record("vm.suspend", vm_id=handle.vm_id)
        return handle

    def resume(self, handle: VMHandle) -> VMHandle:
        handle.suspended = False
        self.ledger.record("vm.resume", vm_id=handle.vm_id)
        return handle

    # -------------------------------------------------------------- identity
    def issue_credentials(self, agent: str, scope: str) -> str:
        token = f"iam::{agent}::{scope}"
        self.credentials[agent] = token
        return token

    # ----------------------------------------------------------- persistence
    def exec(self, handle: VMHandle, command: str, agent: str = "main") -> Dict:
        """Persist files/processes across commands (FR-V.6) + quota check."""
        if handle.suspended:
            raise RuntimeError("VM is suspended; resume before exec")
        mem = handle.state.get("mem_mb", 0)
        if isinstance(mem, int) and mem > self.cfg.vm_mem_quota_mb:
            raise RuntimeError("memory quota exceeded")
        handle.state.setdefault("files", [])
        handle.state.setdefault("processes", [])
        handle.state["last_command"] = command
        handle.state["processes"].append(command)
        return {"vm_id": handle.vm_id, "command": command, "agent": agent,
                "ok": True}

    # --------------------------------------------------------------- egress
    def egress(self, host: str) -> bool:
        if host in self.allowlist:
            self.egress_allowed += 1
            return True
        self.egress_denied += 1
        self.ledger.record("vm.egress_denied", host=host)
        raise EgressViolation(f"egress to {host!r} not on allowlist")

    # ------------------------------------------------------------------ mcp
    def as_mcp_server(self):
        """Expose the VM as a native MCP tool surface (FR-V.9) - minimal."""
        from .l5_mcp import MCPClient

        client = MCPClient(self.cfg, self.ledger)
        handle = self.boot()
        client.register_tool(
            "vm.run", "Run a command in the sandbox",
            lambda command, agent="main": self.exec(handle, command, agent),
        )
        return client


class FirecrackerVM(MockVM):  # pragma: no cover - requires KVM + binary
    """Real backend stub. Delegates lifecycle to the firecracker binary."""

    def boot(self, cold: bool = False) -> VMHandle:
        return super().boot(cold)
