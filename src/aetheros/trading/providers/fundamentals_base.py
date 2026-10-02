"""
Fundamentals-provider abstraction.

The fundamental-analysis layer depends on this interface, never on a concrete
feed, so a real financial-statements vendor/API adapter can be swapped in later
without touching the scoring or service layers (CLAUDE.md sections 10, 23 --
dependency inversion).

A provider's job is narrow and honest:
- return a single :class:`FundamentalSnapshot` of the latest reported financials
  for an instrument,
- stamp it with Provenance (source + SourceTier) and never claim a tier it
  cannot back up, leaving any line it does not have as ``None`` rather than a
  fabricated zero,
- raise a typed :class:`FundamentalsError` rather than inventing financials when
  it cannot fulfil a request.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.enums import SourceTier
from ..domain.fundamentals import FundamentalSnapshot
from ..domain.instrument import Instrument


class FundamentalsProvider(ABC):
    """Interface every fundamentals source implements."""

    #: Human-readable source label used in Provenance.
    name: str = "unknown"

    #: The best tier this provider can honestly claim for its data.
    tier: SourceTier = SourceTier.UNVERIFIED

    @property
    def is_mock(self) -> bool:
        return self.tier is SourceTier.MOCK

    @abstractmethod
    async def get_fundamentals(
        self,
        instrument: Instrument,
    ) -> FundamentalSnapshot:
        """
        Return the latest reported financials for the instrument.

        Must raise a :class:`FundamentalsError` (never fabricate) if the feed
        cannot be retrieved. Any metric the source does not report is left
        ``None`` on the snapshot -- a missing line is honestly absent, not a
        fabricated zero. A snapshot with no reported metrics is a legitimate
        honest result (the source has nothing), distinct from a failure.
        """
        raise NotImplementedError
