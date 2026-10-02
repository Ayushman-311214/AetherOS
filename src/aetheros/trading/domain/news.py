"""
News & sentiment value objects (spec sections 5, 9, 26 item #9).

The news/sentiment layer turns sourced headlines into discrete, auditable
sentiment signals. Its value objects follow the same honesty discipline as the
rest of the domain:

- a :class:`NewsItem` is the *raw*, sourced headline as a provider returned it,
  content-addressed so the same headline dedupes across runs and never carries
  a fabricated timestamp identity;
- a :class:`ScoredNewsItem` pairs one item with the *deterministic* directional
  read the classifier assigned it -- the sentiment is clearly a derived opinion
  over sourced text, never presented as the source's own claim;
- a :class:`NewsAnalysis` is the aggregate: the fused sentiment lean, the
  positive/negative/neutral split, the :class:`Evidence` it yields, and -- like
  every other analysis object -- an explicit ``is_reliable`` flag plus
  ``limitations`` that say plainly when the read should NOT be trusted (mock
  data, too few items, or none at all).

Sentiment is an interpretation, not a fact (spec section 15): nothing here
stores a classifier opinion as an observed truth, and a MOCK or empty feed can
never masquerade as a real, reliable signal (sections 2, 28, 61).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Confidence, Direction
from .evidence import Evidence
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _stable_id(*, instrument_key: str, source: str, headline: str) -> str:
    """
    Content-addressed id: same headline from the same source -> same id.

    Deliberately excludes the publish timestamp so re-fetching the "same" story
    is recognised as one item rather than a brand-new one each poll.
    """
    payload = "|".join((instrument_key, source.strip().lower(), headline.strip().lower()))
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"news_{digest[:16]}"


@dataclass(frozen=True, slots=True)
class NewsItem:
    """A single sourced headline as a provider returned it (no interpretation)."""

    instrument_key: str
    headline: str
    source: str
    provenance: Provenance
    summary: str = ""
    url: str | None = None
    published_at: datetime | None = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(
                self,
                "id",
                _stable_id(
                    instrument_key=self.instrument_key,
                    source=self.source,
                    headline=self.headline,
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instrument_key": self.instrument_key,
            "headline": self.headline,
            "summary": self.summary,
            "source": self.source,
            "url": self.url,
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ScoredNewsItem:
    """A news item paired with the deterministic sentiment read it was given."""

    item: NewsItem
    direction: Direction
    score: float  # signed polarity in [-1, 1]; sign = direction, magnitude = strength
    confidence: Confidence
    positive_terms: tuple[str, ...] = ()
    negative_terms: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.item.to_dict(),
            "sentiment": {
                "direction": self.direction.value,
                "score": self.score,
                "confidence": self.confidence.value,
                "positive_terms": list(self.positive_terms),
                "negative_terms": list(self.negative_terms),
            },
        }


@dataclass(frozen=True, slots=True)
class NewsAnalysis:
    """Aggregate news sentiment for an instrument, with its full audit trail."""

    instrument: Instrument
    items: tuple[ScoredNewsItem, ...]
    direction: Direction
    sentiment_score: float  # mean signed polarity across items, [-1, 1]
    positive_count: int
    negative_count: int
    neutral_count: int
    confidence: Confidence
    evidence: tuple[Evidence, ...]
    provenance: Provenance
    quality: DataQuality
    is_reliable: bool
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def item_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            # Sentiment is a derived interpretation of sourced text, never a
            # guarantee about price (spec sections 3, 15, 28).
            "direction": self.direction.value,
            "sentiment_score": self.sentiment_score,
            "confidence": self.confidence.value,
            "counts": {
                "positive": self.positive_count,
                "negative": self.negative_count,
                "neutral": self.neutral_count,
                "total": self.item_count,
            },
            "is_reliable": self.is_reliable,
            "items": [scored.to_dict() for scored in self.items],
            "evidence": [ev.to_dict() for ev in self.evidence],
            "limitations": list(self.limitations),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
            "created_at": self.created_at.isoformat(),
        }
