"""
Deterministic mock news provider.

This exists so the entire news/sentiment path can be exercised end-to-end -- in
tests and in a no-credentials dev run -- WITHOUT a real news feed, while never
letting synthetic headlines masquerade as real ones (spec sections 2, 28, 53,
61).

Honesty guarantees:
- every item is stamped ``SourceTier.MOCK`` and ``is_mock`` is True,
- the returned set is a seeded, deterministic slice of a fixed mixed-polarity
  catalog keyed by the instrument symbol, so the same symbol always yields the
  same headlines (reproducible tests) but they are clearly labelled synthetic,
- it never claims to be a real vendor and must never be used as evidence of an
  actual market-moving event.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from ..domain.enums import SourceTier
from ..domain.instrument import Instrument
from ..domain.news import NewsItem
from ..domain.provenance import Provenance
from .news_base import NewsProvider

_MOCK_SOURCE = "mock-newswire"

# A fixed, mixed-polarity catalog. Deliberately spans bullish, bearish and
# neutral headlines so the classifier and aggregation are exercised honestly.
_CATALOG: tuple[str, ...] = (
    "{sym} beats quarterly earnings estimates as profit surges",
    "{sym} shares rally after analyst upgrade and raised outlook",
    "{sym} announces record revenue growth and a new buyback",
    "{sym} stock jumps on strong momentum and rising volume",
    "{sym} misses revenue guidance as margins decline",
    "{sym} plunges after profit warning and downgrade",
    "{sym} faces lawsuit and regulatory probe over disclosures",
    "{sym} slashes dividend amid weak demand and mounting losses",
    "{sym} holds annual shareholder meeting next week",
    "{sym} names new chief operating officer",
    "{sym} to present at an industry conference on Thursday",
    "{sym} rebounds as sector strength lifts sentiment",
)


def _seed_for(symbol: str) -> int:
    digest = hashlib.sha1(symbol.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


class MockNewsProvider(NewsProvider):
    """A reproducible, clearly-labelled synthetic news source."""

    name = "mock"
    tier = SourceTier.MOCK

    async def get_news(
        self,
        instrument: Instrument,
        *,
        limit: int,
    ) -> tuple[NewsItem, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive.")

        seed = _seed_for(instrument.symbol)
        # Deterministic rotation into the catalog keyed by the symbol, so the
        # same instrument always yields the same headlines in the same order.
        offset = seed % len(_CATALOG)
        count = min(limit, len(_CATALOG))

        now = datetime.now(timezone.utc).replace(microsecond=0)
        provenance = Provenance(
            source=_MOCK_SOURCE,
            tier=SourceTier.MOCK,
            detail="deterministic synthetic headline catalog",
        )

        items: list[NewsItem] = []
        for i in range(count):
            template = _CATALOG[(offset + i) % len(_CATALOG)]
            headline = template.format(sym=instrument.symbol)
            # Most-recent first: item i is i hours older than 'now'.
            published_at = now - timedelta(hours=i)
            items.append(
                NewsItem(
                    instrument_key=instrument.key,
                    headline=headline,
                    source=_MOCK_SOURCE,
                    provenance=provenance,
                    summary="",
                    url=None,
                    published_at=published_at,
                )
            )
        return tuple(items)
