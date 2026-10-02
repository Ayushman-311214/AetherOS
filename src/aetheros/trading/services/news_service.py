"""
News & sentiment service.

Fetches sourced headlines through an injected :class:`NewsProvider`, scores each
with the deterministic finance-lexicon classifier, and fuses them into a single
auditable :class:`NewsAnalysis` -- the net directional lean, the
positive/negative/neutral split, the NEWS/SENTIMENT :class:`Evidence` it yields,
and an honest ``is_reliable`` gate plus ``limitations`` (spec sections 5, 9, 26
item #9).

Every honesty discipline of the rest of the domain holds here: sentiment is a
derived interpretation of sourced text, never presented as the source's own
claim (section 15); a MOCK or empty feed can never masquerade as a real,
reliable signal (sections 2, 28, 61); and the classifier is deterministic, so
the same headlines always yield the same read. The service performs no LLM call
-- an LLM classifier is a future extension behind the same ``classify`` contract.
"""

from __future__ import annotations

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.enums import (
    Assertion,
    Confidence,
    DataQualityStatus,
    Direction,
    EvidenceType,
)
from ..domain.evidence import Evidence
from ..domain.instrument import Instrument
from ..domain.news import NewsAnalysis, NewsItem, ScoredNewsItem
from ..domain.provenance import DataQuality, Provenance
from ..errors import NewsError
from ..events import NewsSentimentAnalyzed
from ..news.sentiment import classify
from ..providers.news_base import NewsProvider

logger = get_logger("trading.news")

# Net-sentiment dead-band on the *mean* signed score: |mean| below this is
# SIDEWAYS (had news but no clear lean) rather than a weak directional call.
_DIRECTION_BAND = 0.15

_MOCK_LIMITATION = (
    "News sentiment rests on synthetic MOCK headlines (SourceTier.MOCK) — "
    "not real news. The read is illustrative only and is not reliable."
)


class NewsSentimentService:
    """Deterministic news-sentiment analysis for one instrument."""

    def __init__(
        self,
        provider: NewsProvider,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._event_bus = event_bus

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def is_mock(self) -> bool:
        return self._provider.is_mock

    async def analyze(
        self,
        symbol: str | Instrument,
        *,
        limit: int | None = None,
    ) -> NewsAnalysis:
        instrument = self._coerce_instrument(symbol)
        n = self._coerce_limit(limit)

        try:
            items = await self._provider.get_news(instrument, limit=n)
        except NewsError:
            raise
        except Exception as exc:  # provider misbehaved -> typed, honest error
            raise NewsError(
                f"News provider '{self._provider.name}' failed for "
                f"{instrument.key}.",
                context={"symbol": instrument.symbol},
                cause=exc,
            ) from exc

        analysis = self._analyze_items(instrument, items)
        await self._emit(analysis)
        return analysis

    # ------------------------------------------------------------------
    # Aggregation (pure, deterministic)
    # ------------------------------------------------------------------

    def _analyze_items(
        self, instrument: Instrument, items: tuple[NewsItem, ...]
    ) -> NewsAnalysis:
        is_mock = self._provider.is_mock
        tier = self._provider.tier
        provenance = Provenance(
            source=self._provider.name,
            tier=tier,
            detail="deterministic finance-lexicon sentiment over sourced headlines",
        )

        scored: list[ScoredNewsItem] = []
        positive = negative = neutral = 0
        score_sum = 0.0
        for item in items:
            read = classify(f"{item.headline} {item.summary}".strip())
            scored.append(
                ScoredNewsItem(
                    item=item,
                    direction=read.direction,
                    score=read.score,
                    confidence=read.confidence,
                    positive_terms=read.positive_terms,
                    negative_terms=read.negative_terms,
                )
            )
            score_sum += read.score
            if read.direction is Direction.UP:
                positive += 1
            elif read.direction is Direction.DOWN:
                negative += 1
            else:
                neutral += 1

        count = len(scored)
        min_items = self._settings.TRADING_NEWS_MIN_ITEMS

        # Quality: no news is MISSING (honest "no signal"), otherwise OK. Mock
        # feeds carry an explicit synthetic-data issue that propagates onward.
        issues: list[str] = []
        if is_mock:
            issues.append(_MOCK_LIMITATION)
        if count == 0:
            issues.append("No news found for the instrument.")
            status = DataQualityStatus.MISSING
        else:
            status = DataQualityStatus.OK
        quality = DataQuality(status=status, issues=tuple(issues), freshness_seconds=0.0)

        if count == 0:
            sentiment_score = 0.0
            direction = Direction.UNKNOWN
            confidence = Confidence.LOW
        else:
            sentiment_score = round(score_sum / count, 6)
            if sentiment_score >= _DIRECTION_BAND:
                direction = Direction.UP
            elif sentiment_score <= -_DIRECTION_BAND:
                direction = Direction.DOWN
            else:
                direction = Direction.SIDEWAYS
            # Thin coverage never earns more than LOW confidence, however
            # lopsided the lean looks.
            if count < min_items:
                confidence = Confidence.LOW
            else:
                confidence = Confidence.from_score(abs(sentiment_score))

        is_reliable = quality.usable and not is_mock and count >= min_items

        limitations = self._build_limitations(
            is_mock=is_mock, count=count, min_items=min_items, is_reliable=is_reliable
        )
        evidence = self._build_evidence(
            instrument=instrument,
            direction=direction,
            sentiment_score=sentiment_score,
            scored=tuple(scored),
            provenance=provenance,
            quality=quality,
        )

        return NewsAnalysis(
            instrument=instrument,
            items=tuple(scored),
            direction=direction,
            sentiment_score=sentiment_score,
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            confidence=confidence,
            evidence=evidence,
            provenance=provenance,
            quality=quality,
            is_reliable=is_reliable,
            limitations=limitations,
        )

    @staticmethod
    def _build_limitations(
        *, is_mock: bool, count: int, min_items: int, is_reliable: bool
    ) -> tuple[str, ...]:
        limitations: list[str] = []
        if is_mock:
            limitations.append(_MOCK_LIMITATION)
        if count == 0:
            limitations.append(
                "No news was found, so sentiment provides no signal here."
            )
        elif count < min_items:
            limitations.append(
                f"Only {count} headline(s) found (< {min_items}); the sentiment "
                f"read is too thin to be reliable."
            )
        if not is_reliable and not is_mock and count >= min_items:
            # Defensive: keep the honesty note present if some future gate flips.
            limitations.append("News sentiment is not reliable for this instrument.")
        return tuple(limitations)

    def _build_evidence(
        self,
        *,
        instrument: Instrument,
        direction: Direction,
        sentiment_score: float,
        scored: tuple[ScoredNewsItem, ...],
        provenance: Provenance,
        quality: DataQuality,
    ) -> tuple[Evidence, ...]:
        """
        Derive discrete Evidence from the sentiment read.

        An aggregate SENTIMENT claim captures the fused net lean; per-headline
        NEWS claims record each directional headline. All are soft evidence:
        weights are capped below the technical layer's, and a MOCK provenance
        keeps every item ``is_reliable == False``.
        """
        items: list[Evidence] = []

        if direction in (Direction.UP, Direction.DOWN):
            weight = round(min(0.6, 0.2 + abs(sentiment_score) * 0.5), 4)
            items.append(
                Evidence(
                    instrument_key=instrument.key,
                    type=EvidenceType.SENTIMENT,
                    assertion=Assertion.DETECTED,
                    direction=direction,
                    detail=(
                        f"Net news sentiment is {direction.value} "
                        f"(mean score {sentiment_score:+.2f} over {len(scored)} "
                        f"headlines)."
                    ),
                    weight=weight,
                    confidence=Confidence.from_score(weight),
                    provenance=provenance,
                    quality=quality,
                    data={"sentiment_score": sentiment_score, "items": len(scored)},
                )
            )

        for s in scored:
            if s.direction not in (Direction.UP, Direction.DOWN):
                continue
            weight = round(min(0.4, abs(s.score) * 0.4), 4)
            items.append(
                Evidence(
                    instrument_key=instrument.key,
                    type=EvidenceType.NEWS,
                    assertion=Assertion.DETECTED,
                    direction=s.direction,
                    detail=f"Headline reads {s.direction.value}: {s.item.headline}",
                    weight=weight,
                    confidence=Confidence.from_score(weight),
                    provenance=provenance,
                    quality=quality,
                    data={
                        "news_id": s.item.id,
                        "score": s.score,
                        "positive_terms": list(s.positive_terms),
                        "negative_terms": list(s.negative_terms),
                    },
                )
            )
        return tuple(items)

    # ------------------------------------------------------------------
    # Coercion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_instrument(symbol: str | Instrument) -> Instrument:
        if isinstance(symbol, Instrument):
            return symbol
        try:
            return Instrument.parse(symbol)
        except ValueError as exc:
            raise NewsError(str(exc), context={"symbol": symbol}) from exc

    def _coerce_limit(self, limit: int | None) -> int:
        max_items = self._settings.TRADING_NEWS_MAX_ITEMS
        if limit is None:
            return max_items
        if limit <= 0:
            raise NewsError(
                "limit must be a positive integer.", context={"limit": limit}
            )
        return min(limit, max_items)

    async def _emit(self, analysis: NewsAnalysis) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                NewsSentimentAnalyzed(
                    instrument_key=analysis.instrument.key,
                    direction=analysis.direction.value,
                    sentiment_score=analysis.sentiment_score,
                    confidence=analysis.confidence.value,
                    item_count=analysis.item_count,
                    positive_count=analysis.positive_count,
                    negative_count=analysis.negative_count,
                    neutral_count=analysis.neutral_count,
                    is_reliable=analysis.is_reliable,
                    source_tier=analysis.provenance.tier.value,
                )
            )
        except Exception:  # event delivery must never break analysis
            logger.exception("Failed to publish NewsSentimentAnalyzed")
