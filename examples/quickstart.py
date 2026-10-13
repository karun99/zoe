"""Quickstart: run a short interaction with Zoe.

    python examples/quickstart.py
"""

from zoe import ZoeRig
from zoe.config import ZoeConfig


def main() -> None:
    rig = ZoeRig(ZoeConfig.from_env())
    rig.companion.start()
    try:
        for text in [
            "build and implement a plan to fix the code",
            "warn me about the unsafe risk before we proceed",
            "help and explain this clearly, with compassion",
        ]:
            result = rig.run(text, novelty=0.5)
            print("\n".join(l for l in result.output_lines if l))
            print(f"  -> agent={result.agent} growth={result.growth_signal:.2f}\n")
    finally:
        rig.companion.stop()


if __name__ == "__main__":
    main()
