"""
Yahoo Finance news provider.

The first *real* news source in AetherOS, completing the real-data quartet
(market-data, fundamentals, calendar, news). It reads recent headlines for an
instrument from Yahoo's public ``/v1/finance/search`` endpoint over HTTPS, behind
the same :class:`NewsProvider` interface the mock uses, so the deterministic
lexicon classifier, the ``NewsSentimentService`` aggregate and the fused report
work unchanged -- but now on real, sourced headlines rather than a seeded
synthetic catalog (spec sections 5, 9, 26 item #9, 30).

Honesty guarantees (spec sections 9, 15, 20, 28, 61):

* It is ``SourceTier.SECONDARY``, never PRIMARY: Yahoo's search feed is a free,
  aggregated index, not the outlet's own wire, and the tier says so. It is never
  ``MOCK`` -- these are real headlines.
* It **never fabricates**. A network error, a non-200 response, a non-JSON body
  or an unexpected payload shape raises a typed :class:`NewsError`. It does not
  invent headlines.
* A headline is sourced text, never a sentiment claim (section 15): the provider
  returns the raw title/publisher/link/timestamp and lets the classifier derive
  any lean. An item Yahoo does not carry is simply absent, and an instrument with
  no headlines yields an empty tuple -- a legitimate honest "no news", not a
  failure.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..domain.enums import SourceTier
from ..domain.instrument import Instrument
from ..domain.news import NewsItem
from ..domain.provenance import Provenance
from ..errors import NewsError
from .news_base import NewsProvider
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

_SOURCE = "yahoo"


class YahooNewsProvider(NewsProvider):
    """Real recent headlines from Yahoo's public search endpoint."""

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

    async def _fetch_news(self, symbol: str, limit: int) -> list[dict]:
        url = f"{self._base_url}/v1/finance/search"
        params: dict[str, object] = {
            "q": symbol,
            "newsCount": limit,
            "quotesCount": 0,
            "enableFuzzyQuery": "false",
        }
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.get(url, params=params, headers=_HEADERS)
        except httpx.HTTPError as exc:
            raise NewsError(
                f"Yahoo news request failed for '{symbol}': {exc}",
                context={"symbol": symbol},
                cause=exc,
            ) from exc
        finally:
            if self._client is None:
                await client.aclose()

        if resp.status_code != 200:
            raise NewsError(
                f"Yahoo returned HTTP {resp.status_code} for '{symbol}'.",
                context={"symbol": symbol, "status": resp.status_code},
            )
        try:
            payload = resp.json()
        except ValueError as exc:
            raise NewsError(
                f"Yahoo returned a non-JSON response for '{symbol}'.",
                context={"symbol": symbol},
                cause=exc,
            ) from exc

        if not isinstance(payload, dict):
            raise NewsError(
                f"Unexpected Yahoo payload shape for '{symbol}'.",
                context={"symbol": symbol},
            )
        # The search endpoint always carries a "news" list; its absence or a
        # non-list value means the response is not what we expect -- an honest
        # error, distinct from an empty list (a legitimate "no news").
        news = payload.get("news")
        if not isinstance(news, list):
            raise NewsError(
                f"Yahoo payload for '{symbol}' has no news list.",
                context={"symbol": symbol},
            )
        return news

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _published_at(raw: object) -> datetime | None:
        """Convert Yahoo's ``providerPublishTime`` (unix seconds) to UTC."""
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None
        try:
            return datetime.fromtimestamp(int(raw), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Provider interface
    # ------------------------------------------------------------------

    async def get_news(
        self,
        instrument: Instrument,
        *,
        limit: int,
    ) -> tuple[NewsItem, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive.")

        symbol = self._yahoo_symbol(instrument)
        raw_items = await self._fetch_news(symbol, limit)

        provenance = Provenance(
            source=self.name,
            tier=self.tier,
            detail="Yahoo Finance search news",
        )

        items: list[NewsItem] = []
        seen: set[str] = set()
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            title = raw.get("title")
            # A headline with no title is not a usable item -- skip it rather
            # than fabricate text.
            if not isinstance(title, str) or not title.strip():
                continue
            publisher = raw.get("publisher")
            source = (
                publisher.strip()
                if isinstance(publisher, str) and publisher.strip()
                else _SOURCE
            )
            link = raw.get("link")
            url = link if isinstance(link, str) and link.strip() else None
            item = NewsItem(
                instrument_key=instrument.key,
                headline=title.strip(),
                source=source,
                provenance=provenance,
                summary="",
                url=url,
                published_at=self._published_at(raw.get("providerPublishTime")),
            )
            # The same story can appear twice in a search result; dedupe by the
            # content-addressed id (instrument|source|headline).
            if item.id in seen:
                continue
            seen.add(item.id)
            items.append(item)

        # Most-recent first; items without a timestamp sort last (stable).
        items.sort(
            key=lambda it: it.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return tuple(items[:limit])
