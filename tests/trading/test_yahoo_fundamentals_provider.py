"""
YahooFundamentalsProvider: the first real fundamentals adapter.

These tests are fully deterministic and never touch the network: they drive the
provider through an ``httpx.MockTransport`` that returns canned Yahoo
``quoteSummary`` payloads (or failures). They pin the things that matter for a
real fundamentals source under the spec's honesty rules (CLAUDE.md sections 9,
20, 28, 61): it parses a real payload into a correctly-shaped, non-mock
``SourceTier.SECONDARY`` snapshot; it leaves lines Yahoo does not report as
``None`` rather than fabricating zeros; a result with no metrics is an honest
empty snapshot; and any failure raises a typed :class:`FundamentalsError`
rather than inventing financials.
"""

from __future__ import annotations

import httpx
import pytest

from aetheros.trading.domain.enums import SourceTier
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.errors import FundamentalsError
from aetheros.trading.providers.yahoo_fundamentals_provider import (
    YahooFundamentalsProvider,
)


def _summary_payload(
    *,
    financial: dict | None = None,
    key_stats: dict | None = None,
    summary: dict | None = None,
    price: dict | None = None,
    error=None,
    result_empty: bool = False,
):
    """Build a Yahoo /v10/finance/quoteSummary-shaped JSON payload."""
    if error is not None:
        return {"quoteSummary": {"result": None, "error": error}}
    if result_empty:
        return {"quoteSummary": {"result": [], "error": None}}
    return {
        "quoteSummary": {
            "result": [
                {
                    "financialData": financial or {},
                    "defaultKeyStatistics": key_stats or {},
                    "summaryDetail": summary or {},
                    "price": price or {},
                }
            ],
            "error": None,
        }
    }


def _provider(handler) -> YahooFundamentalsProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return YahooFundamentalsProvider(client=client)


def _ok_handler(payload, *, capture: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture.append(request)
        return httpx.Response(200, json=payload)

    return handler


@pytest.mark.asyncio
async def test_parses_real_payload_into_secondary_snapshot():
    payload = _summary_payload(
        financial={
            "totalRevenue": {"raw": 3.94e11},
            "grossMargins": {"raw": 0.44},
            "operatingMargins": {"raw": 0.30},
            "profitMargins": {"raw": 0.25},
            "revenueGrowth": {"raw": 0.08},
            "earningsGrowth": {"raw": 0.11},
            "returnOnEquity": {"raw": 1.5},
            "debtToEquity": {"raw": 150.5},  # percent form -> 1.505x
            "currentRatio": {"raw": 0.98},
            "freeCashflow": {"raw": 9.0e10},
            "financialCurrency": "USD",
        },
        key_stats={
            "netIncomeToCommon": {"raw": 9.9e10},
            "priceToBook": {"raw": 47.0},
            "mostRecentQuarter": {"raw": 1_711_929_600},  # 2024-04-01 UTC
        },
        summary={
            "trailingPE": {"raw": 31.2},
            "priceToSalesTrailing12Months": {"raw": 8.1},
            "dividendYield": {"raw": 0.0044},
        },
        price={"currency": "USD"},
    )
    provider = _provider(_ok_handler(payload))
    snap = await provider.get_fundamentals(Instrument("AAPL"))

    assert snap.provenance.tier is SourceTier.SECONDARY
    assert snap.provenance.source == "yahoo"
    assert provider.is_mock is False
    assert snap.revenue == pytest.approx(3.94e11)
    assert snap.net_margin == pytest.approx(0.25)
    # Yahoo's percent-form debt/equity is converted to a plain ratio.
    assert snap.debt_to_equity == pytest.approx(1.505)
    assert snap.pe_ratio == pytest.approx(31.2)
    assert snap.as_of is not None
    # A rich payload reports many of the metrics the scorer knows.
    assert snap.metric_count >= 12


@pytest.mark.asyncio
async def test_missing_lines_are_none_not_fabricated_zero():
    # Only revenue is reported; everything else must be honestly None.
    payload = _summary_payload(financial={"totalRevenue": {"raw": 1.0e9}})
    provider = _provider(_ok_handler(payload))
    snap = await provider.get_fundamentals(Instrument("AAPL"))

    assert snap.revenue == pytest.approx(1.0e9)
    assert snap.pe_ratio is None
    assert snap.debt_to_equity is None
    assert snap.dividend_yield is None
    assert snap.metric_count == 1


@pytest.mark.asyncio
async def test_empty_modules_is_an_honest_empty_snapshot_not_an_error():
    # A result that parses but carries no known lines is a legitimate honest
    # empty snapshot (the source had nothing), distinct from a failure.
    payload = _summary_payload()
    provider = _provider(_ok_handler(payload))
    snap = await provider.get_fundamentals(Instrument("AAPL"))
    assert snap.metric_count == 0
    assert snap.provenance.tier is SourceTier.SECONDARY


@pytest.mark.asyncio
async def test_maps_exchange_to_yahoo_suffix():
    captured: list[httpx.Request] = []
    payload = _summary_payload(financial={"totalRevenue": {"raw": 1.0}})
    provider = _provider(_ok_handler(payload, capture=captured))
    await provider.get_fundamentals(Instrument("RELIANCE", exchange="NSE"))
    assert captured, "no request captured"
    assert "RELIANCE.NS" in str(captured[0].url)


@pytest.mark.asyncio
async def test_http_error_becomes_fundamentals_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    provider = _provider(handler)
    with pytest.raises(FundamentalsError):
        await provider.get_fundamentals(Instrument("NOPE"))


@pytest.mark.asyncio
async def test_error_payload_becomes_fundamentals_error():
    payload = _summary_payload(
        error={"code": "Not Found", "description": "No fundamentals for symbol"},
    )
    provider = _provider(_ok_handler(payload))
    with pytest.raises(FundamentalsError):
        await provider.get_fundamentals(Instrument("NOPE"))


@pytest.mark.asyncio
async def test_empty_result_becomes_fundamentals_error():
    payload = _summary_payload(result_empty=True)
    provider = _provider(_ok_handler(payload))
    with pytest.raises(FundamentalsError):
        await provider.get_fundamentals(Instrument("AAPL"))


@pytest.mark.asyncio
async def test_network_error_becomes_fundamentals_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(handler)
    with pytest.raises(FundamentalsError):
        await provider.get_fundamentals(Instrument("AAPL"))
