"""
Deterministic news & sentiment tests (spec sections 5, 9, 21, 28).

Three layers, each pinned to the honesty rules:
- the finance-lexicon ``classify`` classifier is deterministic, handles local
  negation, and returns UNKNOWN (never a fabricated lean) on empty or
  no-vocabulary text;
- ``MockNewsProvider`` is reproducible and loudly stamped ``SourceTier.MOCK``;
- ``NewsSentimentService`` fuses scored headlines into an auditable
  ``NewsAnalysis`` that can never present MOCK, empty, or too-thin data as a
  reliable signal, and publishes a ``NewsSentimentAnalyzed`` event.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.domain.enums import (
    Assertion,
    DataQualityStatus,
    Direction,
    EvidenceType,
    SourceTier,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.news import NewsItem
from aetheros.trading.domain.provenance import Provenance
from aetheros.trading.errors import NewsError
from aetheros.trading.events import NewsSentimentAnalyzed
from aetheros.trading.news.sentiment import classify
from aetheros.trading.providers.mock_news_provider import MockNewsProvider
from aetheros.trading.providers.news_base import NewsProvider
from aetheros.trading.services.news_service import NewsSentimentService

_BULLISH = "{sym} beats quarterly earnings estimates as profit surges"
_BEARISH = "{sym} misses revenue guidance as margins decline and losses mount"
_NEUTRAL = "{sym} names new chief operating officer next week"


def _item(headline: str, *, tier: SourceTier = SourceTier.SECONDARY) -> NewsItem:
    """A controllable, clearly-synthetic news item stamped a non-mock tier."""
    return NewsItem(
        instrument_key="AAPL",
        headline=headline,
        source="fake-wire",
        provenance=Provenance(
            source="fake-wire", tier=tier, detail="synthetic test headline"
        ),
    )


class FakeNewsProvider(NewsProvider):
    """Hands back exactly the items the test built; non-mock so it can be reliable."""

    name = "fake-wire"
    tier = SourceTier.SECONDARY

    def __init__(self, items: tuple[NewsItem, ...]) -> None:
        self._items = items

    async def get_news(self, instrument, *, limit) -> tuple[NewsItem, ...]:
        return self._items[:limit]


def _service(provider: NewsProvider, *, event_bus=None) -> NewsSentimentService:
    return NewsSentimentService(provider, get_settings(), event_bus=event_bus)


# ----------------------------------------------------------------------
# Classifier
# ----------------------------------------------------------------------


def test_classify_bullish_text_is_up():
    read = classify("Company beats earnings as profit surges and revenue grows")
    assert read.direction is Direction.UP
    assert read.score > 0.0
    assert "beats" in read.positive_terms


def test_classify_bearish_text_is_down():
    read = classify("Company misses guidance as margins decline and losses mount")
    assert read.direction is Direction.DOWN
    assert read.score < 0.0
    assert read.negative_terms


def test_classify_negation_flips_polarity():
    # "fails to beat" must read bearish, not bullish -- the negator flips "beat".
    read = classify("Company fails to beat estimates")
    assert read.direction is Direction.DOWN
    assert "beat" in read.negative_terms
    assert "beat" not in read.positive_terms


def test_classify_empty_text_is_unknown():
    read = classify("")
    assert read.direction is Direction.UNKNOWN
    assert read.score == 0.0


def test_classify_no_vocabulary_is_unknown():
    # Real words, zero finance vocabulary -> honest "no signal", not a lean.
    read = classify("The company will hold a meeting on Tuesday afternoon")
    assert read.direction is Direction.UNKNOWN
    assert read.score == 0.0


def test_classify_balanced_text_is_sideways():
    # Equal bullish and bearish terms cancel to a within-band neutral read.
    read = classify("profit growth offset by weak demand and losses")
    assert read.direction is Direction.SIDEWAYS


def test_classify_is_deterministic():
    text = "Company beats earnings as profit surges"
    assert classify(text) == classify(text)


# ----------------------------------------------------------------------
# MockNewsProvider
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_provider_is_deterministic():
    provider = MockNewsProvider()
    inst = Instrument.parse("AAPL")
    first = await provider.get_news(inst, limit=8)
    second = await provider.get_news(inst, limit=8)
    assert [i.headline for i in first] == [i.headline for i in second]
    assert [i.id for i in first] == [i.id for i in second]


@pytest.mark.asyncio
async def test_mock_provider_is_labelled_mock():
    provider = MockNewsProvider()
    assert provider.tier is SourceTier.MOCK
    assert provider.is_mock is True
    items = await provider.get_news(Instrument.parse("AAPL"), limit=5)
    assert items
    assert all(i.provenance.tier is SourceTier.MOCK for i in items)


@pytest.mark.asyncio
async def test_mock_provider_rejects_non_positive_limit():
    with pytest.raises(ValueError):
        await MockNewsProvider().get_news(Instrument.parse("AAPL"), limit=0)


@pytest.mark.asyncio
async def test_mock_provider_caps_limit_at_catalog_size():
    items = await MockNewsProvider().get_news(Instrument.parse("AAPL"), limit=500)
    # A finite catalog can never fabricate more headlines than it holds.
    assert 0 < len(items) <= 12
    small = await MockNewsProvider().get_news(Instrument.parse("AAPL"), limit=3)
    assert len(small) == 3


# ----------------------------------------------------------------------
# NewsSentimentService aggregation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_aggregates_bullish_feed_as_up():
    items = tuple(_item(_BULLISH.format(sym="AAPL")) for _ in range(4))
    analysis = await _service(FakeNewsProvider(items)).analyze("AAPL")
    assert analysis.direction is Direction.UP
    assert analysis.positive_count == 4
    assert analysis.negative_count == 0
    assert analysis.sentiment_score > 0.15
    # Non-mock feed with enough items clears the reliability gate.
    assert analysis.is_reliable is True


@pytest.mark.asyncio
async def test_service_counts_mixed_feed():
    items = (
        _item(_BULLISH.format(sym="AAPL")),
        _item(_BULLISH.format(sym="AAPL") + " again"),
        _item(_BEARISH.format(sym="AAPL")),
        _item(_NEUTRAL.format(sym="AAPL")),
    )
    analysis = await _service(FakeNewsProvider(items)).analyze("AAPL")
    assert analysis.positive_count == 2
    assert analysis.negative_count == 1
    assert analysis.neutral_count == 1
    assert analysis.item_count == 4


@pytest.mark.asyncio
async def test_service_builds_news_and_sentiment_evidence():
    items = tuple(_item(_BULLISH.format(sym="AAPL")) for _ in range(3))
    analysis = await _service(FakeNewsProvider(items)).analyze("AAPL")
    types = {ev.type for ev in analysis.evidence}
    assert EvidenceType.SENTIMENT in types  # the fused aggregate lean
    assert EvidenceType.NEWS in types  # per-headline directional claims
    # Sentiment is a derived reading, so it is DETECTED, never OBSERVED fact.
    assert all(ev.assertion is Assertion.DETECTED for ev in analysis.evidence)


@pytest.mark.asyncio
async def test_service_mock_feed_is_never_reliable():
    analysis = await _service(MockNewsProvider()).analyze("AAPL", limit=12)
    assert analysis.is_reliable is False
    assert analysis.provenance.tier is SourceTier.MOCK
    assert any("MOCK" in lim for lim in analysis.limitations)


@pytest.mark.asyncio
async def test_service_empty_feed_is_missing_and_honest():
    analysis = await _service(FakeNewsProvider(())).analyze("AAPL")
    assert analysis.quality.status is DataQualityStatus.MISSING
    assert analysis.direction is Direction.UNKNOWN
    assert analysis.is_reliable is False
    assert analysis.item_count == 0
    assert any("no news" in lim.lower() for lim in analysis.limitations)


@pytest.mark.asyncio
async def test_service_thin_feed_is_low_and_not_reliable():
    settings = get_settings()
    thin = settings.TRADING_NEWS_MIN_ITEMS - 1
    assert thin >= 1
    items = tuple(_item(_BULLISH.format(sym="AAPL")) for _ in range(thin))
    analysis = await _service(FakeNewsProvider(items)).analyze("AAPL")
    # A real but too-thin sample must not be trusted, however lopsided.
    assert analysis.is_reliable is False
    assert any(str(thin) in lim or "thin" in lim.lower() for lim in analysis.limitations)


@pytest.mark.asyncio
async def test_service_publishes_event():
    received: list[NewsSentimentAnalyzed] = []
    bus = EventBus()
    await bus.subscribe(NewsSentimentAnalyzed, lambda e: received.append(e))

    items = tuple(_item(_BULLISH.format(sym="AAPL")) for _ in range(3))
    await _service(FakeNewsProvider(items), event_bus=bus).analyze("AAPL")

    assert len(received) == 1
    assert received[0].instrument_key == "AAPL"
    assert received[0].direction == Direction.UP.value
    assert received[0].item_count == 3


@pytest.mark.asyncio
async def test_service_rejects_empty_symbol():
    with pytest.raises(NewsError):
        await _service(FakeNewsProvider(())).analyze("")


@pytest.mark.asyncio
async def test_service_rejects_non_positive_limit():
    with pytest.raises(NewsError):
        await _service(FakeNewsProvider(())).analyze("AAPL", limit=0)
