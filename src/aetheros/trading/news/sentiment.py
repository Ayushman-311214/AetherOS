"""
Deterministic finance-lexicon sentiment classifier.

This is intentionally a small, transparent, reproducible classifier -- NOT an
LLM. Given a piece of text it returns a signed polarity in ``[-1, 1]`` derived
from a fixed finance vocabulary, so the same headline always yields the same
score and every score is fully explainable by the terms it matched (spec
sections 5, 21, 28). An LLM-backed classifier is a clean future extension behind
the same ``classify`` contract -- the spec permits LLMs for language
understanding *provided the source data stays traceable* (section 5) -- but the
deterministic baseline must exist and be testable first.

The classifier is deliberately conservative: it counts bullish and bearish
terms, applies simple local negation ("fails to beat" flips "beat"), and reports
the *net* lean. Text with no finance vocabulary at all is ``UNKNOWN`` with a
zero score, never a fabricated lean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..domain.enums import Confidence, Direction

# Bullish vocabulary. Kept lowercase and space-normalised; multi-word phrases are
# matched against the normalised token stream.
_POSITIVE: frozenset[str] = frozenset(
    {
        "beat", "beats", "surge", "surges", "surged", "soar", "soars", "soared",
        "rally", "rallies", "gain", "gains", "gained", "record", "upgrade",
        "upgraded", "outperform", "outperforms", "profit", "profits", "growth",
        "grow", "grows", "strong", "strength", "bullish", "rise", "rises",
        "rose", "jump", "jumps", "jumped", "tops", "top", "exceed", "exceeds",
        "exceeded", "buyback", "expansion", "expand", "expands", "win", "wins",
        "won", "approval", "approved", "breakthrough", "optimistic", "boost",
        "boosts", "boosted", "upbeat", "higher", "raises", "raised", "rebound",
        "rebounds", "positive", "accelerate", "accelerates", "momentum",
        "dividend", "outlook",
    }
)

# Bearish vocabulary.
_NEGATIVE: frozenset[str] = frozenset(
    {
        "miss", "misses", "missed", "plunge", "plunges", "plunged", "slump",
        "slumps", "crash", "crashes", "crashed", "fall", "falls", "fell",
        "drop", "drops", "dropped", "downgrade", "downgraded", "underperform",
        "underperforms", "loss", "losses", "weak", "weakness", "bearish",
        "decline", "declines", "declined", "cut", "cuts", "layoff", "layoffs",
        "lawsuit", "probe", "investigation", "fraud", "recall", "bankruptcy",
        "warning", "warns", "warned", "slash", "slashes", "slashed", "plummet",
        "plummets", "plummeted", "tumble", "tumbles", "tumbled", "concern",
        "concerns", "lower", "downbeat", "disappointing", "disappoints",
        "default", "defaults", "sink", "sinks", "sank", "halt", "halts",
        "halted", "delay", "delays", "delayed", "negative", "risk", "risks",
        "selloff",
    }
)

# Structural negators. These are NOT scored themselves; they flip the polarity of
# a lexicon term appearing within the look-back window after them.
_NEGATORS: frozenset[str] = frozenset(
    {
        "not", "no", "never", "without", "cannot", "cant", "isnt", "arent",
        "wasnt", "werent", "dont", "doesnt", "didnt", "fails", "failed", "fail",
    }
)

# How many preceding tokens a negator reaches forward to flip.
_NEGATION_WINDOW = 2

# Net-polarity dead-band: |score| below this is SIDEWAYS (had vocabulary but no
# clear lean) rather than a weak directional call.
_DIRECTION_BAND = 0.15

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class LexiconSentiment:
    """The deterministic sentiment read for one piece of text."""

    direction: Direction
    score: float  # signed polarity in [-1, 1]
    confidence: Confidence
    positive_terms: tuple[str, ...]
    negative_terms: tuple[str, ...]


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def classify(text: str) -> LexiconSentiment:
    """
    Classify ``text`` into a deterministic directional sentiment.

    Returns UNKNOWN with a zero score when no finance vocabulary is present --
    an honest "no signal", never a fabricated lean.
    """
    tokens = _tokenize(text)
    if not tokens:
        return LexiconSentiment(Direction.UNKNOWN, 0.0, Confidence.LOW, (), ())

    positive_hits: list[str] = []
    negative_hits: list[str] = []

    for i, token in enumerate(tokens):
        polarity = 1 if token in _POSITIVE else -1 if token in _NEGATIVE else 0
        if polarity == 0:
            continue
        # Local negation: a negator within the preceding window flips the term.
        window = tokens[max(0, i - _NEGATION_WINDOW):i]
        if any(w in _NEGATORS for w in window):
            polarity = -polarity
        if polarity > 0:
            positive_hits.append(token)
        else:
            negative_hits.append(token)

    total = len(positive_hits) + len(negative_hits)
    if total == 0:
        return LexiconSentiment(Direction.UNKNOWN, 0.0, Confidence.LOW, (), ())

    score = (len(positive_hits) - len(negative_hits)) / total
    score = round(max(-1.0, min(1.0, score)), 6)

    if score >= _DIRECTION_BAND:
        direction = Direction.UP
    elif score <= -_DIRECTION_BAND:
        direction = Direction.DOWN
    else:
        # Had vocabulary, but the bulls and bears roughly cancel.
        direction = Direction.SIDEWAYS

    confidence = Confidence.from_score(abs(score))
    return LexiconSentiment(
        direction=direction,
        score=score,
        confidence=confidence,
        positive_terms=tuple(positive_hits),
        negative_terms=tuple(negative_hits),
    )
