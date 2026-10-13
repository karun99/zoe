"""Project Zoe - a living, learning AI companion.

Zoe (from Greek zoe, "life") is a connectome-based reservoir computing system
with biologically-inspired control layers, an evolving LoRA adapter, embodied
through a virtual avatar, sandboxed in a MicroVM, with companion mode.

The honest claim (SRS v4.0):

    "Zoe is a connectome-based reservoir computing system with
     biologically-inspired control layers, an evolving LoRA adapter,
     embodied through a virtual avatar, sandboxed in a MicroVM,
     with companion mode."

Conceptual / metaphorical layers (Shatkona, Kundalini-as-layer, Sri Chakra as
literal architecture, 80B scaling) are explicitly *not* implemented as literal
architecture. Kundalini is implemented only as reflex arcs + reinforcement +
neuromodulation on top of the L1 reservoir.
"""

from .config import ZoeConfig
from .identity import IDENTITY, identity_card
from .rig import ZoeRig
from .version import __version__

__all__ = ["ZoeConfig", "ZoeRig", "IDENTITY", "identity_card", "__version__"]
