"""
Yahoo Finance fundamentals provider.

The first *real* fundamentals source in AetherOS. It reads the latest reported
company financials from Yahoo's public ``quoteSummary`` endpoint over HTTPS,
behind the same :class:`FundamentalsProvider` interface the mock uses, so the
scoring and analysis layers work unchanged -- but now on real, sourced figures
rather than seeded synthetic ones (spec sections 1, 9, 30: reliable data is the
priority, data matters more than the LLM).

Honesty guarantees (spec sections 9, 20, 28, 61):

* It is ``SourceTier.SECONDARY``, never PRIMARY: Yahoo is a free, aggregated
  feed, not an audited filing, and the tier says so. It is never ``MOCK`` --
  these are real numbers.
* It **never fabricates**. A network error, a non-200 response, an error object
  in the payload, or a missing result raises a typed :class:`FundamentalsError`.
  It does not fall back to synthetic data.
* Any line Yahoo does not report is left ``None`` on the snapshot -- an absent
  metric is honestly absent, never a fabricated zero. A result that parses but
  reports no metrics is a legitimate honest empty snapshot (the source had
  nothing), distinct from a failure, exactly as the interface specifies.
* It does not interpret: it returns the sourced figures and lets the
  FundamentalAnalysisService derive any opinion. The one arithmetic conversion
  it makes is documented at the field (Yahoo's percent-form debt/equity).
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..domain.enums import SourceTier
from ..domain.fundamentals import FundamentalSnapshot
from ..domain.instrument import Instrument
from ..domain.provenance import Provenance
from ..errors import FundamentalsError
from .fundamentals_base import FundamentalsProvider
from .yahoo_provider import _EXCHANGE_SUFFIX  # single source of truth for suffixes

_DEFAULT_BASE_URL = "https://query1.finance.yahoo.com"

# A browser-like User-Agent: the public endpoint rejects some default clients.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# The quoteSummary modules that carry the lines the scorer knows how to read.
_MODULES = "financialData,defaultKeyStatistics,summaryDetail,price"


class YahooFundamentalsProvider(FundamentalsProvider):
    """Real reported financials from Yahoo's public quoteSummary endpoint."""

    name = "yahoo"
    tier = SourceTier.SECONDARY

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ) -> None:
        # An injected client (owned by the caller) makes this provider testable
        # with httpx.MockTransport and lets a host share one connection pool. If
        # none is given we open and close a client per request.
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Symbol mapping (shares the market provider's exchange suffix table)
    # ------------------------------------------------------------------

    @staticmethod
    def _yahoo_symbol(instrument: Instrument) -> str:
        suffix = ""
        if instrument.exchange:
            suffix = _EXCHANGE_SUFFIX.get(instrument.exchange, "")
        return f"{instrument.symbol}{suffix}"

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    async def _fetch_summary(self, symbol: str) -> dict:
        url = f"{self._base_url}/v10/finance/quoteSummary/{symbol}"
        params: dict[str, object] = {"modules": _MODULES}
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.get(url, params=params, headers=_HEADERS)
        except httpx.HTTPError as exc:
            raise FundamentalsError(
                f"Yahoo fundamentals request failed for '{symbol}': {exc}",
                context={"symbol": symbol},
                cause=exc,
            ) from exc
        finally:
            if self._client is None:
                await client.aclose()

        if resp.status_code != 200:
            raise FundamentalsError(
                f"Yahoo returned HTTP {resp.status_code} for '{symbol}'.",
                context={"symbol": symbol, "status": resp.status_code},
            )
        try:
            payload = resp.json()
        except ValueError as exc:
            raise FundamentalsError(
                f"Yahoo returned a non-JSON response for '{symbol}'.",
                context={"symbol": symbol},
                cause=exc,
            ) from exc

        summary = payload.get("quoteSummary") if isinstance(payload, dict) else None
        if not isinstance(summary, dict):
            raise FundamentalsError(
                f"Unexpected Yahoo payload shape for '{symbol}'.",
                context={"symbol": symbol},
            )
        error = summary.get("error")
        if error:
            desc = error.get("description") if isinstance(error, dict) else error
            raise FundamentalsError(
                f"Yahoo reported an error for '{symbol}': {desc}",
                context={"symbol": symbol},
            )
        results = summary.get("result")
        if not results:
            raise FundamentalsError(
                f"Yahoo returned no fundamentals for '{symbol}'.",
                context={"symbol": symbol},
            )
        return results[0]

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _raw(block: dict, key: str) -> float | None:
        """
        Read one numeric line from a quoteSummary module.

        Yahoo wraps numbers as ``{"raw": 1.23, "fmt": "1.23"}``; a missing or
        non-numeric line yields ``None`` (honestly absent, never a fabricated
        zero). A bare number is also accepted for robustness.
        """
        value = block.get(key)
        if isinstance(value, dict):
            value = value.get("raw")
        if isinstance(value, bool):  # guard: bool is an int subclass
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    # ------------------------------------------------------------------
    # Provider interface
    # ------------------------------------------------------------------

    async def get_fundamentals(
        self,
        instrument: Instrument,
    ) -> FundamentalSnapshot:
        symbol = self._yahoo_symbol(instrument)
        result = await self._fetch_summary(symbol)

        financial = result.get("financialData") or {}
        key_stats = result.get("defaultKeyStatistics") or {}
        summary = result.get("summaryDetail") or {}
        price = result.get("price") or {}

        # Currency: prefer the financial-statements currency, then the quote's.
        currency = (
            financial.get("financialCurrency")
            or price.get("currency")
            or "USD"
        )
        if not isinstance(currency, str):
            currency = "USD"

        # Reporting-period end: Yahoo gives the most-recent quarter as a unix ts.
        as_of: datetime | None = None
        mrq = self._raw(key_stats, "mostRecentQuarter")
        if mrq is not None:
            try:
                as_of = datetime.fromtimestamp(int(mrq), tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                as_of = None

        # Yahoo reports debt/equity in percent form (e.g. 150.5 == 1.505x); the
        # domain and every other provider carry it as a plain ratio, so convert.
        d_to_e = self._raw(financial, "debtToEquity")
        if d_to_e is not None:
            d_to_e = round(d_to_e / 100.0, 4)

        return FundamentalSnapshot(
            instrument_key=instrument.key,
            provenance=Provenance(
                source=self.name,
                tier=self.tier,
                detail="Yahoo Finance quoteSummary",
            ),
            currency=currency,
            as_of=as_of,
            # Profitability (Yahoo margins are already fractions)
            revenue=self._raw(financial, "totalRevenue"),
            net_income=self._raw(key_stats, "netIncomeToCommon"),
            gross_margin=self._raw(financial, "grossMargins"),
            operating_margin=self._raw(financial, "operatingMargins"),
            net_margin=self._raw(financial, "profitMargins"),
            # Growth (fractions)
            revenue_growth_yoy=self._raw(financial, "revenueGrowth"),
            earnings_growth_yoy=self._raw(financial, "earningsGrowth"),
            return_on_equity=self._raw(financial, "returnOnEquity"),
            # Balance-sheet health
            debt_to_equity=d_to_e,
            current_ratio=self._raw(financial, "currentRatio"),
            free_cash_flow=self._raw(financial, "freeCashflow"),
            # Valuation
            pe_ratio=self._raw(summary, "trailingPE"),
            pb_ratio=self._raw(key_stats, "priceToBook"),
            price_to_sales=self._raw(summary, "priceToSalesTrailing12Months"),
            dividend_yield=self._raw(summary, "dividendYield"),
        )
