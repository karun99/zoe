"""Evolution: grow the LoRA adapter through the Kali/Dunce loop.

    python examples/evolve.py
"""

from zoe import ZoeRig
from zoe.config import ZoeConfig


def main() -> None:
    rig = ZoeRig(ZoeConfig.from_env())
    history = rig.train(generations=200)
    print(f"generations mutated : {rig.model.generation}")
    print(f"dunce patches       : {len(rig.dunce.patterns)}")
    print(f"accuracy first/last : {history[0]:.3f} -> {history[-1]:.3f}")
    for i in range(0, len(history), max(1, len(history) // 12)):
        acc = history[i]
        print(f"  gen {i:>4}  {acc:.3f}  {'#' * int(acc * 40)}")


if __name__ == "__main__":
    main()
