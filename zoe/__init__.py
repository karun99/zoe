"""Project Zoe - a living, learning AI companion.

Zoe (from Greek zoe, "life") is a connectome-based reservoir computing system
with biologically-inspired control layers, an evolving LoRA adapter, embodied
through a virtual avatar, sandboxed in a MicroVM, with companion mode. Emoja is
its consented, non-diagnostic reflection layer: Zoe's reservoir/LoRA layers
evolve underneath, Emoja reflects safely on top.

The honest claim (SRS v4.0):

    "Zoe is a connectome-based reservoir computing system with
     biologically-inspired control layers, an evolving LoRA adapter,
     embodied through a virtual avatar, sandboxed in a MicroVM,
     with companion mode."

Conceptual / metaphorical layers (Shatkona, Kundalini-as-layer, Sri Chakra as
literal architecture, 80B scaling) are explicitly *not* implemented as literal
architecture. Kundalini is implemented only as reflex arcs + reinforcement +
neuromodulation on top of the L1 reservoir.

``ZoeRig`` is resolved lazily so that lightweight tools (``zoe doctor``,
``zoe backends``) still run on a machine where NumPy is missing or broken.
"""

from .config import ZoeConfig
from .emoja import EmojaSession
from .identity import IDENTITY, identity_card
from .version import __version__

__all__ = ["ZoeConfig", "ZoeRig", "IDENTITY", "identity_card", "EmojaSession",
           "__version__"]


def __getattr__(name: str):
    """PEP 562 lazy attribute - keeps ``import zoe`` free of NumPy."""
    if name == "ZoeRig":
        from .rig import ZoeRig

        globals()["ZoeRig"] = ZoeRig
        return ZoeRig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
