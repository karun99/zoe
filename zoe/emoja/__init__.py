"""Emoja — Zoe's consented, non-diagnostic reflection layer.

Emoja is a module of Zoe, not a second project. Zoe's reservoir/LoRA layers
evolve underneath; Emoja reflects on top. It is not therapy, not emotion
detection, and not a diagnostic tool.

Public API::

    from zoe.emoja import EmojaSession
    session = EmojaSession(consent=True)
    turn = session.reflect("I am tired but steady")
    print(turn.text)
"""

from .agents import (
    Bindu,
    Drishti,
    EmojaCard,
    EmojaTurn,
    Katha,
    Mudra,
    Rang,
    Setu,
    Suno,
)
from .session import EmojaCommand, EmojaSession
from .storage import CardStore

__all__ = [
    "Bindu", "CardStore", "Drishti", "EmojaCard", "EmojaCommand",
    "EmojaSession", "EmojaTurn", "Katha", "Mudra", "Rang", "Setu", "Suno",
]
