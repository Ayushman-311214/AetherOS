"""
Chart services: deterministic chart projection, annotation and sync, plus
screenshot capture delegated to the existing screen infrastructure.

The chart engine owns *no* pixels: :class:`ChartService` turns candle series
into the domain's :class:`~aetheros.trading.domain.chart.ChartData` (pure
maths, no I/O), and :class:`ChartCaptureService` wraps the desktop
subsystem's :class:`~aetheros.desktop.screen.controller.ScreenService` to
capture a chart region as a vision :class:`~aetheros.vision.image.Image` --
exactly the Interface -> Backend -> Service -> Tool layering CLAUDE.md
sections 12/14 prescribe. A headless machine (no ScreenService registered)
gets a typed, honest error rather than a fabricated frame.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from ...core.logging import get_logger
from ...desktop.screen.controller import ScreenService
from ...vision.image import Image
from ..domain.chart import (
    ChartAnnotation,
    ChartData,
    ChartPoint,
    ChartState,
)
from ..domain.market_data import MarketData
from ..errors import AnalysisError, InsufficientDataError, TradingError

logger = get_logger("trading.charts")


class ChartService:
    """Pure, deterministic chart operations over MarketData windows."""

    def build_chart(self, data: MarketData) -> ChartData:
        """Project a candle series into renderable ChartData."""
        if not data.candles:
            raise InsufficientDataError(
                "Cannot build a chart from an empty candle series.",
                context={"instrument": data.instrument.key},
            )
        points = tuple(
            ChartPoint(
                timestamp=c.timestamp,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
            )
            for c in data.candles
        )
        return ChartData(
            instrument=data.instrument,
            timeframe=data.timeframe,
            points=points,
            provenance=data.provenance,
        )

    def slice_chart(
        self, data: MarketData, start: datetime, end: datetime
    ) -> ChartData:
        """
        Build the chart restricted to the visible window ``[start, end]``.

        Bars whose open time falls inside the window are kept; the window is
        inclusive on both ends. An empty result raises InsufficientDataError
        rather than producing a chart with no points.
        """
        chart = self.build_chart(data)
        points = tuple(
            p for p in chart.points if start <= p.timestamp <= end
        )
        if not points:
            raise InsufficientDataError(
                "The requested window contains no candles.",
                context={
                    "instrument": data.instrument.key,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
            )
        return ChartData(
            instrument=chart.instrument,
            timeframe=chart.timeframe,
            points=points,
            provenance=chart.provenance,
        )

    def add_annotation(
        self, state: ChartState, annotation: ChartAnnotation
    ) -> ChartState:
        """
        Derive a new chart state carrying one more annotation.

        Immutable models: the input state is untouched and a fresh state is
        returned with a bumped ``updated_at``.
        """
        import dataclasses

        return dataclasses.replace(
            state,
            annotations=state.annotations + (annotation,),
            updated_at=datetime.now(UTC),
        )

    def synchronize(
        self, series: Mapping[str, MarketData]
    ) -> dict[str, dict[str, Any]]:
        """
        Align several charts onto their common time window.

        Each series is trimmed to the intersection of all series' time ranges
        (by open-timestamp). A series with no overlap is reported with an
        empty window and a limitation rather than fabricated alignment. The
        result maps each key to the trimmed ChartData plus sync metadata.
        """
        if not series:
            return {}

        usable = {k: v for k, v in series.items() if v.candles}
        limitations: list[str] = []
        for key, value in series.items():
            if not value.candles:
                limitations.append(f"{key}: no candles, excluded from sync.")
        if not usable:
            return {
                key: {"chart": None, "synced": False, "limitation": "no data"}
                for key in series
            }

        start = max(v.candles[0].timestamp for v in usable.values())
        end = min(v.candles[-1].timestamp for v in usable.values())

        result: dict[str, dict[str, Any]] = {}
        any_overlap = False
        for key, value in series.items():
            if not value.candles:
                result[key] = {
                    "chart": None,
                    "synced": False,
                    "limitation": "empty series",
                }
                continue
            points = tuple(
                ChartPoint(
                    timestamp=c.timestamp,
                    open=c.open,
                    high=c.high,
                    low=c.low,
                    close=c.close,
                    volume=c.volume,
                )
                for c in value.candles
                if start <= c.timestamp <= end
            )
            if points:
                any_overlap = True
                result[key] = {
                    "chart": ChartData(
                        instrument=value.instrument,
                        timeframe=value.timeframe,
                        points=points,
                        provenance=value.provenance,
                    ),
                    "synced": True,
                    "window": {
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    },
                }
            else:
                note = (
                    f"no overlap with the common window "
                    f"[{start.isoformat()} .. {end.isoformat()}]"
                )
                limitations.append(f"{key}: {note}")
                result[key] = {
                    "chart": None,
                    "synced": False,
                    "limitation": note,
                }

        if not any_overlap:
            # The common window exists but contains no bars from any series
            # (e.g. daily vs weekly grids that never coincide). Report it
            # honestly rather than claiming alignment.
            for key in result:
                if result[key]["synced"]:
                    result[key] = {
                        "chart": None,
                        "synced": False,
                        "limitation": "common window contains no shared bars",
                    }
        return result


class ChartCaptureService:
    """
    Chart screenshots through the desktop screen infrastructure.

    Owns no capture logic of its own: ``capture`` and ``capture_region`` are
    delegated wholesale to the injected :class:`ScreenService`, and the frame
    is wrapped in the vision subsystem's validated :class:`Image` so it can
    flow directly into OCR/detection later (Phase 17/18). A missing or failed
    capture raises a typed error -- never a fabricated frame.
    """

    def __init__(self, screen: ScreenService) -> None:
        self._screen = screen
        self._logger = get_logger("trading.chart_capture")

    async def capture_chart(
        self,
        *,
        left: int | None = None,
        top: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[Image, dict[str, Any]]:
        """Capture the full screen or a region as a chart screenshot."""
        region: tuple[int, int, int, int] | None = None
        if (left, top, width, height) != (None, None, None, None):
            if None in (left, top, width, height):
                raise TradingError(
                    "A chart region needs all four of left, top, width, height.",
                    context={"left": left, "top": top, "width": width, "height": height},
                )
            if width <= 0 or height <= 0:
                raise TradingError(
                    "Chart region dimensions must be positive.",
                    context={"width": width, "height": height},
                )
            region = (int(left), int(top), int(width), int(height))  # type: ignore[arg-type]

        try:
            if region is None:
                frame = await self._screen.capture()
            else:
                frame = await self._screen.capture_region(*region)
        except Exception as exc:
            raise AnalysisError(
                f"Chart screenshot capture failed: {exc}",
                cause=exc,
            ) from exc

        if frame is None or frame.size == 0:
            raise AnalysisError("Chart screenshot capture returned an empty frame.")

        height_px, width_px = frame.shape[:2]
        image = Image.from_numpy(frame)
        metadata: dict[str, Any] = {
            "source": "screen",
            "width": int(width_px),
            "height": int(height_px),
            "color_space": image.color_space,
            "captured_at": datetime.now(UTC).isoformat(),
        }
        if region is not None:
            metadata["region"] = {
                "left": region[0],
                "top": region[1],
                "width": region[2],
                "height": region[3],
            }
        self._logger.bind(
            width=width_px,
            height=height_px,
            region=region is not None,
        ).debug("Chart screenshot captured.")
        return image, metadata

    async def save_screenshot(
        self,
        *,
        left: int | None = None,
        top: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> dict[str, Any]:
        """Capture and return metadata only (pixels stay in memory)."""
        _image, metadata = await self.capture_chart(
            left=left, top=top, width=width, height=height
        )
        return metadata
