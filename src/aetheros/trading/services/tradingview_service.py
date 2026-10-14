"""
TradingView chart adapter (spec Phase 18).

Opens TradingView charts, selects symbols and timeframes, captures the
rendered frame and reads back what the chart shows -- through the existing
AetherOS automation, never around it:

* navigation via ``BrowserService`` (goto the chart URL; the DOM path),
* symbol/timeframe entry via keyboard (the same keys a trader presses),
* element targeting via the vision grounding engine (natural-language target
  -> screen coordinates) with mouse actuation only through the grounded point,
* frame capture via ``ChartCaptureService`` (the Phase 3 screen seam),
* state reading via ``VisionService`` OCR over the captured frame.

The adapter owns no automation logic of its own: every actuation delegates to
an injected service, every dependency is optional, and every method degrades
to an honest typed error when its subsystem is absent. Coordinates are never
hardcoded -- the only geometry is what grounding returns for the live frame,
and a grounding result that is not ``safe_to_act`` is reported, never clicked.

Trading Intelligence consumes the returned :class:`TradingViewChartState`
(plus the screenshot the capture service already provides); it never touches
a browser, a mouse, or a pixel through this module.
"""

from __future__ import annotations

from typing import Any

from ...core.logging import get_logger
from ..domain.tradingview import TradingViewChartState, chart_url
from ..errors import TradingError

logger = get_logger("trading.tradingview")

#: TradingView's interval shortcuts, as typed into the chart. The adapter sends
#: these as keystrokes after focusing the chart -- the same input a trader uses.
TIMEFRAME_KEYS: dict[str, str] = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
    "1d": "D",
    "1w": "W",
    "1M": "M",
}


class TradingViewAdapter:
    """
    TradingView chart interaction through existing AetherOS subsystems.

    All collaborators are optional and injected: ``browser`` (navigation),
    ``keyboard`` (symbol/timeframe entry), ``screen`` (frame capture via the
    chart-capture service shape), ``vision`` (OCR state reading), ``grounding``
    (visual element targeting), ``mouse`` (grounded clicks only). A method
    whose subsystem is missing raises :class:`TradingError` naming it -- never
    a fabricated state.
    """

    def __init__(
        self,
        *,
        browser: Any | None = None,
        keyboard: Any | None = None,
        mouse: Any | None = None,
        screen: Any | None = None,
        vision: Any | None = None,
        grounding: Any | None = None,
    ) -> None:
        self._browser = browser
        self._keyboard = keyboard
        self._mouse = mouse
        self._screen = screen
        self._vision = vision
        self._grounding = grounding

    # ------------------------------------------------------------------
    # Chart lifecycle
    # ------------------------------------------------------------------

    async def open_chart(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
    ) -> dict[str, Any]:
        """
        Navigate the browser to the TradingView chart for ``symbol``.

        Returns the URL navigated to plus the page title/URL read back --
        the observable proof the right chart loaded, not an assumption.
        """
        if self._browser is None:
            raise TradingError(
                "Cannot open a TradingView chart: no browser service is wired.",
            )
        url = chart_url(symbol, exchange)
        await self._browser.goto(url)
        await self._browser.wait_for_load()
        return {
            "url": url,
            "page_url": await self._browser.url(),
            "page_title": await self._browser.title(),
        }

    async def select_symbol(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
    ) -> dict[str, Any]:
        """
        Focus the chart and type the symbol (the trader's own input path).

        Re-navigating to the symbol URL is the deterministic route; typing is
        reserved for the in-chart symbol dialog when a browser context already
        shows a chart. This method takes the deterministic route.
        """
        return await self.open_chart(symbol, exchange=exchange)

    async def select_timeframe(self, timeframe: str) -> dict[str, Any]:
        """
        Send the TradingView interval shortcut for ``timeframe``.

        Requires the keyboard service and a focused chart. An unknown
        timeframe is refused rather than approximated -- sending the wrong
        keys would silently show the wrong bars.
        """
        if self._keyboard is None:
            raise TradingError(
                "Cannot select a timeframe: no keyboard service is wired.",
            )
        keys = TIMEFRAME_KEYS.get(timeframe.strip())
        if keys is None:
            raise TradingError(
                f"Unknown TradingView timeframe '{timeframe}'. Supported: "
                f"{', '.join(sorted(TIMEFRAME_KEYS))}.",
                context={"timeframe": timeframe},
            )
        await self._keyboard.write(keys)
        await self._keyboard.press("enter")
        return {"timeframe": timeframe, "keys_sent": keys}

    # ------------------------------------------------------------------
    # Capture + state
    # ------------------------------------------------------------------

    async def capture_chart(
        self,
        *,
        left: int | None = None,
        top: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        """
        Capture the chart frame through the injected screen service.

        Returns the vision ``Image`` and its metadata, exactly as
        :class:`ChartCaptureService` does -- this adapter reuses that shape
        so the frame flows into OCR/detection unchanged.
        """
        if self._screen is None:
            raise TradingError(
                "Cannot capture a chart: no screen service is wired.",
            )
        from ...vision.image import Image

        if (left, top, width, height) != (None, None, None, None):
            if None in (left, top, width, height):
                raise TradingError(
                    "A chart region needs all four of left, top, width, height.",
                )
            frame = await self._screen.capture_region(left, top, width, height)
        else:
            frame = await self._screen.capture()
        if frame is None or frame.size == 0:
            raise TradingError("Chart screenshot capture returned an empty frame.")
        image = Image.from_numpy(frame)
        height_px, width_px = frame.shape[:2]
        metadata: dict[str, Any] = {
            "source": "screen",
            "width": int(width_px),
            "height": int(height_px),
            "color_space": image.color_space,
        }
        return image, metadata

    async def read_chart_state(
        self,
        symbol: str,
        timeframe: str,
        *,
        image: Any | None = None,
    ) -> TradingViewChartState:
        """
        Read what the chart shows: page identity plus vision-read text.

        When ``image`` is not supplied the screen is captured first. OCR runs
        only when the vision service is wired and reports ``has_ocr``;
        otherwise the visible fields stay ``None`` with a limitation -- never
        guessed. The first text blocks are reported verbatim (symbol /
        timeframe / price slots take the first three non-empty reads); deeper
        interpretation is Phase 19's hybrid context, not this adapter.
        """
        limitations: list[str] = []
        page_url, page_title = "", ""
        if self._browser is not None:
            try:
                page_url = await self._browser.url()
                page_title = await self._browser.title()
            except Exception as exc:
                limitations.append(f"Could not read page identity: {type(exc).__name__}.")

        frame = image
        if frame is None:
            try:
                frame, _shot = await self.capture_chart()
            except TradingError as exc:
                limitations.append(str(exc.args[0]) if exc.args else "Capture failed.")
                frame = None

        visible_symbol, visible_timeframe, visible_price = None, None, None
        if frame is not None and self._vision is not None and self._vision.has_ocr:
            try:
                blocks = await self._vision.read_text(frame)
                texts = [b.text.strip() for b in blocks if b.text.strip()]
                if texts:
                    visible_symbol = texts[0] if len(texts) > 0 else None
                    visible_timeframe = texts[1] if len(texts) > 1 else None
                    visible_price = texts[2] if len(texts) > 2 else None
                else:
                    limitations.append("OCR found no readable text on the chart.")
            except Exception as exc:
                limitations.append(f"OCR failed: {type(exc).__name__}.")
        elif frame is not None:
            limitations.append("Vision OCR is unavailable; chart text not read.")

        return TradingViewChartState(
            requested_symbol=symbol,
            requested_timeframe=timeframe,
            page_url=page_url,
            page_title=page_title,
            visible_symbol=visible_symbol,
            visible_timeframe=visible_timeframe,
            visible_price=visible_price,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------
    # Grounded interaction (no hardcoded coordinates)
    # ------------------------------------------------------------------

    async def click_target(self, description: str, image: Any) -> dict[str, Any]:
        """
        Click what ``description`` names, located by visual grounding.

        The grounding engine resolves the phrase against the live frame; only
        a ``safe_to_act`` result is clicked, through the injected mouse, at
        the grounded point. Anything else -- no match, ambiguity, low
        confidence, no grounding/mouse service -- is returned as an honest
        refusal, never a blind click at a guessed coordinate.
        """
        if self._grounding is None:
            raise TradingError(
                "Cannot ground a target: no grounding engine is wired.",
            )
        if self._mouse is None:
            raise TradingError(
                "Cannot click a target: no mouse service is wired.",
            )
        result = await self._grounding.ground(description, image)
        if not result.success:
            return {
                "clicked": False,
                "reason": result.reason,
                "confidence": result.confidence,
            }
        if not result.safe_to_act:
            return {
                "clicked": False,
                "reason": (
                    "Match is not safe to act on "
                    f"(band {result.confidence_band}, "
                    f"confidence {result.confidence:.2f})."
                ),
                "confidence": result.confidence,
            }
        x, y = result.center
        await self._mouse.click(x, y)
        return {
            "clicked": True,
            "x": x,
            "y": y,
            "confidence": result.confidence,
            "confidence_band": result.confidence_band,
        }
