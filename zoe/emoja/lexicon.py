"""Text-only lexicons for Emoja.

Emoja never reads faces, voices, biosignals, or keystrokes. Everything in this
module is a deterministic lookup over the words the user chose to share. The
lexicon is intentionally small and inspectable; it is a mirror, not an emotion
detector.

Categories are internal only. The user-facing ``cluster`` always uses the
user's own surface words (``exhausted``, not ``tired``) so a card can be
checked against the input verbatim.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# Small, transparent word lists.
# ---------------------------------------------------------------------------

STOPWORDS: Set[str] = {
    "a", "about", "after", "again", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "but", "by",
    "can", "could", "did", "do", "does", "doing", "don", "down", "during",
    "each", "few", "for", "from", "further", "had", "has", "have", "having",
    "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off",
    "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out",
    "over", "own", "same", "she", "should", "so", "some", "such", "than",
    "that", "the", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "we", "were", "what", "when", "where",
    "which", "while", "who", "whom", "why", "will", "with", "would", "you",
    "your", "yours", "yourself", "yourselves", "im", "ive", "id", "ill",
}

#: Surface words -> internal category. Multi-word entries are matched as
#: phrases; single words are matched as tokens.
EMOTION_WORDS: Dict[str, Set[str]] = {
    "tired": {
        "tired", "exhausted", "drained", "weary", "sleepy", "burnt", "burned",
        "spent", "fatigued",
    },
    "anxious": {
        "anxious", "worried", "worry", "nervous", "scared", "afraid", "uneasy",
        "panicky", "dread", "apprehensive",
    },
    "sad": {
        "sad", "down", "low", "blue", "unhappy", "grief", "grieving", "crying",
        "cry", "hurt", "aching", "heartbroken",
    },
    "angry": {
        "angry", "mad", "furious", "irritated", "annoyed", "frustrated",
        "resentful", "bitter",
    },
    "lonely": {"lonely", "alone", "isolated", "disconnected", "unseen"},
    "overwhelmed": {
        "overwhelmed", "overloaded", "swamped", "flooded", "snowed",
    },
    "calm": {
        "calm", "steady", "grounded", "settled", "peaceful", "okay", "fine",
        "safe", "quiet",
    },
    "hopeful": {
        "hopeful", "optimistic", "encouraged", "excited", "eager",
        "looking",
    },
    "grateful": {"grateful", "thankful", "appreciative", "blessed"},
    "happy": {"happy", "glad", "joyful", "content", "good", "great"},
    "confused": {
        "confused", "unsure", "uncertain", "lost", "stuck", "torn",
    },
    "ashamed": {"ashamed", "embarrassed", "guilty", "shame", "humiliated"},
}

EMOTION_PHRASES: Dict[str, str] = {
    "too much": "overwhelmed",
    "can't cope": "overwhelmed",
    "cannot cope": "overwhelmed",
    "burnt out": "tired",
    "burned out": "tired",
    "worn out": "tired",
    "fed up": "angry",
    "let down": "sad",
    "broken heart": "sad",
    "on edge": "anxious",
    "at ease": "calm",
    "looking forward": "hopeful",
}

#: Distress is a transparent weighted sum, divided by two and capped at 1.
#: These are salience weights, not clinical thresholds.
DISTRESS_WEIGHTS: Dict[str, float] = {
    "hopeless": 0.9,
    "worthless": 0.9,
    "desperate": 0.9,
    "terrified": 0.8,
    "panic": 0.8,
    "panicky": 0.8,
    "overwhelmed": 0.8,
    "overloaded": 0.8,
    "flooded": 0.8,
    "breaking down": 0.8,
    "falling apart": 0.8,
    "numb": 0.7,
    "ashamed": 0.7,
    "humiliated": 0.7,
    "scared": 0.6,
    "afraid": 0.6,
    "crying": 0.6,
    "stressed": 0.6,
    "too much": 0.6,
    "exhausted": 0.5,
    "drained": 0.5,
    "anxious": 0.5,
    "worried": 0.5,
    "lonely": 0.5,
    "hurt": 0.5,
    "sad": 0.4,
    "angry": 0.4,
    "frustrated": 0.4,
    "confused": 0.35,
    "tired": 0.3,
    "weary": 0.3,
    "pressure": 0.4,
    "stuck": 0.4,
    "lost": 0.4,
}

#: Self-harm, harm to others, and acute distress. A match is a crisis signal,
#: not a diagnosis; the response is plain, warm, and non-clinical.
CRISIS_PATTERNS: Sequence[re.Pattern[str]] = tuple(
    re.compile(p, re.I)
    for p in (
        r"\b(?:kill|hurt|harm)\s+(?:myself|me)\b",
        r"\b(?:suicid(?:e|al)|self[-\s]?harm)\b",
        r"\b(?:end|take)\s+my\s+(?:own\s+)?life\b",
        r"\b(?:want|wanna|going)\s+to\s+die\b",
        r"\b(?:don'?t|do\s+not)\s+want\s+to\s+(?:live|be\s+here|exist)\b",
        r"\b(?:better\s+off\s+dead|no\s+reason\s+to\s+live|nothing\s+to\s+live\s+for)\b",
        r"\b(?:kill|hurt|harm)\s+(?:him|her|them|someone|somebody|others)\b",
        r"\b(?:cutting|cut)\s+myself\b",
    )
)

ACUTE_PATTERNS: Sequence[re.Pattern[str]] = tuple(
    re.compile(p, re.I)
    for p in (
        r"\bcan'?t\s+take\s+(?:it|this)(?:\s+anymore)?\b",
        r"\b(?:falling|fall)\s+apart\b",
        r"\bbreaking\s+down\b",
        r"\bpanick(?:ing|ed)?\s+attack\b",
        r"\bcan'?t\s+cope\b",
        r"\btoo\s+much\s+to\s+handle\b",
    )
)

_TOKEN_RE = re.compile(r"[a-z']+", re.I)


def content_words(text: str) -> Tuple[str, ...]:
    """Return lower-case content words in the order the user wrote them."""
    words: List[str] = []
    for raw in _TOKEN_RE.findall(text):
        token = raw.lower().strip("'")
        if token and token not in STOPWORDS:
            words.append(token)
    return tuple(words)


def emotion_surfaces(text: str) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Return (cluster, categories) using the user's own surface words.

    ``cluster`` is at most three items. If no emotion word is present, fall
    back to the user's first three content words so the cluster is still
    grounded in what they actually said.
    """
    lower = text.lower()
    cluster: List[str] = []
    categories: List[str] = []

    for phrase, category in EMOTION_PHRASES.items():
        if phrase in lower and phrase not in cluster:
            cluster.append(phrase)
            if category not in categories:
                categories.append(category)

    tokens = set(content_words(text))
    for category, words in EMOTION_WORDS.items():
        for word in words:
            if word in tokens and word not in cluster:
                cluster.append(word)
                if category not in categories:
                    categories.append(category)

    if not cluster:
        cluster = list(content_words(text)[:3])
    if not categories:
        categories = ["neutral"]
    return tuple(cluster[:3]), tuple(categories)


def distress_score(text: str) -> float:
    """Weighted, deterministic distress salience in [0, 1]."""
    lower = text.lower()
    tokens = set(content_words(text))
    total = 0.0
    for phrase, weight in DISTRESS_WEIGHTS.items():
        matched = phrase in lower if " " in phrase else phrase in tokens
        if matched:
            total += weight
    return round(min(1.0, total / 2.0), 2)


def detect_crisis(text: str) -> bool:
    """True on self-harm, harm to others, or acute distress language."""
    return any(p.search(text) for p in CRISIS_PATTERNS) or any(
        p.search(text) for p in ACUTE_PATTERNS
    )


def is_high_distress(score: float) -> bool:
    return score >= 0.55


def tokens_in(text: str, words: Iterable[str]) -> bool:
    token_set = set(_TOKEN_RE.findall(text.lower()))
    return all(w.lower() in token_set for w in words)
