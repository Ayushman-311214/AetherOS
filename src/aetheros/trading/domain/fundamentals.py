"""
Fundamental-analysis value objects (spec sections 5, 9, 26).

The fundamentals layer turns sourced company financials into a discrete,
auditable read on company health and valuation. Its value objects follow the
same honesty discipline as the rest of the domain:

- a :class:`FundamentalSnapshot` is the *raw*, sourced financial data as a
  provider returned it -- every metric is Optional because a real feed may not
  report every line, and a missing metric is honestly ``None`` rather than a
  fabricated zero (spec section 9);
- a :class:`FundamentalFactor` is one *deterministic* signed read the scorer
  derived from a single metric -- clearly a derived opinion over sourced data,
  never the source's own claim;
- a :class:`FundamentalAnalysis` is the aggregate: the fused health/valuation
  lean, the factors behind it, the :class:`Evidence` it yields, and -- like
  every other analysis object -- an explicit ``is_reliable`` flag plus
  ``limitations`` that say plainly when the read should NOT be trusted (mock
  data, or too few reported metrics to judge).

A fundamental read is an interpretation, not a guarantee about price (spec
sections 3, 15, 28): nothing here stores a scorer opinion as an observed truth,
and a MOCK snapshot can never masquerade as a real, reliable read (sections 2,
28, 61).
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


def _stable_id(*, instrument_key: str, source: str, as_of: datetime | None) -> str:
    """
    Content-addressed id: same instrument + source + reporting period -> same id.

    Keyed on the reporting-period *date* (not the fetch time) so re-fetching the
    same quarterly filing is recognised as one snapshot rather than a brand-new
    one each poll.
    """
    day = as_of.date().isoformat() if as_of is not None else "unknown"
    payload = "|".join((instrument_key, source.strip().lower(), day))
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"fund_{digest[:16]}"


# The metric fields the scorer knows how to read, in a stable order. Used for
# counting reported coverage and for serialisation.
_METRIC_FIELDS: tuple[str, ...] = (
    "revenue",
    "net_income",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "revenue_growth_yoy",
    "earnings_growth_yoy",
    "return_on_equity",
    "debt_to_equity",
    "current_ratio",
    "free_cash_flow",
    "pe_ratio",
    "pb_ratio",
    "price_to_sales",
    "dividend_yield",
)


@dataclass(frozen=True, slots=True)
class FundamentalSnapshot:
    """Raw sourced company financials (no interpretation). Missing metric = None."""

    instrument_key: str
    provenance: Provenance
    currency: str = "USD"
    as_of: datetime | None = None  # reporting-period end the figures describe
    # Profitability
    revenue: float | None = None
    net_income: float | None = None
    gross_margin: float | None = None  # fraction, e.g. 0.42 == 42%
    operating_margin: float | None = None
    net_margin: float | None = None
    # Growth (year-over-year, as fractions)
    revenue_growth_yoy: float | None = None
    earnings_growth_yoy: float | None = None
    return_on_equity: float | None = None
    # Balance-sheet health
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    free_cash_flow: float | None = None
    # Valuation
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    price_to_sales: float | None = None
    dividend_yield: float | None = None  # fraction, e.g. 0.015 == 1.5%
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(
                self,
                "id",
                _stable_id(
                    instrument_key=self.instrument_key,
                    source=self.provenance.source,
                    as_of=self.as_of,
                ),
            )

    @property
    def reported_metrics(self) -> tuple[str, ...]:
        """Names of the metrics that were actually reported (non-None)."""
        return tuple(f for f in _METRIC_FIELDS if getattr(self, f) is not None)

    @property
    def metric_count(self) -> int:
        return len(self.reported_metrics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instrument_key": self.instrument_key,
            "currency": self.currency,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "metrics": {f: getattr(self, f) for f in _METRIC_FIELDS},
            "reported_metric_count": self.metric_count,
            "provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class FundamentalFactor:
    """
    One deterministic signed read the scorer derived from a single metric.

    ``score`` is in [-1, 1]: positive = healthy/attractive, negative =
    weak/expensive, 0 = neutral. It is a *derived opinion*, never the source's
    own claim -- ``metric``/``value`` keep the sourced figure it was read from
    so the lean stays auditable back to the snapshot.
    """

    metric: str
    value: float
    direction: Direction
    score: float
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "direction": self.direction.value,
            "score": round(self.score, 4),
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class FundamentalAnalysis:
    """
    The fused fundamental read: a health/valuation lean over sourced financials.

    ``health_score`` is the mean of the per-factor scores, in [-1, 1]. A MOCK
    snapshot, or too few reported metrics to judge, is honestly ``is_reliable =
    False`` with the reason spelled out in ``limitations`` (spec sections 28,
    61) -- the lean is still computed and shown, but must not be traded on.
    """

    instrument: Instrument
    snapshot: FundamentalSnapshot
    direction: Direction
    health_score: float
    confidence: Confidence
    factors: tuple[FundamentalFactor, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    provenance: Provenance | None = None
    quality: DataQuality | None = None
    is_reliable: bool = False
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def scored_metric_count(self) -> int:
        return len(self.factors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "direction": self.direction.value,
            "health_score": round(self.health_score, 4),
            "confidence": self.confidence.value,
            "scored_metric_count": self.scored_metric_count,
            "reported_metric_count": self.snapshot.metric_count,
            "factors": [f.to_dict() for f in self.factors],
            "snapshot": self.snapshot.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "quality": self.quality.to_dict() if self.quality else None,
            "is_reliable": self.is_reliable,
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
