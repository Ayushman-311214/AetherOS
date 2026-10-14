"""
Hybrid chart-context assembly (spec Phase 19).

Builds the single unified :class:`HybridChartContext` the LLM reasons over:
the deterministic numerical read (market state, chart projection, technical
state, news, fundamentals) side by side with the visual read (screenshot
metadata, capabilities, observations, VISUAL evidence). It assembles; it
computes nothing -- every section is lifted verbatim from an already-produced
object, so there is one source of truth for every number and every read.

Provenance-weighted trust is structural, not advisory. The visual sections
arrive as UNCERTAIN observations/evidence with verbatim backend confidence
and fusion-capped weight (Phase 17); the context embeds the trust rules that
say so explicitly, and the cross-check reports agreement or conflict between
what the chart *shows* and what the API-derived analysis *measured* -- with
the numerical read governing whenever they disagree.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ...core.logging import get_logger
from ..domain.chart import ChartData
from ..domain.evidence import Evidence
from ..domain.hybrid import TRUST_RULES, HybridChartContext
from ..domain.report import TradingReport
from ..domain.visual import VisualObservation
from ..errors import TradingError
from .chart_service import ChartCaptureService, ChartService
from .market_data_service import MarketDataService
from .orchestration_service import OrchestrationService
from .visual_service import VisualObservationService

logger = get_logger("trading.hybrid")


class HybridContextService:
    """
    Fetch-and-assemble the numerical + visual context for one instrument.

    The pure :meth:`assemble` lifts already-produced objects; :meth:`build`
    is the single orchestration entry point that produces them -- report via
    the orchestrator, chart via the chart service, visual reads via the
    capture/vision subsystems -- and then assembles. Capture and vision are
    optional: ``capture`` is absent on a headless machine, and ``vision`` is
    a thunk (not a resolved service) so merely constructing this service
    never loads an OCR model -- resolution happens only inside an explicit
    visual attempt.
    """

    def __init__(
        self,
        orchestration: OrchestrationService,
        market_data: MarketDataService,
        charts: ChartService,
        visual: VisualObservationService,
        *,
        capture: ChartCaptureService | None = None,
        vision_factory: Callable[[], Any | None] | None = None,
    ) -> None:
        self._orchestration = orchestration
        self._market_data = market_data
        self._charts = charts
        self._visual = visual
        self._capture = capture
        self._vision_factory = vision_factory

    async def build(
        self,
        symbol: str,
        timeframe: str | None = None,
        *,
        limit: int | None = None,
        with_visual: bool = True,
        report: TradingReport | None = None,
    ) -> HybridChartContext:
        """
        Produce the unified context for one analysis request.

        Runs the deterministic report (unless one is supplied), projects the
        chart, attempts the visual read when asked, and assembles. Every
        visual failure -- no capture, no vision, a failed screenshot, an
        unreadable frame -- degrades to honest limitations inside
        ``visual_state``; it can never sink the numerical context.
        """
        if report is None:
            report = await self._orchestration.generate_report(
                symbol, timeframe, limit=limit
            )
        try:
            data = await self._market_data.get_candles(symbol, timeframe, limit=limit)
        except TradingError:
            logger.exception("Hybrid context proceeds without market candles")
            data = None
        chart: ChartData | None = None
        if data is not None:
            try:
                chart = self._charts.build_chart(data)
            except TradingError:
                logger.exception("Hybrid context proceeds without a chart")

        observations: tuple[VisualObservation, ...] = ()
        visual_evidence: tuple[Evidence, ...] = ()
        screenshot: dict[str, Any] | None = None
        capabilities: dict[str, bool] | None = None
        if with_visual and data is not None:
            try:
                observations, visual_evidence, screenshot, capabilities = (
                    await self._acquire_visual(data)
                )
            except Exception:
                logger.exception(
                    "Visual read failed; the hybrid context carries "
                    "numerical evidence alone"
                )

        return self.assemble(
            report,
            chart,
            observations,
            visual_evidence,
            screenshot=screenshot,
            capabilities=capabilities,
        )

    async def _acquire_visual(
        self, data: Any
    ) -> tuple[
        tuple[VisualObservation, ...],
        tuple[Evidence, ...],
        dict[str, Any] | None,
        dict[str, bool] | None,
    ]:
        """Capture, OCR/detect and translate -- or report honest absence."""
        vision = self._vision_factory() if self._vision_factory is not None else None
        if self._capture is None or vision is None:
            return (), (), None, None
        image, shot = await self._capture.capture_chart()
        capabilities = vision.capabilities()
        text_blocks: list = []
        detections: list = []
        if vision.has_ocr:
            try:
                text_blocks = await vision.read_text(image)
            except Exception:
                text_blocks = []
        if vision.has_detector:
            try:
                detections = await vision.detect_objects(image)
            except Exception:
                detections = []
        text_obs = self._visual.observe_text(
            text_blocks, instrument_key=data.instrument.key
        )
        object_obs = self._visual.observe_objects(
            detections, instrument_key=data.instrument.key
        )
        observations = text_obs + object_obs
        return observations, self._visual.to_evidence(observations, data), shot, capabilities

    @staticmethod
    def assemble(
        report: TradingReport,
        chart: ChartData | None,
        observations: tuple[VisualObservation, ...] = (),
        visual_evidence: tuple[Evidence, ...] = (),
        *,
        screenshot: dict[str, Any] | None = None,
        capabilities: dict[str, bool] | None = None,
    ) -> HybridChartContext:
        """
        Lift a finished report, chart projection and visual reads into one
        unified context.

        ``chart`` may be ``None`` (chart projection unavailable -- recorded as
        a limitation, never fabricated). An empty ``observations`` with no
        screenshot means no visual read was attempted or possible; that too is
        an honest limitation inside ``visual_state``, never a neutral vote.
        """
        payload = report.to_dict()
        limitations = list(report.limitations)

        chart_state: dict[str, Any] | None = None
        if chart is not None:
            chart_state = chart.to_dict()
        else:
            limitations.append(
                "No deterministic chart projection was available; the context "
                "carries the OHLCV-derived market state without a chart range."
            )

        visual_state: dict[str, Any] = {
            "screenshot": screenshot,
            "capabilities": capabilities,
            "observations": [obs.to_dict() for obs in observations],
            "evidence": [item.to_dict() for item in visual_evidence],
        }
        visual_limitations: list[str] = []
        if screenshot is None:
            visual_limitations.append(
                "No chart screenshot was captured; the context carries no "
                "visual read -- numerical evidence stands alone."
            )
        elif not observations or all(obs.kind == "empty" for obs in observations):
            visual_limitations.append(
                "Vision found nothing readable on the screenshot; the visual "
                "read is an honest empty, not evidence for or against the call."
            )
        visual_state["limitations"] = visual_limitations
        limitations.extend(f"Visual: {line}" for line in visual_limitations)

        cross_check = HybridContextService._cross_check(report, observations)
        visual_state["cross_check"] = cross_check
        if cross_check["conflict"] is not None:
            limitations.append(f"Visual/numerical conflict: {cross_check['conflict']}")

        technical_state = {
            key: payload[key]
            for key in (
                "signal",
                "technical",
                "structure",
                "volume",
                "key_levels",
                "market_regime",
                "relative_strength",
                "anomaly",
                "historical_analogue",
                "macro",
                "multi_timeframe",
                "divergence",
                "breakout",
            )
            if key in payload
        }
        news_state = {
            "news": payload.get("news"),
            "calendar": payload.get("calendar"),
        }
        metadata = {
            "recommendation": payload["recommendation"],
            "is_actionable": payload["is_actionable"],
            "critique": payload["critique"],
            "probability": payload["probability"],
            "risk": payload["risk"],
            "invalidation": payload["invalidation"],
            "horizon": payload["horizon"],
            "evidence": payload["evidence"],
            "backtest": payload["backtest"],
            "limitations": limitations,
            "provenance": payload["provenance"],
            "quality": payload["quality"],
            "model": payload["model"],
        }
        return HybridChartContext(
            instrument_key=report.instrument.key,
            timeframe=report.analysis.timeframe_value,
            market_state={
                "instrument": payload["instrument"],
                "timeframe": payload["timeframe"],
                "last_price": payload["last_price"],
                "quality": payload["quality"],
                "provenance": payload["provenance"],
            },
            chart_state=chart_state,
            technical_state=technical_state,
            visual_state=visual_state,
            news_state=news_state,
            fundamental_state=payload.get("fundamentals"),
            metadata=metadata,
            trust_rules=TRUST_RULES,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _cross_check(
        report: TradingReport,
        observations: tuple[VisualObservation, ...],
    ) -> dict[str, Any]:
        """
        Compare what the chart *shows* against what the analysis *measured*.

        Only a direct verbatim comparison is judged: whether any text read
        names the analysed instrument. A mismatch is a conflict (wrong chart
        on screen); a match is agreement. Price text is surfaced verbatim
        alongside the measured last price but never judged -- a screenshot
        may be stale, and a stale frame is not a contradiction. No text
        reads at all means no cross-check is possible.
        """
        texts = [obs for obs in observations if obs.kind == "text"]
        last_price = report.analysis.last_price
        result: dict[str, Any] = {
            "instrument_key": report.instrument.key,
            "measured_last_price": last_price,
            "visible_texts": [obs.label for obs in texts],
            "symbol_match": None,
            "conflict": None,
        }
        if not texts:
            return result
        symbol = report.instrument.symbol.upper()
        match = any(symbol in obs.label.upper() for obs in texts)
        result["symbol_match"] = match
        if not match:
            result["conflict"] = (
                f"None of the chart's visible text names '{symbol}'; the "
                "screenshot may show a different instrument, so the visual "
                "read must not support this analysis and the numerical read "
                "governs."
            )
        return result
