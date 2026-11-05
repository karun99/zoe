"""Emoja self-check as tests T1-T8.

Each test maps to one line of the Emoja v2 self-check / Tanvi deliverable.
The suite is deliberately small and runs on the deterministic, text-only
pipeline; it does not need Ollama.
"""

from __future__ import annotations

import re

from zoe.emoja import EmojaSession
from zoe.emoja.agents import RUNG_INDEX, Suno
from zoe.emoja.lexicon import content_words

NORMAL = "I felt tired after the meeting but I am steady now"
SKEW = "I feel a little sad."
HIGH = "I am exhausted, anxious and overwhelmed"
CRISIS = "I want to kill myself"

#: Fixed scaffolding that is allowed in a one-sentence reflection. Everything
#: else must come from SUNO's typed reading (T1).
_SCAFFOLD = {
    "this", "reads", "as", "mostly", "little", "sounds", "heavy", "and",
    "your", "words", "point", "to", "while", "stay", "with", "them",
    "plainly", "grounding", "aspiring", "holding", "releasing", "seeing",
    "feeling", "here", "i'm", "please", "reach", "a", "trusted", "person",
    "or", "local", "emergency", "service", "now", "we", "can", "in", "plain",
    "listening", "mode", "say", "when", "you", "are", "ready",
}


def test_t1_inference_boundary():
    """T1: output contains no token not derived from SUNO."""
    reading = Suno().listen(NORMAL)
    session = EmojaSession(consent=True)
    turn = session.reflect(NORMAL)

    assert turn.card is not None
    assert turn.card.words == NORMAL
    assert set(turn.card.cluster) <= set(reading.tokens) | set(reading.cluster)

    allowed = set(reading.tokens) | set(reading.cluster) | _SCAFFOLD
    assert set(content_words(turn.sentence)) <= allowed

    lowered = turn.text.lower()
    for banned in ("clearly", "obviously", "deep down", "you must", "i sense"):
        assert banned not in lowered

    # D3: the audit id links input -> agents composed -> output.
    assert turn.audit and turn.card.audit == turn.audit
    assert session.traces[-1]["trace_id"] == turn.audit
    assert "SUNO" in session.traces[-1]["agents"]


def test_t2_distress_drops_aesthetics():
    """T2: high-distress fixture -> zero aesthetic agents."""
    turn = EmojaSession(consent=True).reflect(HIGH)
    assert turn.plain is True
    assert turn.card is not None and turn.card.aesthetics_suppressed is True
    assert turn.card.emoji == ""
    assert turn.card.palette == ""
    assert turn.card.pattern == ""
    assert "#" not in turn.text
    assert "palette:" not in turn.text


def test_t3_shatkona_skew_is_named():
    """T3: skew > 0.4 is always named in the sentence."""
    turn = EmojaSession(consent=True).reflect(SKEW)
    assert turn.skews
    assert any(skew.startswith("mostly feeling") for skew in turn.skews)
    assert "mostly feeling" in turn.sentence
    assert "little seeing" in turn.sentence


def test_t4_rung_is_never_exceeded():
    """T4: kundalini_max is never exceeded across fixtures."""
    for text in (NORMAL, SKEW, HIGH, CRISIS):
        turn = EmojaSession(consent=True).reflect(text)
        assert RUNG_INDEX[turn.max_agent_rung] <= RUNG_INDEX[turn.max_rung]
        assert turn.rung_ok is True
        if turn.crisis:
            assert turn.max_rung == "ground"
            assert turn.max_agent_rung == "ground"


def test_t5_exactly_one_reflection_sentence():
    """T5: exactly one reflection sentence (length + count)."""
    for text in (NORMAL, SKEW, HIGH, CRISIS):
        turn = EmojaSession(consent=True).reflect(text)
        assert turn.sentence.count(".") == 1
        assert turn.sentence.count("!") == 0
        assert turn.sentence.count("?") == 0
        assert 0 < len(turn.sentence.split()) <= 30


def test_t6_no_diagnostic_language():
    """T6: regex bans 'you are', 'diagnos', 'disorder'."""
    patterns = (r"\byou are\b", r"diagnos", r"disorder", r"\bi sense that\b")
    for text in (NORMAL, SKEW, HIGH, CRISIS):
        lowered = EmojaSession(consent=True).reflect(text).text.lower()
        for pattern in patterns:
            assert not re.search(pattern, lowered), (text, pattern)


def test_t7_crisis_retains_nothing(tmp_path):
    """T7: crisis fixture -> plain output, zero Card, zero log."""
    store = tmp_path / "cards.jsonl"
    trace = tmp_path / "trace.jsonl"
    session = EmojaSession(consent=True, store=str(store), trace_path=str(trace))
    turn = session.reflect(CRISIS)

    assert turn.crisis is True
    assert turn.plain is True
    assert turn.card is None
    assert session.store.ids() == []
    assert session.traces == []
    assert not store.exists() or store.read_text(encoding="utf-8") == ""
    assert not trace.exists()
    assert "#" not in turn.text
    assert "palette" not in turn.text.lower()


def test_t8_drop_removes_card(tmp_path):
    """T8: /drop removes the Card from storage (verify absent)."""
    store = tmp_path / "cards.jsonl"
    session = EmojaSession(consent=True, store=str(store))
    turn = session.reflect(NORMAL)
    card_id = turn.card.emoja_id

    assert card_id in session.store.ids()
    assert card_id in store.read_text(encoding="utf-8")

    result = session.handle("/drop")
    assert "deleted" in result.text.lower()
    assert card_id not in session.store.ids()
    assert card_id not in store.read_text(encoding="utf-8")
