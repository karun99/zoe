"""Emoja's internal agents.

Boundary: ``SUNO`` is the only agent that sees the raw turn. Every other
agent receives the typed :class:`SunoReading` (words, cluster, categories,
distress, crisis flag). Aesthetic agents never receive raw text.

DRISHTI holds a real veto: if it vetoes aesthetics, SETU does not assemble
them. The veto is enforced in this module, not merely documented.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .lexicon import (
    content_words,
    detect_crisis,
    distress_score,
    emotion_surfaces,
    is_high_distress,
)

# ---------------------------------------------------------------------------
# SUNO - listener
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SunoReading:
    """Typed output of the sole perception agent."""

    words: str
    tokens: Tuple[str, ...]
    cluster: Tuple[str, ...]
    categories: Tuple[str, ...]
    distress: float
    crisis: bool
    high_distress: bool

    def mirror(self) -> str:
        return f'You said: "{self.words}"'


class Suno:
    """A 1-2 line mirror in the user's own phrasing. No interpretation."""

    def listen(self, text: str) -> SunoReading:
        words = " ".join(text.strip().split())
        cluster, categories = emotion_surfaces(words)
        crisis = detect_crisis(words)
        distress = 1.0 if crisis else distress_score(words)
        return SunoReading(
            words=words,
            tokens=content_words(words),
            cluster=cluster,
            categories=categories,
            distress=distress,
            crisis=crisis,
            high_distress=is_high_distress(distress),
        )


# ---------------------------------------------------------------------------
# DRISHTI - warden
# ---------------------------------------------------------------------------

RUNG_ORDER: Tuple[str, ...] = (
    "ground", "feel", "will", "compassion", "voice", "insight",
)
RUNG_INDEX: Dict[str, int] = {name: i for i, name in enumerate(RUNG_ORDER)}

#: Per-axis word sets. These are not emotion detection; they describe the
#: balance of the user's own language on three symbolic axes.
AXIS_WORDS: Dict[Tuple[str, str], Tuple[set, set]] = {
    ("ground", "aspire"): (
        {"here", "now", "steady", "safe", "rest", "breathe", "slow", "body",
         "today", "home", "floor", "floor", "ground", "calm"},
        {"want", "goal", "future", "grow", "build", "become", "hope", "plan",
         "learn", "try", "aspire", "next", "start", "change"},
    ),
    ("hold", "release"): (
        {"keep", "hold", "control", "stay", "contain", "protect", "remember",
         "must", "should", "guard", "carry"},
        {"release", "drop", "leave", "allow", "forgive", "stop", "enough",
         "let", "go", "open", "soften"},
    ),
    ("see", "feel"): (
        {"think", "know", "understand", "notice", "see", "reason", "logic",
         "because", "plan", "clear", "realize", "realise", "consider"},
        {"feel", "felt", "hurt", "sad", "angry", "scared", "anxious", "tired",
         "love", "happy", "lonely", "grief", "cry", "crying", "afraid"},
    ),
}


@dataclass(frozen=True)
class DrishtiVerdict:
    consent: bool
    crisis: bool
    distress: float
    max_rung: str
    veto_aesthetics: bool
    veto_reason: str
    shatkona: Dict[str, float]
    skews: Tuple[str, ...]

    @property
    def veto(self) -> bool:
        return self.veto_aesthetics

    @property
    def shatkona_flag(self) -> str:
        return "; ".join(self.skews) if self.skews else "balanced"


class Drishti:
    """Consent check, crisis flag, Shatkona scores, rung, and veto.

    The pre-check consumes SUNO's safety flags rather than raw text. That is
    deliberate: it keeps the trust boundary intact while still giving the
    warden the final say before any aesthetic agent runs.
    """

    def precheck(self, reading: SunoReading, consent: bool,
                 katha_opt_in: bool = False,
                 deep: bool = False) -> DrishtiVerdict:
        shatkona = self.score_shatkona(reading.tokens)
        skews = self.skews(shatkona)

        if not consent:
            return DrishtiVerdict(
                consent=False, crisis=reading.crisis,
                distress=reading.distress, max_rung="ground",
                veto_aesthetics=True, veto_reason="consent not stated",
                shatkona=shatkona, skews=skews,
            )
        if reading.crisis:
            return DrishtiVerdict(
                consent=True, crisis=True, distress=reading.distress,
                max_rung="ground", veto_aesthetics=True,
                veto_reason="crisis protocol", shatkona=shatkona, skews=skews,
            )
        if reading.high_distress:
            return DrishtiVerdict(
                consent=True, crisis=False, distress=reading.distress,
                max_rung="feel", veto_aesthetics=True,
                veto_reason="plain mode over acute pain",
                shatkona=shatkona, skews=skews,
            )

        if deep and reading.distress < 0.15:
            max_rung = "insight"
        elif presenting_complexity(reading):
            max_rung = "voice"
        else:
            max_rung = "will"
        if katha_opt_in and RUNG_INDEX[max_rung] < RUNG_INDEX["compassion"]:
            max_rung = "compassion"
        return DrishtiVerdict(
            consent=True, crisis=False, distress=reading.distress,
            max_rung=max_rung, veto_aesthetics=False, veto_reason="",
            shatkona=shatkona, skews=skews,
        )

    @staticmethod
    def score_shatkona(tokens: Sequence[str]) -> Dict[str, float]:
        token_set = set(tokens)
        scores: Dict[str, float] = {}
        for (left, right), (left_words, right_words) in AXIS_WORDS.items():
            lc = len(token_set & left_words)
            rc = len(token_set & right_words)
            total = lc + rc
            if total == 0:
                scores[left] = 0.5
                scores[right] = 0.5
            else:
                scores[left] = round(lc / total, 2)
                scores[right] = round(rc / total, 2)
        return scores

    @staticmethod
    def skews(scores: Dict[str, float], threshold: float = 0.4) -> Tuple[str, ...]:
        out: List[str] = []
        for left, right in AXIS_WORDS:
            diff = abs(scores[left] - scores[right])
            if diff <= threshold:
                continue
            high, low = (left, right) if scores[left] > scores[right] else (right, left)
            out.append(f"mostly {_gerund(high)}, little {_gerund(low)}")
        return tuple(out)


def _gerund(axis: str) -> str:
    return {
        "ground": "grounding", "aspire": "aspiring",
        "hold": "holding", "release": "releasing",
        "see": "seeing", "feel": "feeling",
    }.get(axis, axis)


def presenting_complexity(reading: SunoReading) -> bool:
    """A lighter signal for allowing the 'voice' rung.

    This is not a diagnosis. It simply notes that the turn contains more than
    one distinct emotion surface, which can support a slightly richer
    reflection without adding drama.
    """
    return len(reading.categories) >= 2


# ---------------------------------------------------------------------------
# MUDRA - glyph
# ---------------------------------------------------------------------------

_EMOJI: Dict[str, Tuple[str, ...]] = {
    "tired": ("🌙", "🫧", "🛏️", "🌿"),
    "anxious": ("🌪️", "🫨", "🪢", "🫧"),
    "sad": ("🌧️", "💧", "🫂", "🌱"),
    "angry": ("🔥", "⚡", "🪨", "🌋"),
    "lonely": ("🌑", "🕯️", "🫂", "🌌"),
    "overwhelmed": ("🌊", "🌀", "🫧", "🪨"),
    "calm": ("🌿", "🫧", "☀️", "🪷"),
    "hopeful": ("🌱", "🌅", "✨", "🕊️"),
    "grateful": ("🙏", "🌻", "✨", "🫶"),
    "happy": ("😊", "☀️", "🌈", "✨"),
    "confused": ("🌀", "🧩", "🌫️", "❓"),
    "ashamed": ("🫥", "🌫️", "🫂", "🕯️"),
    "neutral": ("🫧", "🌿", "🪨", "✨"),
}


@dataclass(frozen=True)
class MudraOutput:
    sequence: Tuple[str, ...]
    anchor: str
    rung_required: str = "feel"

    def render(self) -> str:
        return " ".join(self.sequence)


class Mudra:
    """A 3-5 emoji mini-narrative plus one anchor emoji."""

    def render(self, reading: SunoReading) -> MudraOutput:
        category = reading.categories[0] if reading.categories else "neutral"
        sequence = _EMOJI.get(category, _EMOJI["neutral"])[:4]
        anchor = sequence[1] if len(sequence) > 1 else sequence[0]
        return MudraOutput(sequence=tuple(sequence), anchor=anchor)


# ---------------------------------------------------------------------------
# RANG - colorist
# ---------------------------------------------------------------------------

_HUE: Dict[str, float] = {
    "tired": 250.0, "anxious": 90.0, "sad": 230.0, "angry": 25.0,
    "lonely": 270.0, "overwhelmed": 200.0, "calm": 150.0,
    "hopeful": 120.0, "grateful": 80.0, "happy": 60.0,
    "confused": 300.0, "ashamed": 330.0, "neutral": 210.0,
}

_ELEMENT: Dict[str, str] = {
    "tired": "water", "anxious": "wood", "sad": "water", "angry": "fire",
    "lonely": "metal", "overwhelmed": "water", "calm": "earth",
    "hopeful": "wood", "grateful": "earth", "happy": "fire",
    "confused": "metal", "ashamed": "water", "neutral": "earth",
}


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def oklch_to_hex(lightness: float, chroma: float, hue_deg: float) -> str:
    """Convert OKLCH to an sRGB hex token (clamped to gamut)."""
    h = math.radians(hue_deg)
    a = chroma * math.cos(h)
    b = chroma * math.sin(h)
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    channels = [
        max(0, min(255, round(_linear_to_srgb(max(0.0, min(1.0, x))) * 255)))
        for x in (r, g, bl)
    ]
    return "#" + "".join(f"{c:02x}" for c in channels)


def relative_luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    if len(value) == 8:
        value = value[:6]
    r, g, b = (int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (0.2126 * _srgb_to_linear(r)
            + 0.7152 * _srgb_to_linear(g)
            + 0.0722 * _srgb_to_linear(b))


def contrast_ratio(first: str, second: str) -> float:
    l1, l2 = relative_luminance(first), relative_luminance(second)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


@dataclass(frozen=True)
class RangOutput:
    palette: Tuple[str, ...]
    contrast: str
    element: str
    rung_required: str = "feel"

    def render(self) -> str:
        return " / ".join(self.palette)


class Rang:
    """3-5 hex tokens, blended in OKLCH internally, output as hex only."""

    def render(self, reading: SunoReading) -> RangOutput:
        category = reading.categories[0] if reading.categories else "neutral"
        hue = _HUE.get(category, 210.0)
        anchor = oklch_to_hex(0.44, 0.15, hue)
        accent_a = oklch_to_hex(0.68, 0.13, hue + 18.0)
        accent_b = oklch_to_hex(0.36, 0.12, hue - 28.0)
        neutral = oklch_to_hex(0.95, 0.02, 70.0)
        ratio = contrast_ratio(anchor, neutral)
        return RangOutput(
            palette=(anchor, accent_a, accent_b, neutral),
            contrast="PASS" if ratio >= 4.5 else "FLAG",
            element=_ELEMENT.get(category, "earth"),
        )


# ---------------------------------------------------------------------------
# BINDU - patternist
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BinduOutput:
    pattern: str
    intensity: float
    direction: str
    rung_required: str = "feel"

    def render(self) -> str:
        return f"{self.pattern} | intensity {self.intensity:.2f} | {self.direction}"


class Bindu:
    """Pattern movement in words; band width = time, saturation = intensity."""

    def render(self, reading: SunoReading, turn_index: int,
               previous_intensity: Optional[float] = None) -> BinduOutput:
        intensity = round(reading.distress, 2)
        if previous_intensity is None:
            direction = "steady"
        elif intensity > previous_intensity + 0.08:
            direction = "rising"
        elif intensity < previous_intensity - 0.08:
            direction = "fading"
        else:
            direction = "steady"

        width = "narrow" if turn_index <= 1 else "widening" if turn_index <= 4 else "wide"
        saturation = "low" if intensity < 0.4 else "medium" if intensity < 0.7 else "high"
        confidence = 1.0 - reading.distress
        alpha = "high" if confidence >= 0.7 else "medium" if confidence >= 0.4 else "low"
        pattern = (
            f"a {width} band, {saturation} saturation, "
            f"{alpha} confidence"
        )
        return BinduOutput(
            pattern=pattern,
            intensity=intensity,
            direction=direction,
        )


# ---------------------------------------------------------------------------
# KATHA - Jataka sage (one optional resilience beat)
# ---------------------------------------------------------------------------

_KATHA_BEATS: Dict[str, str] = {
    "tired": (
        "A Jataka story tells of a traveler who rested under a tree before "
        "continuing; rest was part of the road, not a detour. If you want, "
        "we can name one thing that would let you rest today."
    ),
    "anxious": (
        "In the Jataka tales, the Bodhisatta often waited for the right "
        "moment rather than forcing a crossing. If you want, we can look at "
        "what one small steady step would be."
    ),
    "sad": (
        "A Jataka tale tells of a Bodhisatta who grieved and then returned "
        "to the path. If you want, we can sit with one small kindness for "
        "today."
    ),
    "overwhelmed": (
        "A Jataka story tells of a Bodhisatta who kept returning to the "
        "shore until the raft was ready. If you want, we can look at one "
        "next step, no more."
    ),
    "default": (
        "A Jataka story tells of a Bodhisatta who kept returning to the "
        "shore until the raft was ready. If you want, we can look at one "
        "next step, no more."
    ),
}


@dataclass(frozen=True)
class KathaOutput:
    beat: str
    offered: bool = True
    rung_required: str = "feel"


class Katha:
    """One resilience beat from Jataka literature, offered never instructed."""

    def maybe_offer(self, reading: SunoReading, opt_in: bool) -> Optional[KathaOutput]:
        if reading.crisis:
            return None
        if not opt_in and reading.distress <= 0.5:
            return None
        category = reading.categories[0] if reading.categories else "default"
        return KathaOutput(beat=_KATHA_BEATS.get(category, _KATHA_BEATS["default"]))


# ---------------------------------------------------------------------------
# Card + SETU - synthesizer
# ---------------------------------------------------------------------------


@dataclass
class EmojaCard:
    emoja_id: str
    timestamp: str
    consent: bool
    words: str
    cluster: Tuple[str, ...]
    emoji: str
    anchor: str
    palette: str
    contrast: str
    pattern: str
    intensity: float
    direction: str
    shatkona: Dict[str, float]
    shatkona_flag: str
    kundalini_max: str
    integration: str
    jataka: str
    audit: str
    sentence: str
    aesthetics_suppressed: bool = False
    mode: str = "card"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["cluster"] = list(self.cluster)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmojaCard":
        payload = dict(data)
        payload["cluster"] = tuple(payload.get("cluster") or ())
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in payload.items() if k in known})

    def render(self) -> str:
        lines = [
            f"Emoja Card · {self.emoja_id}",
            f'words: "{self.words}"',
            f"cluster: {', '.join(self.cluster)}",
        ]
        if self.aesthetics_suppressed:
            lines.append("aesthetics: suppressed (plain mode over acute pain)")
        else:
            lines.append(f"emoji: {self.emoji}   anchor: {self.anchor}")
            lines.append(f"palette: {self.palette}   contrast: {self.contrast}")
            lines.append(
                f"pattern: {self.pattern} | intensity {self.intensity:.2f} "
                f"| {self.direction}"
            )
        lines.extend([
            "shatkona: "
            f"ground {self.shatkona.get('ground', 0):.2f} ↔ aspire "
            f"{self.shatkona.get('aspire', 0):.2f} | "
            f"hold {self.shatkona.get('hold', 0):.2f} ↔ release "
            f"{self.shatkona.get('release', 0):.2f} | "
            f"see {self.shatkona.get('see', 0):.2f} ↔ feel "
            f"{self.shatkona.get('feel', 0):.2f} → {self.shatkona_flag}",
            f"kundalini_max: {self.kundalini_max}   "
            f"integration: {self.integration}",
            f"jataka: {self.jataka}",
            f"audit: {self.audit}",
            f'sentence: "{self.sentence}"',
        ])
        return "\n".join(lines)


@dataclass
class EmojaTurn:
    text: str
    card: Optional[EmojaCard]
    sentence: str
    plain: bool
    crisis: bool
    consent: bool
    paused: bool
    distress: float
    max_rung: str
    max_agent_rung: str
    shatkona: Dict[str, float]
    skews: Tuple[str, ...]
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    audit: Optional[str] = None
    mas_text: str = ""

    @property
    def rung_ok(self) -> bool:
        return RUNG_INDEX[self.max_agent_rung] <= RUNG_INDEX[self.max_rung]


_DISCLOSURE = (
    "This reflects your own words as color and glyph — it isn't therapy or "
    "emotion detection. You can pause, correct, or delete anything. Emoja is "
    "the reflection layer of Zoe: Zoe's reservoir/LoRA layers evolve "
    "underneath, Emoja reflects safely on top."
)

_CRISIS_TEXT = (
    "I'm here with you; please reach a trusted person or local emergency "
    "service now, and we can stay in plain listening mode."
)


class Setu:
    """Assemble the card, one plain sentence, and the named skew."""

    disclosure = _DISCLOSURE

    def consent_prompt(self, reading: SunoReading) -> EmojaTurn:
        sentence = (
            "I can reflect only what you choose to share; say /consent or "
            "pass --consent when you are ready."
        )
        return EmojaTurn(
            text=(
                "Reflection is paused until consent is stated. "
                + sentence
            ),
            card=None, sentence=sentence, plain=True, crisis=False,
            consent=False, paused=False, distress=reading.distress,
            max_rung="ground", max_agent_rung="ground",
            shatkona=self._flat_shatkona(), skews=(),
        )

    def crisis(self, reading: SunoReading) -> EmojaTurn:
        return EmojaTurn(
            text=_CRISIS_TEXT,
            card=None, sentence=_CRISIS_TEXT, plain=True, crisis=True,
            consent=True, paused=False, distress=reading.distress,
            max_rung="ground", max_agent_rung="ground",
            shatkona=self._flat_shatkona(), skews=(),
        )

    def crisis_now(self) -> EmojaTurn:
        return EmojaTurn(
            text=_CRISIS_TEXT,
            card=None, sentence=_CRISIS_TEXT, plain=True, crisis=True,
            consent=True, paused=False, distress=1.0,
            max_rung="ground", max_agent_rung="ground",
            shatkona=self._flat_shatkona(), skews=(),
        )

    def paused_turn(self, reading: SunoReading) -> EmojaTurn:
        text = f'{reading.mirror()}\nPlain listening is on; no card is made.'
        return EmojaTurn(
            text=text, card=None, sentence=reading.mirror(), plain=True,
            crisis=False, consent=True, paused=True,
            distress=reading.distress, max_rung="ground",
            max_agent_rung="ground", shatkona=self._flat_shatkona(), skews=(),
        )

    def sentence(self, reading: SunoReading, verdict: DrishtiVerdict) -> str:
        if reading.crisis:
            return _CRISIS_TEXT
        cluster = ", ".join(reading.cluster) if reading.cluster else "your words"
        if reading.high_distress:
            return (
                f"This sounds heavy, and your words point to {cluster} while "
                "I stay with them plainly."
            )
        base = f"This reads as {cluster}"
        if verdict.skews:
            base += ", " + "; ".join(verdict.skews)
        return base + "."

    def assemble(
        self,
        reading: SunoReading,
        verdict: DrishtiVerdict,
        *,
        mudra: Optional[MudraOutput],
        rang: Optional[RangOutput],
        bindu: Optional[BinduOutput],
        katha: Optional[KathaOutput],
        audit: str,
        turn_index: int,
        mas: bool,
        integration: str = "pending",
    ) -> EmojaTurn:
        sentence = self.sentence(reading, verdict)

        if reading.crisis:
            return self.crisis(reading)

        # DRISHTI veto is enforced here: no aesthetic object is assembled.
        suppressed = verdict.veto_aesthetics
        card = EmojaCard(
            emoja_id=_emoja_id(reading, turn_index),
            timestamp=_timestamp(),
            consent=True,
            words=reading.words,
            cluster=reading.cluster,
            emoji="" if suppressed or mudra is None else " ".join(mudra.sequence),
            anchor="" if suppressed or mudra is None else mudra.anchor,
            palette="" if suppressed or rang is None else " / ".join(rang.palette),
            contrast="n/a" if suppressed or rang is None else rang.contrast,
            pattern="" if suppressed or bindu is None else bindu.pattern,
            intensity=0.0 if suppressed or bindu is None else bindu.intensity,
            direction="steady" if suppressed or bindu is None else bindu.direction,
            shatkona=dict(verdict.shatkona),
            shatkona_flag=verdict.shatkona_flag,
            kundalini_max=verdict.max_rung,
            integration=integration,
            jataka="offered" if katha is not None else "not-run",
            audit=audit,
            sentence=sentence,
            aesthetics_suppressed=suppressed,
            mode="plain" if suppressed else "card",
        )

        agent_outputs: Dict[str, Any] = {
            "SUNO": reading,
            "DRISHTI": verdict,
            "MUDRA": mudra,
            "RANG": rang,
            "BINDU": bindu,
            "KATHA": katha,
        }
        max_agent = "ground"
        for output in (mudra, rang, bindu, katha):
            if output is not None:
                required = getattr(output, "rung_required", "ground")
                if RUNG_INDEX[required] > RUNG_INDEX[max_agent]:
                    max_agent = required

        mas_text = self._mas(reading, verdict, mudra, rang, bindu, katha, card)
        return EmojaTurn(
            text=mas_text if mas else card.render(),
            card=card,
            sentence=sentence,
            plain=suppressed,
            crisis=False,
            consent=True,
            paused=False,
            distress=reading.distress,
            max_rung=verdict.max_rung,
            max_agent_rung=max_agent,
            shatkona=dict(verdict.shatkona),
            skews=verdict.skews,
            agent_outputs=agent_outputs,
            audit=audit,
            mas_text=mas_text,
        )

    def _mas(self, reading: SunoReading, verdict: DrishtiVerdict,
             mudra: Optional[MudraOutput], rang: Optional[RangOutput],
             bindu: Optional[BinduOutput], katha: Optional[KathaOutput],
             card: EmojaCard) -> str:
        def show(value: Any) -> str:
            if value is None:
                return "(vetoed)"
            if hasattr(value, "render"):
                return value.render()
            return str(value)

        lines = [
            "── /mas on ──",
            f"SUNO: {reading.mirror()}",
            (f"DRISHTI: consent={verdict.consent} distress={verdict.distress:.2f} "
             f"max_rung={verdict.max_rung} "
             f"veto={'yes' if verdict.veto_aesthetics else 'no'} "
             f"skew={verdict.shatkona_flag}"),
            f"MUDRA: {show(mudra)}",
            f"RANG: {show(rang)}",
            f"BINDU: {show(bindu)}",
            f"KATHA: {show(katha)}",
            "SETU:",
            card.render(),
        ]
        return "\n".join(lines)

    @staticmethod
    def _flat_shatkona() -> Dict[str, float]:
        return {
            "ground": 0.5, "aspire": 0.5,
            "hold": 0.5, "release": 0.5,
            "see": 0.5, "feel": 0.5,
        }


# ---------------------------------------------------------------------------
# Audit trace
# ---------------------------------------------------------------------------


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _emoja_id(reading: SunoReading, turn_index: int) -> str:
    seed = f"{reading.words}|{turn_index}|{reading.distress}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    return f"em-{digest}"


def make_audit(reading: SunoReading, agents: Sequence[str], output: str) -> Dict[str, Any]:
    stamp = _timestamp()
    payload = f"{reading.words}|{','.join(agents)}|{output}|{stamp}"
    trace_id = "emoja-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return {
        "trace_id": trace_id,
        "timestamp": stamp,
        "input": reading.words,
        "input_sha256": hashlib.sha256(reading.words.encode("utf-8")).hexdigest(),
        "agents": list(agents),
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
    }
