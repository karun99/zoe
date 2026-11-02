"""Zoe command-line interface.

    python -m zoe run "build and implement a plan"
    python -m zoe train --generations 60
    python -m zoe report
    python -m zoe doctor                 # what engine can serve Zoe here?
    python -m zoe backends               # list engines + availability
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING, List, Optional

from .config import ZoeConfig
from .version import __version__

if TYPE_CHECKING:  # pragma: no cover - typing only, keeps numpy optional
    from .rig import ZoeRig


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="zoe", description="Project Zoe companion rig")
    p.add_argument("--version", action="version", version=f"zoe {__version__}")
    p.add_argument("--mock", action="store_true", help="force mock LLM mode")
    p.add_argument("--backend", default=None,
                   help="inference engine: mock | ollama | llama-server | "
                        "llamacpp | llama-cli | auto")
    p.add_argument("--model", default=None,
                   help="model name for the active backend (e.g. qwen2.5:0.5b)")
    sub = p.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run one 13-step interaction")
    run.add_argument("text", help="input text for Zoe")
    run.add_argument("--novelty", type=float, default=None)
    run.add_argument("--json", action="store_true", help="emit a JSON result")

    train = sub.add_parser("train", help="run the evolution loop")
    train.add_argument("--generations", type=int, default=60)

    sub.add_parser("report", help="run full training + 7-tier evaluation")
    sub.add_parser("demo", help="run a short scripted demonstration")

    doctor = sub.add_parser("doctor", help="check the local environment")
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--no-probe", action="store_true",
                        help="skip network probes")

    backends = sub.add_parser("backends", help="list inference backends")
    backends.add_argument("--json", action="store_true")
    return p


def cmd_run(rig: ZoeRig, args: argparse.Namespace) -> int:
    result = rig.run(args.text, novelty=args.novelty)
    if args.json:
        print(json.dumps({
            "input": result.input,
            "agent": result.agent,
            "lines": result.output_lines,
            "growth_signal": result.growth_signal,
            "mutation_permitted": result.mutation_permitted,
            "frames": result.frames,
            "backend": result.backend,
            "mock": result.mock,
            "degraded": rig.model.degraded,
            "e2e_latency_s": result.e2e_latency_s,
        }, indent=2))
        return 0
    print("\n".join(result.output_lines))
    print(f"\nagent={result.agent} growth={result.growth_signal:.3f} "
          f"mutated={result.mutation_permitted} frames={result.frames} "
          f"backend={result.backend}")
    return 0


def cmd_train(rig: ZoeRig, args: argparse.Namespace) -> int:
    history = rig.train(args.generations)
    print("accuracy trend:")
    for i, acc in enumerate(history):
        if i % max(1, len(history) // 10) == 0 or i == len(history) - 1:
            bar = "#" * int(acc * 30)
            print(f"  gen {i:>4} {acc:.3f} {bar}")
    print(f"first={history[0]:.3f} last={history[-1]:.3f} "
          f"improved={history[-1] > history[0]}")
    return 0


def cmd_report(rig: ZoeRig, args: argparse.Namespace) -> int:
    report = rig.report()
    summary = report["summary"]
    print("=== Zoe 7-tier evaluation ===")
    print(f"scored={summary['scored']} passed={summary['passed']} "
          f"pass_rate={summary['pass_rate']} critical_five_ok={summary['critical_five_ok']}")
    for tier, stats in summary["by_tier"].items():
        print(f"  {tier}: {stats['passed']}/{stats['scored']}")
    print("\n=== failing metrics ===")
    failures = [r for r in report["evaluation"].results if not r.ok and r.value is not None]
    for r in failures:
        print(f"  {r.id} {r.name}: {r.value:.3f} (want {r.target})")
    print("\n=== premortem ===")
    for w in report["premortem"] or ["none detected"]:
        print(f"  - {w}")
    return 0


def cmd_demo(rig: ZoeRig, args: argparse.Namespace) -> int:
    print("Project Zoe - demo")
    rig.companion.start()
    try:
        for text in [
            "build and implement a plan to fix the code",
            "warn me about the unsafe risk before we proceed",
            "help and explain this clearly, with compassion",
            "tool: check the clock",
        ]:
            result = rig.run(text, novelty=0.5)
            print("  " + " | ".join(l for l in result.output_lines if l))
    finally:
        rig.companion.stop()
    print("companion states exercised; ledger entries:",
          len(rig.ledger.entries()), "backend:", rig.model.backend_name)
    return 0


def cmd_doctor(cfg: ZoeConfig, args: argparse.Namespace) -> int:
    from .doctor import main as doctor_main

    argv = ["--json"] if args.json else []
    if args.no_probe:
        argv.append("--no-probe")
    return doctor_main(argv, cfg=cfg)


def cmd_backends(cfg: ZoeConfig, args: argparse.Namespace) -> int:
    from .backends import available_backends

    report = available_backends(cfg)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"configured: {cfg.llm_backend}")
    for name, info in report.items():
        mark = "ready" if info.get("available") else "  -  "
        print(f"  [{mark}] {name:<13} {info.get('label', '')}")
        for key in ("host", "url", "model", "model_path", "binary_path", "error"):
            value = info.get(key)
            if value:
                print(f"          {key}: {value}")
    return 0


def _config_from_args(args: argparse.Namespace) -> ZoeConfig:
    overrides = {}
    if args.mock:
        overrides["mock_mode"] = True
    if args.backend:
        overrides["llm_backend"] = args.backend
    if args.model:
        model = args.model
        overrides["ollama_model"] = model
        overrides["llama_server_model"] = model
    return ZoeConfig.from_env(**overrides)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    cfg = _config_from_args(args)
    if args.command == "doctor":
        return cmd_doctor(cfg, args)
    if args.command == "backends":
        return cmd_backends(cfg, args)

    # Imported here, not at module scope: `zoe doctor` and `zoe backends` must
    # run on a machine where numpy is missing or broken (that is the point).
    from .rig import ZoeRig

    rig = ZoeRig(cfg)
    dispatch = {
        "run": cmd_run,
        "train": cmd_train,
        "report": cmd_report,
        "demo": cmd_demo,
    }
    return dispatch[args.command](rig, args)


if __name__ == "__main__":
    sys.exit(main())
