"""Spectrum agents (Appendix F) and conflict matrix (Appendix G)."""

from .spectrum import (
    ADJACENT,
    AGENTS,
    OPPOSITE,
    SpectrumAgent,
    blend,
    resolve_pair,
    route_scores,
)

__all__ = [
    "AGENTS",
    "OPPOSITE",
    "ADJACENT",
    "SpectrumAgent",
    "route_scores",
    "resolve_pair",
    "blend",
]
