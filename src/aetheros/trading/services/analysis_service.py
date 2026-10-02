"""
Analysis service -- the deterministic orchestrator of the numerical core.

Given a symbol, it pulls candles (via MarketDataService), computes the
technical snapshot, market structure and volume read, asks the EvidenceService
to turn those into weighted claims, and *fuses* the claims into a single
directional lean with an honest confidence. It then packages everything into a
:class:`TradingAnalysis` and publishes AnalysisCompleted.

The fusion is a transparent weighted vote -- not a calibrated probability, and
never an LLM guess. Calibrated probabilities are a later quant-layer concern;
this layer's job is an auditable, evidence-grounded situation report. When the
data is unusable, mock, or the evidence is contradictory/empty, it says so and
returns Direction.UNKNOWN rather than manufacturing a signal (spec sections 28,
61).
"""

from __future__ import annotations

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.analysis import TradingAnalysis
from ..domain.enums import Confidence, Direction, SourceTier
from ..domain.evidence import Evidence
from ..domain.instrument import Instrument
from ..domain.market_data import MarketData
from ..domain.provenance import Provenance
from ..errors import InsufficientDataError
from ..events import AnalysisCompleted
from .evidence_service import EvidenceService
from .market_data_service import MarketDataService
from .market_structure_service import MarketStructureService
from .technical_analysis_service import TechnicalAnalysisService

logger = get_logger("trading.analysis")

# A net directional lean smaller than this in magnitude is read as SIDEWAYS.
_DIRECTION_THRESHOLD = 0.15


class AnalysisService:
    """Deterministic end-to-end analysis for one instrument."""

    def __init__(
        self,
        market_data: MarketDataService,
        technical: TechnicalAnalysisService,
        structure: MarketStructureService,
        evidence: EvidenceService,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._market_data = market_data
        self._technical = technical
        self._structure = structure
        self._evidence = evidence
        self._settings = settings
        self._event_bus = event_bus

    async def analyze(
        self,
        symbol: str | Instrument,
        timeframe: str | None = None,
        *,
        limit: int | None = None,
    ) -> TradingAnalysis:
        data = await self._market_data.get_candles(symbol, timeframe, limit=limit)
        return await self._analyze_data(data)

    async def analyze_data(
        self, data: MarketData, *, emit: bool = True
    ) -> TradingAnalysis:
        """
        Analyse an already-fetched :class:`MarketData` window.

        Exposed for callers that hold the data themselves -- notably the
        backtester, which slices a series into growing windows and must analyse
        each without re-fetching. ``emit=False`` suppresses AnalysisCompleted so
        a walk-forward run does not flood the event bus with one event per bar.
        """
        return await self._analyze_data(data, emit=emit)

    async def _analyze_data(
        self, data: MarketData, *, emit: bool = True
    ) -> TradingAnalysis:
        limitations: list[str] = []

        # Surface any data-quality problems as limitations from the start.
        if data.provenance.is_mock:
            limitations.append(
                "Analysis is based on synthetic MOCK data and is not a real "
                "market signal."
            )
        if not data.quality.ok:
            limitations.append(
                f"Data quality is '{data.quality.status.value}': "
                + "; ".join(data.quality.issues)
            )

        technical = self._technical.compute(data)
        structure = self._structure.analyze(data)
        volume = self._evidence.build_volume_analysis(data)
        evidence = self._evidence.build(
            data=data, technical=technical, structure=structure, volume=volume
        )

        direction, score, confidence = self._fuse(evidence, data)

        if not evidence:
            limitations.append("No directional evidence could be derived.")

        analysis = TradingAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            last_price=technical.last_price,
            direction=direction,
            directional_score=score,
            confidence=confidence,
            technical=technical,
            structure=structure,
            evidence=evidence,
            volume=volume,
            quality=data.quality,
            provenance=Provenance(
                source=data.provenance.source,
                tier=SourceTier.MOCK if data.provenance.is_mock else SourceTier.DERIVED,
                detail="deterministic evidence-fusion analysis",
            ),
            limitations=tuple(limitations),
        )

        if emit:
            await self._emit_completed(analysis)
        return analysis

    # ------------------------------------------------------------------

    def _fuse(
        self, evidence: tuple[Evidence, ...], data: MarketData
    ) -> tuple[Direction, float, Confidence]:
        """
        Transparent weighted vote over directional evidence.

        Returns (direction, signed_score in [-1,1], confidence). Evidence with
        UNKNOWN direction (e.g. volume participation) contributes to confidence
        via corroboration but not to the directional sign.
        """
        # If the data is not usable at all, there is no honest direction.
        if not data.quality.usable or not evidence:
            return Direction.UNKNOWN, 0.0, Confidence.LOW

        up = sum(e.weight for e in evidence if e.direction is Direction.UP)
        down = sum(e.weight for e in evidence if e.direction is Direction.DOWN)
        total = up + down

        if total <= 0:
            return Direction.SIDEWAYS, 0.0, Confidence.LOW

        score = (up - down) / total  # signed, in [-1, 1]

        if score > _DIRECTION_THRESHOLD:
            direction = Direction.UP
        elif score < -_DIRECTION_THRESHOLD:
            direction = Direction.DOWN
        else:
            direction = Direction.SIDEWAYS

        confidence = self._confidence(score, evidence, data)
        return direction, round(score, 4), confidence

    @staticmethod
    def _confidence(
        score: float, evidence: tuple[Evidence, ...], data: MarketData
    ) -> Confidence:
        # Base confidence on agreement strength and evidence count.
        magnitude = abs(score)
        breadth = min(1.0, len(evidence) / 6.0)
        base = 0.5 * magnitude + 0.5 * breadth

        # Penalise anything that undermines trust in the inputs.
        if data.provenance.is_mock:
            base *= 0.4
        if not data.quality.ok:
            base *= 0.6

        return Confidence.from_score(base)

    async def _emit_completed(self, analysis: TradingAnalysis) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                AnalysisCompleted(
                    instrument_key=analysis.instrument.key,
                    timeframe=analysis.timeframe_value,
                    direction=analysis.direction.value,
                    confidence=analysis.confidence.value,
                    directional_score=analysis.directional_score,
                    is_actionable=analysis.is_actionable,
                    evidence_count=len(analysis.evidence),
                    source_tier=analysis.provenance.tier.value,
                )
            )
        except Exception:
            logger.exception("Failed to publish AnalysisCompleted")
