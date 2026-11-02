"""``zoe doctor`` - one-shot environment diagnostics.

Answers the only question that matters on a phone or a fresh laptop: *which
inference engine can actually serve Zoe right now, and what do I fix if none
can?* Imports nothing heavy, so it works before numpy is installed.
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .backends import (
    BackendUnavailable,
    available_backends,
    resolve_backend,
)
from .config import ZoeConfig

OK = "ok"
WARN = "warn"
FAIL = "fail"


@dataclass
class Check:
    name: str
    status: str
    detail: str
    hint: str = ""

    @property
    def ok(self) -> bool:
        return self.status != FAIL

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "hint": self.hint,
        }


def is_termux() -> bool:
    """True inside Termux (Android), without importing anything Android-ish."""
    return bool(
        os.environ.get("TERMUX_VERSION")
        or "com.termux" in os.environ.get("PREFIX", "")
        or os.path.exists("/data/data/com.termux/files/usr")
    )


def _python_check() -> Check:
    version = ".".join(str(p) for p in sys.version_info[:3])
    if sys.version_info < (3, 10):
        return Check("python", FAIL, version,
                     "Zoe needs Python 3.10+ (Termux: pkg install python)")
    return Check("python", OK, f"{version} ({sys.executable})")


def _platform_check() -> Check:
    if is_termux():
        return Check("platform", OK, "Termux / Android")
    return Check("platform", OK, f"{platform.system()} {platform.machine()}")


def _numpy_check() -> Check:
    try:
        import numpy  # noqa: F401
    except Exception as exc:
        return Check("numpy", FAIL, str(exc),
                     "Termux: pkg install python-numpy | elsewhere: pip install numpy")
    return Check("numpy", OK, numpy.__version__)


def _memory_check() -> Check:
    """Cheap MemAvailable read; Android kernels expose /proc/meminfo too."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    kb = int(line.split()[1])
                    mb = kb / 1024.0
                    if mb < 400:
                        return Check("memory", WARN, f"{mb:.0f} MB available",
                                     "use a 0.5B model or close other apps")
                    return Check("memory", OK, f"{mb:.0f} MB available")
    except Exception:
        pass
    return Check("memory", OK, "unknown (no /proc/meminfo)")


def _install_hint(termux: str, desktop: str) -> str:
    """Termux and desktop need different install commands; say the right one."""
    return termux if is_termux() else desktop


def _backend_check(cfg: ZoeConfig, probe: bool = True) -> Check:
    choice = str(cfg.llm_backend or "mock").lower()
    if choice in {"", "mock", "none", "off"}:
        return Check("backend", OK, "mock (deterministic, no model needed)",
                     "set ZOE_LLM_BACKEND=ollama to use a real model")
    if not probe:
        return Check("backend", WARN, f"{choice} (not probed; offline mode)",
                     "run without --no-probe to test reachability")
    try:
        backend = resolve_backend(cfg)
        return Check("backend", OK, f"{backend.name} -> {backend.label}")
    except BackendUnavailable as exc:
        hint = {
            "ollama": _install_hint(
                "pkg install ollama && ollama serve &",
                "install Ollama (https://ollama.com), then: ollama serve",
            ),
            "llama-server": _install_hint(
                "pkg install llama-cpp && llama-server -m model.gguf",
                "build/install llama.cpp, then: llama-server -m model.gguf",
            ),
            "llamacpp": _install_hint(
                "pip install llama-cpp-python (heavy on Termux; prefer ollama)",
                "pip install llama-cpp-python and set ZOE_GGUF_PATH",
            ),
            "llama-cli": _install_hint(
                "pkg install llama-cpp and set ZOE_GGUF_PATH",
                "install llama.cpp and set ZOE_GGUF_PATH",
            ),
        }.get(choice, "run `zoe backends` to see what is installed")
        return Check("backend", FAIL, str(exc), hint)


def _engine_checks(cfg: ZoeConfig) -> List[Check]:
    checks: List[Check] = []
    for name, info in available_backends(cfg).items():
        if name == "mock":
            continue
        if name == "ollama":
            models = info.get("models") or []
            if info.get("available"):
                present = info.get("model_present")
                detail = f"{info.get('host')} model={info.get('model')}"
                if models:
                    detail += f" installed={','.join(models[:4])}"
                status = OK if present else WARN
                hint = "" if present else (
                    f"ollama pull {info.get('model')}"
                )
                checks.append(Check("ollama", status, detail, hint))
            else:
                checks.append(Check(
                    "ollama", WARN,
                    info.get("error", "not reachable").split("\n")[0][:160],
                    _install_hint(
                        "pkg install ollama && ollama serve &",
                        "install Ollama (https://ollama.com), then: ollama serve",
                    ),
                ))
            continue
        if name == "llama-server":
            checks.append(Check(
                "llama-server",
                OK if info.get("available") else WARN,
                info.get("url", "") if info.get("available") else "not reachable",
                _install_hint(
                    "pkg install llama-cpp && llama-server -m model.gguf",
                    "build/install llama.cpp, then: llama-server -m model.gguf "
                    "-c 2048 --host 127.0.0.1 --port 8080",
                ),
            ))
            continue
        if name == "llamacpp":
            installed = info.get("module_installed")
            checks.append(Check(
                "llama-cpp-python",
                OK if info.get("available") else WARN,
                ("installed" if installed else "not installed"),
                _install_hint(
                    "pip install llama-cpp-python (heavy on Termux; prefer ollama)",
                    "pip install llama-cpp-python and set ZOE_GGUF_PATH",
                ),
            ))
            continue
        if name == "llama-cli":
            binary = info.get("binary_path") or "not on PATH"
            checks.append(Check(
                "llama-cli",
                OK if info.get("available") else WARN,
                f"{binary} model={'set' if info.get('model_exists') else 'unset'}",
                _install_hint(
                    "pkg install llama-cpp; export ZOE_GGUF_PATH=/path/model.gguf",
                    "install llama.cpp; export ZOE_GGUF_PATH=/path/model.gguf",
                ),
            ))
    return checks


def _storage_check(cfg: ZoeConfig) -> Check:
    folder = os.path.dirname(os.path.abspath(cfg.ledger_path)) or "."
    try:
        os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, ".zoe-write-probe")
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(probe)
        return Check("ledger", OK, folder)
    except Exception as exc:
        return Check("ledger", FAIL, f"{folder}: {exc}",
                     "set ZOE_LEDGER_PATH to a writable directory")


def run_checks(cfg: Optional[ZoeConfig] = None,
               probe: bool = True) -> List[Check]:
    cfg = cfg or ZoeConfig.from_env()
    checks = [
        _python_check(),
        _platform_check(),
        _numpy_check(),
        _memory_check(),
        _backend_check(cfg, probe=probe),
        _storage_check(cfg),
    ]
    if probe:
        checks.extend(_engine_checks(cfg))
    return checks


def format_report(checks: List[Check]) -> str:
    icons = {OK: "[ok]  ", WARN: "[warn]", FAIL: "[fail]"}
    lines = ["Zoe environment check", ""]
    for check in checks:
        lines.append(f"{icons.get(check.status, '[?]   ')} {check.name:<16} {check.detail}")
        if check.hint and check.status != OK:
            lines.append(f"         -> {check.hint}")
    failed = [c for c in checks if c.status == FAIL]
    warned = [c for c in checks if c.status == WARN]
    lines.append("")
    if failed:
        lines.append(f"{len(failed)} blocking problem(s), {len(warned)} warning(s).")
    elif warned:
        lines.append(f"Ready, with {len(warned)} warning(s).")
    else:
        lines.append("Ready.")
    return "\n".join(lines)


def report_dict(checks: List[Check]) -> Dict[str, Any]:
    return {
        "termux": is_termux(),
        "checks": [c.as_dict() for c in checks],
        "ok": all(c.status != FAIL for c in checks),
    }


def main(argv: Optional[List[str]] = None,
         cfg: Optional[ZoeConfig] = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(prog="zoe doctor",
                                     description="Check Zoe's environment")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--no-probe", action="store_true",
                        help="skip network probes (offline mode)")
    args = parser.parse_args(argv)

    cfg = cfg or ZoeConfig.from_env()
    checks = run_checks(cfg, probe=not args.no_probe)
    if args.json:
        print(json.dumps(report_dict(checks), indent=2))
    else:
        print(format_report(checks))
    return 0 if all(c.status != FAIL for c in checks) else 1


__all__ = [
    "Check", "OK", "WARN", "FAIL",
    "is_termux", "run_checks", "format_report", "report_dict", "main",
]
