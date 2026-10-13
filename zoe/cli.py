"""Zoe command-line interface.

    python -m zoe run "build and implement a plan"
    python -m zoe train --generations 60
    python -m zoe report
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .config import ZoeConfig
from .rig import ZoeRig
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="zoe", description="Project Zoe companion rig")
    p.add_argument("--version", action="version", version=f"zoe {__version__}")
    p.add_argument("--mock", action="store_true", help="force mock LLM mode")
    sub = p.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run one 13-step interaction")
    run.add_argument("text", help="input text for Zoe")
    run.add_argument("--novelty", type=float, default=None)

    train = sub.add_parser("train", help="run the evolution loop")
    train.add_argument("--generations", type=int, default=60)

    sub.add_parser("report", help="run full training + 7-tier evaluation")
    sub.add_parser("demo", help="run a short scripted demonstration")
    return p


def cmd_run(rig: ZoeRig, args: argparse.Namespace) -> int:
    result = rig.run(args.text, novelty=args.novelty)
    print("\n".join(result.output_lines))
    print(f"\nagent={result.agent} growth={result.growth_signal:.3f} "
          f"mutated={result.mutation_permitted} frames={result.frames}")
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
          len(rig.ledger.entries()))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    cfg = ZoeConfig.from_env(mock_mode=args.mock or None) if args.mock else ZoeConfig.from_env()
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
