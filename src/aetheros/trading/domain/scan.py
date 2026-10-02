"""
Watchlist-scan value objects.

A :class:`ScanResult` is the deterministic ranking of a watchlist: each symbol's
evidence-grounded directional read (from the analysis layer), ordered so the
strongest *actionable* setups surface first. It is the multi-instrument
counterpart to the single-name analysis (CLAUDE.md sections 1, 26): the same
honesty rules apply per row -- a mock/unusable/UNKNOWN symbol is included but
flagged not actionable and ranked last, and a symbol whose data could not be
fetched is reported as an error row rather than silently dropped or fabricated.

The scan ranks; it computes no signal of its own. Every field on a row traces to
that symbol's :class:`TradingAnalysis` (sections 5, 28).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Confidence, Direction


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class ScanEntry:
    """One symbol's compact directional read within a watchlist scan."""

    symbol: str  # as requested by the caller, verbatim
    instrument_key: str  # resolved instrument key, or the raw symbol on error
    direction: Direction
    directional_score: float
    confidence: Confidence
    last_price: float | None
    is_actionable: bool
    is_reliable: bool  # usable, non-mock data -- leanable-on
    is_mock: bool
    note: str = ""  # first limitation, or an error message
    errored: bool = False  # the symbol could not be analysed at all

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "instrument_key": self.instrument_key,
            "direction": self.direction.value,
            "directional_score": self.directional_score,
            "confidence": self.confidence.value,
            "last_price": self.last_price,
            "is_actionable": self.is_actionable,
            "is_reliable": self.is_reliable,
            "is_mock": self.is_mock,
            "note": self.note,
            "errored": self.errored,
        }


@dataclass(frozen=True, slots=True)
class ScanResult:
    """A ranked watchlist scan over several instruments."""

    timeframe_value: str
    entries: tuple[ScanEntry, ...]  # already ranked, strongest actionable first
    requested: int
    analysed: int
    errored: int
    actionable: int
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timeframe": self.timeframe_value,
            "requested": self.requested,
            "analysed": self.analysed,
            "errored": self.errored,
            "actionable": self.actionable,
            "entries": [e.to_dict() for e in self.entries],
            "created_at": self.created_at.isoformat(),
        }
