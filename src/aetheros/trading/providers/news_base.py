"""
News-provider abstraction.

The news/sentiment layer depends on this interface, never on a concrete feed, so
a real news vendor/RSS/API adapter can be swapped in later without touching the
sentiment or service layers (CLAUDE.md sections 10, 23 -- dependency inversion).

A provider's job is narrow and honest:
- return the most-recent :class:`NewsItem` headlines for an instrument,
- stamp every item with Provenance (source + SourceTier) and never claim a tier
  it cannot back up,
- raise a typed :class:`NewsError` rather than fabricating headlines when it
  cannot fulfil a request.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.enums import SourceTier
from ..domain.instrument import Instrument
from ..domain.news import NewsItem


class NewsProvider(ABC):
    """Interface every news source implements."""

    #: Human-readable source label used in Provenance.
    name: str = "unknown"

    #: The best tier this provider can honestly claim for its data.
    tier: SourceTier = SourceTier.UNVERIFIED

    @property
    def is_mock(self) -> bool:
        return self.tier is SourceTier.MOCK

    @abstractmethod
    async def get_news(
        self,
        instrument: Instrument,
        *,
        limit: int,
    ) -> tuple[NewsItem, ...]:
        """
        Return up to ``limit`` most-recent headlines for the instrument.

        Must raise a :class:`NewsError` (never fabricate) if the feed cannot be
        retrieved. Each returned NewsItem carries its own Provenance. An empty
        tuple is a legitimate honest result (no news found), distinct from a
        failure.
        """
        raise NotImplementedError
