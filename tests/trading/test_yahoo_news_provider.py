"""
YahooNewsProvider: the first real news adapter.

These tests are fully deterministic and never touch the network: they drive the
provider through an ``httpx.MockTransport`` that returns canned Yahoo
``/v1/finance/search`` payloads (or failures). They pin the things that matter
for a real news source under the spec's honesty rules (CLAUDE.md sections 9, 15,
20, 28, 61): it parses a real payload into correctly-shaped, non-mock
``SourceTier.SECONDARY`` headlines (raw text only -- no sentiment); it orders
most-recent-first and dedupes a repeated story; an item with no title is skipped
rather than fabricated; an empty news list is an honest "no news" (not a
failure); and any transport/shape failure raises a typed :class:`NewsError`.
"""

from __future__ import annotations

import httpx
import pytest

from aetheros.trading.domain.enums import SourceTier
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.errors import NewsError
from aetheros.trading.providers.yahoo_news_provider import YahooNewsProvider


def _news_item(title, *, publisher="Reuters", link="https://example.com/a", ts=1_711_929_600):
    item: dict = {}
    if title is not None:
        item["title"] = title
    if publisher is not None:
        item["publisher"] = publisher
    if link is not None:
        item["link"] = link
    if ts is not None:
        item["providerPublishTime"] = ts
    return item


def _search_payload(*, news=None, drop_news=False):
    payload: dict = {"count": 0, "quotes": []}
    if not drop_news:
        payload["news"] = news if news is not None else []
    return payload


def _provider(handler) -> YahooNewsProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return YahooNewsProvider(client=client)


def _ok_handler(payload, *, capture: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture.append(request)
        return httpx.Response(200, json=payload)

    return handler


@pytest.mark.asyncio
async def test_parses_real_payload_into_secondary_headlines():
    payload = _search_payload(
        news=[
            _news_item("AAPL beats quarterly earnings estimates", ts=1_700_000_100),
            _news_item("AAPL faces regulatory probe", publisher="Bloomberg",
                       link="https://example.com/b", ts=1_700_000_500),
        ]
    )
    provider = _provider(_ok_handler(payload))
    items = await provider.get_news(Instrument("AAPL"), limit=10)

    assert len(items) == 2
    for item in items:
        assert item.provenance.tier is SourceTier.SECONDARY
        assert item.provenance.tier is not SourceTier.MOCK
        assert item.instrument_key == Instrument("AAPL").key
        assert item.summary == ""  # search feed carries no body; never fabricated
    # Most-recent first.
    assert items[0].headline == "AAPL faces regulatory probe"
    assert items[0].source == "Bloomberg"
    assert items[0].url == "https://example.com/b"


@pytest.mark.asyncio
async def test_orders_most_recent_first():
    payload = _search_payload(
        news=[
            _news_item("older", ts=1_000),
            _news_item("newer", ts=9_000),
            _news_item("middle", ts=5_000),
        ]
    )
    provider = _provider(_ok_handler(payload))
    items = await provider.get_news(Instrument("AAPL"), limit=10)
    assert [i.headline for i in items] == ["newer", "middle", "older"]


@pytest.mark.asyncio
async def test_items_without_title_are_skipped_not_fabricated():
    payload = _search_payload(
        news=[
            _news_item(None),  # no title key
            _news_item("   "),  # blank title
            _news_item("real headline"),
        ]
    )
    provider = _provider(_ok_handler(payload))
    items = await provider.get_news(Instrument("AAPL"), limit=10)
    assert [i.headline for i in items] == ["real headline"]


@pytest.mark.asyncio
async def test_duplicate_story_is_deduped():
    payload = _search_payload(
        news=[
            _news_item("same story", ts=2_000),
            _news_item("same story", ts=2_000),
        ]
    )
    provider = _provider(_ok_handler(payload))
    items = await provider.get_news(Instrument("AAPL"), limit=10)
    assert len(items) == 1


@pytest.mark.asyncio
async def test_missing_publisher_falls_back_to_source_label():
    payload = _search_payload(news=[_news_item("headline", publisher=None)])
    provider = _provider(_ok_handler(payload))
    items = await provider.get_news(Instrument("AAPL"), limit=10)
    assert items[0].source == "yahoo"


@pytest.mark.asyncio
async def test_limit_caps_returned_items():
    payload = _search_payload(
        news=[_news_item(f"headline {i}", ts=1_000 + i) for i in range(8)]
    )
    provider = _provider(_ok_handler(payload))
    items = await provider.get_news(Instrument("AAPL"), limit=3)
    assert len(items) == 3


@pytest.mark.asyncio
async def test_empty_news_list_is_honest_no_news_not_an_error():
    payload = _search_payload(news=[])
    provider = _provider(_ok_handler(payload))
    items = await provider.get_news(Instrument("AAPL"), limit=10)
    assert items == ()


@pytest.mark.asyncio
async def test_maps_exchange_to_yahoo_suffix():
    captured: list[httpx.Request] = []
    payload = _search_payload(news=[_news_item("headline")])
    provider = _provider(_ok_handler(payload, capture=captured))
    await provider.get_news(Instrument("RELIANCE", exchange="NSE"), limit=5)
    assert captured, "no request captured"
    assert "RELIANCE.NS" in str(captured[0].url)


@pytest.mark.asyncio
async def test_non_positive_limit_raises_value_error():
    provider = _provider(_ok_handler(_search_payload(news=[])))
    with pytest.raises(ValueError):
        await provider.get_news(Instrument("AAPL"), limit=0)


@pytest.mark.asyncio
async def test_missing_news_list_becomes_news_error():
    payload = _search_payload(drop_news=True)
    provider = _provider(_ok_handler(payload))
    with pytest.raises(NewsError):
        await provider.get_news(Instrument("AAPL"), limit=10)


@pytest.mark.asyncio
async def test_http_error_becomes_news_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    provider = _provider(handler)
    with pytest.raises(NewsError):
        await provider.get_news(Instrument("NOPE"), limit=10)


@pytest.mark.asyncio
async def test_network_error_becomes_news_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(handler)
    with pytest.raises(NewsError):
        await provider.get_news(Instrument("AAPL"), limit=10)
