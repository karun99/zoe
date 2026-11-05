"""Command-line surface for Emoja.

    zoe emoja "I am tired but steady"      # one reflection
    zoe emoja                              # interactive session
    zoe emoja --json "..."                 # machine-readable card
    zoe-emoja                              # same as `zoe emoja`

The first-turn disclosure is printed once, then never again in the session.
Invoking the command is treated as consent for the words in that command; use
``--no-consent`` to see the consent prompt instead.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .agents import EmojaTurn, Setu
from .session import EmojaCommand, EmojaSession


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="zoe emoja",
        description="Emoja — reflect your own words as an emoji sequence, "
                    "a hex palette, a blended pattern, and one plain sentence.",
    )
    p.add_argument("text", nargs="?", help="one turn of text (omit for a REPL)")
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.add_argument("--mas", action="store_true", help="show all agent outputs")
    p.add_argument("--no-consent", action="store_true",
                   help="do not assume consent; show the consent prompt")
    p.add_argument("--katha", action="store_true",
                   help="opt in to one Jataka resilience beat")
    p.add_argument("--deep", action="store_true",
                   help="allow the insight rung when distress is low")
    p.add_argument("--store", default=None,
                   help="opt-in JSONL card store path (default: memory only)")
    p.add_argument("--trace", default=None,
                   help="opt-in audit trace JSONL path")
    p.add_argument("--no-disclosure", action="store_true",
                   help="suppress the first-turn disclosure")
    return p


def _session(args: argparse.Namespace) -> EmojaSession:
    return EmojaSession(
        consent=not args.no_consent,
        mas=args.mas,
        katha_opt_in=args.katha,
        store=args.store,
        trace_path=args.trace,
        deep=args.deep,
    )


def _print_turn(turn: EmojaTurn, as_json: bool) -> None:
    if as_json:
        payload = {
            "text": turn.text,
            "sentence": turn.sentence,
            "plain": turn.plain,
            "crisis": turn.crisis,
            "consent": turn.consent,
            "paused": turn.paused,
            "distress": turn.distress,
            "max_rung": turn.max_rung,
            "max_agent_rung": turn.max_agent_rung,
            "rung_ok": turn.rung_ok,
            "shatkona": turn.shatkona,
            "skews": list(turn.skews),
            "audit": turn.audit,
            "card": turn.card.to_dict() if turn.card else None,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    print(turn.text)


def _disclosure(as_json: bool, suppressed: bool) -> None:
    if suppressed:
        return
    if as_json:
        print(Setu.disclosure, file=sys.stderr)
    else:
        print(Setu.disclosure)
        print()


def cmd_one(args: argparse.Namespace) -> int:
    session = _session(args)
    _disclosure(args.json, args.no_disclosure)
    turn = session.reflect(args.text or "")
    session.close()
    _print_turn(turn, args.json)
    return 0


def cmd_repl(args: argparse.Namespace) -> int:
    session = _session(args)
    _disclosure(False, args.no_disclosure)
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            if line.lower() in {"/quit", "/exit"}:
                break
            result = session.handle(line)
            if isinstance(result, EmojaCommand):
                print(result.text)
            else:
                _print_turn(result, False)
    except KeyboardInterrupt:
        print()
    finally:
        print(session.close())
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.text is not None:
        return cmd_one(args)
    return cmd_repl(args)


def run(args: argparse.Namespace) -> int:
    """Entry point for the ``zoe emoja`` subcommand."""
    if args.text is not None:
        return cmd_one(args)
    return cmd_repl(args)


if __name__ == "__main__":
    raise SystemExit(main())
