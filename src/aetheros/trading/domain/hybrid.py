"""
Hybrid chart context value object (spec Phase 19).

A :class:`HybridChartContext` is the single unified Trading Intelligence
context for one instrument: the deterministic numerical read (market state,
chart projection, technical state) side by side with the visual read (chart
screenshot metadata plus vision observations), plus the news and fundamental
states and a metadata envelope. It is what the LLM receives when it must
reason over BOTH numbers and pictures.

It assembles; it computes nothing. Every section is lifted verbatim from an
already-produced object (a :class:`TradingReport`, a ``ChartData``, vision
observations/evidence), so there is a single source of truth for every number
and every read. The context carries the provenance-weighted trust rules with
it (``trust_rules``): a visual guess is UNCERTAIN, confidence verbatim, weight
capped below any API-derived number -- never equal to a measured fact. When
visual and numerical conflict, the conflict is reported and the numerical
read governs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(UTC)


#: Provenance-weighted trust rules shipped inside every hybrid context, so any
#: LLM receiving the payload inherits the weighting without needing a
#: separate prompt. Visual reads stay guesses; API-derived numbers stay facts.
TRUST_RULES: tuple[str, ...] = (
    "Numerical sections (market, technical, news, fundamental) are "
    "API-derived facts with their own provenance and reliability flags; "
    "trust them first.",
    "Visual observations are UNCERTAIN reads with verbatim backend "
    "confidence, weighted below any API-derived number; never treat a "
    "visual guess as equal to a measured fact.",
    "When visual and numerical reads conflict, report the conflict "
    "explicitly and let the numerical read govern.",
    "A missing section (null with a limitation) is honest absence of "
    "evidence, never a neutral vote.",
)


@dataclass(frozen=True, slots=True)
class HybridChartContext:
    """
    One unified numerical + visual context for a single instrument.

    ``market_state`` is the OHLCV-derived identity (instrument, timeframe,
    last price, quality, provenance). ``chart_state`` is the deterministic
    chart projection (ranges plus a recent-point tail). ``technical_state``
    bundles signal, technicals, structure, volume, key levels and regime.
    ``visual_state`` carries the screenshot metadata, vision capabilities,
    observations and VISUAL evidence -- or honest limitations when no
    screenshot was taken. ``news_state`` and ``fundamental_state`` are the
    advisory layers verbatim. ``metadata`` is the decision envelope
    (recommendation, direction, actionability, verdict, limitations,
    provenance, pipeline version).
    """

    instrument_key: str
    timeframe: str
    market_state: dict[str, Any]
    chart_state: dict[str, Any] | None
    technical_state: dict[str, Any]
    visual_state: dict[str, Any]
    news_state: dict[str, Any]
    fundamental_state: dict[str, Any] | None
    metadata: dict[str, Any]
    trust_rules: tuple[str, ...] = TRUST_RULES
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "market_state": self.market_state,
            "chart_state": self.chart_state,
            "technical_state": self.technical_state,
            "visual_state": self.visual_state,
            "news_state": self.news_state,
            "fundamental_state": self.fundamental_state,
            "metadata": self.metadata,
            "trust_rules": list(self.trust_rules),
            "created_at": self.created_at.isoformat(),
        }
