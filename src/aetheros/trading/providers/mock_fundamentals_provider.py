"""
Deterministic mock fundamentals provider.

This exists so the entire fundamental-analysis path can be exercised end-to-end
-- in tests and in a no-credentials dev run -- WITHOUT a real financials feed,
while never letting synthetic financials masquerade as real ones (spec sections
2, 28, 53, 61).

Honesty guarantees:
- the snapshot is stamped ``SourceTier.MOCK`` and ``is_mock`` is True,
- every metric is a seeded, deterministic function of the instrument symbol, so
  the same symbol always yields the same figures (reproducible tests) but they
  are clearly labelled synthetic,
- it never claims to be a real vendor and must never be used as evidence of a
  company's actual financial condition.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ..domain.enums import SourceTier
from ..domain.fundamentals import FundamentalSnapshot
from ..domain.instrument import Instrument
from ..domain.provenance import Provenance
from .fundamentals_base import FundamentalsProvider

_MOCK_SOURCE = "mock-fundamentals"

# A fixed placeholder reporting-period end. Deliberately constant so the mock is
# fully deterministic (stable content-addressed id) and obviously synthetic.
_AS_OF = datetime(2025, 12, 31, tzinfo=timezone.utc)


def _seed_for(symbol: str) -> str:
    return hashlib.sha1(symbol.encode("utf-8")).hexdigest()


def _unit(digest: str, start: int) -> float:
    """A deterministic pseudo-value in [0, 1] from a 4-hex slice of the digest."""
    return int(digest[start : start + 4], 16) / 0xFFFF


def _span(digest: str, start: int, lo: float, hi: float) -> float:
    """Map a digest slice into the inclusive band [lo, hi]."""
    return round(lo + (hi - lo) * _unit(digest, start), 4)


class MockFundamentalsProvider(FundamentalsProvider):
    """A reproducible, clearly-labelled synthetic fundamentals source."""

    name = "mock"
    tier = SourceTier.MOCK

    async def get_fundamentals(
        self,
        instrument: Instrument,
    ) -> FundamentalSnapshot:
        d = _seed_for(instrument.symbol)

        # An archetype bias in {0: weak, 1: mixed, 2: strong} keeps the catalog
        # spanning bullish, neutral and bearish companies so the scorer is
        # exercised honestly across symbols.
        archetype = int(d[0], 16) % 3
        bias = (archetype - 1) * 0.5  # -0.5, 0.0, +0.5

        revenue = _span(d, 4, 5.0e8, 5.0e10)
        net_margin = round(_span(d, 8, -0.05, 0.25) + bias * 0.1, 4)
        gross_margin = round(min(0.9, max(0.05, net_margin + _span(d, 12, 0.1, 0.4))), 4)
        operating_margin = round(min(gross_margin, max(-0.1, net_margin + 0.03)), 4)

        return FundamentalSnapshot(
            instrument_key=instrument.key,
            provenance=Provenance(
                source=_MOCK_SOURCE,
                tier=SourceTier.MOCK,
                detail="deterministic synthetic financials",
            ),
            currency="USD",
            as_of=_AS_OF,
            revenue=revenue,
            net_income=round(revenue * net_margin, 2),
            gross_margin=gross_margin,
            operating_margin=operating_margin,
            net_margin=net_margin,
            revenue_growth_yoy=round(_span(d, 16, -0.10, 0.30) + bias * 0.1, 4),
            earnings_growth_yoy=round(_span(d, 20, -0.20, 0.40) + bias * 0.1, 4),
            return_on_equity=round(_span(d, 24, -0.05, 0.30) + bias * 0.05, 4),
            debt_to_equity=round(_span(d, 28, 0.1, 3.0) - bias * 0.6, 4),
            current_ratio=round(_span(d, 32, 0.6, 3.0) + bias * 0.4, 4),
            free_cash_flow=round(revenue * _span(d, 4, -0.05, 0.20), 2),
            pe_ratio=round(_span(d, 12, 5.0, 45.0), 2),
            pb_ratio=round(_span(d, 16, 0.5, 8.0), 2),
            price_to_sales=round(_span(d, 20, 0.5, 12.0), 2),
            dividend_yield=round(_span(d, 24, 0.0, 0.05), 4),
        )
