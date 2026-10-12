"""
Market-intelligence service (Phase 4).

The composition point for the non-liquidity layer. It runs the existing
deterministic services over one candle series -- market structure, technical
indicators, price action, volume and regime -- tracks the 6-state regime across
successive reads (emitting ``MarketRegimeChanged`` only on a confirmed
transition), and distils everything into the canonical ``MarketFeatures``
vector.

It holds **no analytical logic of its own** -- it composes services and
analyzers, so it can never produce a number the underlying deterministic reads
didn't earn. These are evidence and features for the Signal Engine downstream,
never trading decisions; nothing here emits a BUY/SELL.

Determinism: the reads are pure functions of the series (and the prior regime
history the tracker carries). Feeding the same window of reads replays the same
transitions.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.market_data import MarketData
from ..domain.regime import RegimeAnalysis
from ..domain.structure import MarketStructure
from ..domain.technical import TechnicalSnapshot
from ..events import MarketRegimeChanged
from ..services.market_structure_service import MarketStructureService
from ..services.regime_service import RegimeService
from ..services.technical_analysis_service import TechnicalAnalysisService
from .features import MarketFeatures, extract_features
from .price_action import PriceActionAnalysis, PriceActionService
from .regime import RegimeTracker
from .volume import VolumeActionService, VolumeAnalysis2

logger = get_logger("trading.market_intel")


@dataclass(frozen=True, slots=True)
class MarketIntelReport:
    """The full non-liquidity read for one series: every sub-read + features."""

    structure: MarketStructure
    technical: TechnicalSnapshot
    price_action: PriceActionAnalysis
    volume: VolumeAnalysis2
    regime: RegimeAnalysis
    features: MarketFeatures

    def to_dict(self) -> dict:
        return {
            "structure": self.structure.to_dict(),
            "technical": self.technical.to_dict(),
            "price_action": self.price_action.to_dict(),
            "volume": self.volume.to_dict(),
            "regime": self.regime.to_dict(),
            "features": self.features.to_dict(),
        }


class MarketIntelService:
    """
    Composes the deterministic market reads + regime tracking for one series.

    The regime tracker is the stateful piece: it keeps a window of recent
    classified regimes so a ``MarketRegimeChanged`` is emitted only on a
    confirmed transition, never on a flicker. Everything else is a stateless,
    pure composition of the underlying services.
    """

    def __init__(
        self,
        *,
        settings=None,
        event_bus: EventBus | None = None,
        structure: MarketStructureService | None = None,
        technical: TechnicalAnalysisService | None = None,
        regime: RegimeService | None = None,
        price_action: PriceActionService | None = None,
        volume: VolumeActionService | None = None,
        regime_tracker: RegimeTracker | None = None,
    ) -> None:
        self._settings = settings
        self._event_bus = event_bus
        self._structure = structure or MarketStructureService()
        self._technical = technical or TechnicalAnalysisService()
        self._regime = regime or (
            RegimeService(settings) if settings is not None else None
        )
        self._price_action = price_action or PriceActionService()
        self._volume = volume or VolumeActionService()
        self._tracker = regime_tracker or RegimeTracker()

    async def analyze(self, data: MarketData) -> MarketIntelReport:
        """
        Run the full non-liquidity read over a candle series.

        Composes structure + technical + price action + volume + regime, feeds
        the regime read to the tracker (publishing ``MarketRegimeChanged`` on a
        confirmed transition), and distils all of it into ``MarketFeatures``.
        """
        structure = self._structure.analyze(data)
        technical = self._technical.compute(data)
        price_action = self._price_action.analyze(data)
        volume = self._volume.analyze(data)
        regime = (
            await self._regime.detect(data)
            if self._regime is not None
            else self._no_regime(data)
        )

        transition = self._tracker.update(regime)
        if transition is not None:
            await self._emit(transition)

        features = extract_features(
            symbol=data.instrument.key,
            timeframe=data.timeframe.value,
            structure=structure,
            technical=technical,
            price_action=price_action,
            volume=volume,
            regime=regime,
            is_mock=data.provenance.is_mock,
        )
        return MarketIntelReport(
            structure=structure,
            technical=technical,
            price_action=price_action,
            volume=volume,
            regime=regime,
            features=features,
        )

    @staticmethod
    def _no_regime(data: MarketData) -> RegimeAnalysis:
        """A regime read when no RegimeService is wired (honest UNKNOWN)."""
        from ..domain.enums import Confidence, MarketRegime
        return RegimeAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            regime=MarketRegime.UNKNOWN,
            adx=None,
            trend_strength=None,
            atr_pct=None,
            realized_volatility=None,
            confidence=Confidence.LOW,
            quality=data.quality,
            provenance=data.provenance,
            observation="No regime service wired; regime undetermined.",
            limitations=("RegimeService not configured.",),
        )

    async def _emit(self, transition) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                MarketRegimeChanged(
                    instrument_key=transition.instrument_key,
                    timeframe=transition.timeframe,
                    previous_regime=transition.previous.value,
                    regime=transition.current.value,
                    direction=transition.direction,
                    is_reliable=transition.is_reliable,
                    source_tier="mock" if transition.is_mock else "derived",
                )
            )
        except Exception:
            logger.exception("Failed to publish MarketRegimeChanged")
