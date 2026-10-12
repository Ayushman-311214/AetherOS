"""
TradingView adapter: chart interaction decoupled from Trading Intelligence
(Phase 18).

Every collaborator is stubbed -- no browser, no display, no models. The tests
pin the adapter's contract: URL conventions, honest degradation when a
subsystem is missing, timeframe-key mapping, grounding-gated clicks (never a
blind coordinate), and state reading that reports what vision found without
guessing the rest.
"""

from __future__ import annotations

import numpy as np
import pytest

from aetheros.trading.domain.tradingview import (
    TRADINGVIEW_BASE_URL,
    TradingViewChartState,
    chart_url,
)
from aetheros.trading.errors import TradingError
from aetheros.trading.services.tradingview_service import (
    TIMEFRAME_KEYS,
    TradingViewAdapter,
)
from aetheros.vision.models import TextBlock

# ==============================================================
# Stubs (no browser, display, or models)
# ==============================================================


class StubBrowser:
    def __init__(self) -> None:
        self.visited: list[str] = []

    async def goto(self, url: str) -> None:
        self.visited.append(url)

    async def wait_for_load(self) -> None:
        return None

    async def url(self) -> str:
        return self.visited[-1] if self.visited else ""

    async def title(self) -> str:
        return "AAPL Chart - TradingView"


class StubKeyboard:
    def __init__(self) -> None:
        self.typed: list[str] = []
        self.pressed: list[str] = []

    async def write(self, text: str) -> None:
        self.typed.append(text)

    async def press(self, key: str) -> None:
        self.pressed.append(key)


class StubMouse:
    def __init__(self) -> None:
        self.clicks: list[tuple[int, int]] = []

    async def click(self, x: int, y: int) -> None:
        self.clicks.append((x, y))


class StubScreen:
    def __init__(self, frame: np.ndarray | None = None) -> None:
        self.frame = (
            frame if frame is not None else np.zeros((60, 80, 3), dtype=np.uint8)
        )

    async def capture(self) -> np.ndarray:
        return self.frame

    async def capture_region(
        self, left: int, top: int, width: int, height: int
    ) -> np.ndarray:
        return self.frame[:height, :width]


class StubVision:
    def __init__(
        self, blocks: list[TextBlock] | None = None, *, has_ocr: bool = True
    ) -> None:
        self._blocks = blocks if blocks is not None else []
        self._has_ocr = has_ocr

    @property
    def has_ocr(self) -> bool:
        return self._has_ocr

    @property
    def has_detector(self) -> bool:
        return False

    async def read_text(self, image) -> list[TextBlock]:
        return list(self._blocks)


class StubGrounding:
    def __init__(self, result) -> None:
        self._result = result

    async def ground(self, description: str, image):
        return self._result


class StubGroundingResult:
    def __init__(
        self,
        *,
        success: bool = True,
        safe_to_act: bool = True,
        confidence: float = 0.95,
        band: str = "high",
        center: tuple[int, int] = (40, 30),
        reason: str = "",
    ) -> None:
        self.success = success
        self.safe_to_act = safe_to_act
        self.confidence = confidence
        self.confidence_band = band
        self.center = center
        self.reason = reason


def _text(text: str, confidence: float = 0.9) -> TextBlock:
    return TextBlock(
        text=text, confidence=confidence,
        left=10, top=20, right=110, bottom=40,
    )


# ==============================================================
# URL conventions (pure, no browser)
# ==============================================================


def test_chart_url_bare_symbol():
    url = chart_url("aapl")
    assert url.startswith(TRADINGVIEW_BASE_URL)
    assert "AAPL" in url


def test_chart_url_exchange_symbol_slug():
    assert "NSE:RELIANCE" in chart_url("reliance", exchange="nse")


def test_chart_url_rejects_empty_symbol():
    with pytest.raises(ValueError, match="non-empty symbol"):
        chart_url("  ")


# ==============================================================
# Chart lifecycle
# ==============================================================


@pytest.mark.asyncio
async def test_open_chart_navigates_and_reads_back():
    browser = StubBrowser()
    result = await TradingViewAdapter(browser=browser).open_chart(
        "AAPL", exchange="NASDAQ"
    )
    assert "NASDAQ:AAPL" in result["url"]
    assert result["page_url"] == result["url"]
    assert "TradingView" in result["page_title"]
    assert browser.visited == [result["url"]]


@pytest.mark.asyncio
async def test_open_chart_without_browser_is_honest():
    with pytest.raises(TradingError, match="no browser"):
        await TradingViewAdapter().open_chart("AAPL")


@pytest.mark.asyncio
async def test_select_timeframe_sends_interval_keys():
    keyboard = StubKeyboard()
    result = await TradingViewAdapter(keyboard=keyboard).select_timeframe("1d")
    assert result["keys_sent"] == TIMEFRAME_KEYS["1d"] == "D"
    assert keyboard.typed == ["D"]
    assert keyboard.pressed == ["enter"]


@pytest.mark.asyncio
async def test_select_timeframe_refuses_unknown():
    with pytest.raises(TradingError, match="Unknown TradingView timeframe"):
        await TradingViewAdapter(keyboard=StubKeyboard()).select_timeframe("7x")


@pytest.mark.asyncio
async def test_select_timeframe_without_keyboard_is_honest():
    with pytest.raises(TradingError, match="no keyboard"):
        await TradingViewAdapter().select_timeframe("1d")


@pytest.mark.asyncio
async def test_timeframe_keys_cover_every_supported_bar():
    for tf in ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"):
        assert tf in TIMEFRAME_KEYS


# ==============================================================
# Capture + state
# ==============================================================


@pytest.mark.asyncio
async def test_capture_chart_returns_image_and_metadata():
    image, metadata = await TradingViewAdapter(
        screen=StubScreen()
    ).capture_chart()
    assert image.data.shape == (60, 80, 3)
    assert metadata["source"] == "screen"
    assert metadata["width"] == 80


@pytest.mark.asyncio
async def test_capture_chart_without_screen_is_honest():
    with pytest.raises(TradingError, match="no screen"):
        await TradingViewAdapter().capture_chart()


@pytest.mark.asyncio
async def test_read_chart_state_reports_vision_verbatim():
    from aetheros.vision.image import Image as VisionImage

    frame = VisionImage.from_numpy(np.zeros((60, 80, 3), dtype=np.uint8))
    vision = StubVision([_text("AAPL"), _text("1D"), _text("234.56")])
    state = await TradingViewAdapter(
        browser=StubBrowser(), vision=vision
    ).read_chart_state("AAPL", "1d", image=frame)
    assert isinstance(state, TradingViewChartState)
    assert state.requested_symbol == "AAPL"
    assert state.visible_symbol == "AAPL"
    assert state.visible_timeframe == "1D"
    assert state.visible_price == "234.56"
    assert "TradingView" in state.page_title
    assert state.limitations == ()


@pytest.mark.asyncio
async def test_read_chart_state_without_ocr_records_limitation():
    from aetheros.vision.image import Image as VisionImage

    frame = VisionImage.from_numpy(np.zeros((60, 80, 3), dtype=np.uint8))
    vision = StubVision([], has_ocr=False)
    state = await TradingViewAdapter(
        browser=StubBrowser(), vision=vision
    ).read_chart_state("AAPL", "1d", image=frame)
    assert state.visible_symbol is None
    assert any("OCR" in line for line in state.limitations)


@pytest.mark.asyncio
async def test_read_chart_state_without_browser_leaves_page_blank():
    from aetheros.vision.image import Image as VisionImage

    frame = VisionImage.from_numpy(np.zeros((60, 80, 3), dtype=np.uint8))
    state = await TradingViewAdapter(
        vision=StubVision([_text("AAPL")])
    ).read_chart_state("AAPL", "1d", image=frame)
    assert state.page_url == ""
    assert state.visible_symbol == "AAPL"


def test_chart_state_to_dict_shape():
    payload = TradingViewChartState(
        requested_symbol="AAPL", requested_timeframe="1d"
    ).to_dict()
    assert payload["requested_symbol"] == "AAPL"
    assert payload["visible_symbol"] is None
    assert "captured_at" in payload


# ==============================================================
# Grounded clicks (never a hardcoded coordinate)
# ==============================================================


@pytest.mark.asyncio
async def test_click_target_clicks_only_the_grounded_point():
    mouse = StubMouse()
    adapter = TradingViewAdapter(
        mouse=mouse,
        grounding=StubGrounding(StubGroundingResult(center=(41, 29))),
    )
    result = await adapter.click_target("symbol search box", object())
    assert result["clicked"] is True
    assert mouse.clicks == [(41, 29)]
    assert result["confidence"] == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_click_target_refuses_unsafe_match():
    mouse = StubMouse()
    adapter = TradingViewAdapter(
        mouse=mouse,
        grounding=StubGrounding(
            StubGroundingResult(safe_to_act=False, confidence=0.4, band="low")
        ),
    )
    result = await adapter.click_target("vague thing", object())
    assert result["clicked"] is False
    assert mouse.clicks == []
    assert "not safe" in result["reason"]


@pytest.mark.asyncio
async def test_click_target_reports_grounding_failure():
    mouse = StubMouse()
    adapter = TradingViewAdapter(
        mouse=mouse,
        grounding=StubGrounding(
            StubGroundingResult(success=False, reason="no match")
        ),
    )
    result = await adapter.click_target("missing widget", object())
    assert result["clicked"] is False
    assert mouse.clicks == []
    assert result["reason"] == "no match"


@pytest.mark.asyncio
async def test_click_target_without_services_is_honest():
    with pytest.raises(TradingError, match="no grounding"):
        await TradingViewAdapter(mouse=StubMouse()).click_target("x", object())
    with pytest.raises(TradingError, match="no mouse"):
        await TradingViewAdapter(
            grounding=StubGrounding(StubGroundingResult())
        ).click_target("x", object())
