"""
ChartCaptureService: screenshot capture through a stubbed screen backend.

No real display and no capture library are needed: the ScreenController
interface is stubbed with a tiny numpy frame, pinning the contract that the
chart engine delegates capture wholesale to the desktop subsystem and wraps
the result in the vision Image model.
"""

from __future__ import annotations

import numpy as np
import pytest

from aetheros.desktop.screen.controller import ScreenService
from aetheros.trading.errors import TradingError
from aetheros.trading.services.chart_service import ChartCaptureService


class StubScreenController:
    """ScreenController double returning a small solid BGR frame."""

    def __init__(self, frame: np.ndarray | None = None) -> None:
        self.frame = frame if frame is not None else np.zeros((60, 80, 3), dtype=np.uint8)
        self.captured_regions: list[tuple[int, int, int, int]] = []
        self.full_captures = 0

    def capture(self) -> np.ndarray:
        self.full_captures += 1
        return self.frame

    def capture_region(self, left, top, width, height) -> np.ndarray:
        self.captured_regions.append((left, top, width, height))
        return self.frame[:height, :width]

    def save(self, image, path) -> None:
        return None

    def size(self) -> tuple[int, int]:
        return (80, 60)

    def monitors(self) -> list[dict]:
        return [{"index": 1, "width": 80, "height": 60}]

    def close(self) -> None:
        return None


def _service(controller: StubScreenController) -> ChartCaptureService:
    return ChartCaptureService(ScreenService(controller))


# ==============================================================
# Full-screen capture
# ==============================================================


@pytest.mark.asyncio
async def test_full_capture_returns_image_and_metadata():
    controller = StubScreenController()
    image, metadata = await _service(controller).capture_chart()

    assert controller.full_captures == 1
    assert controller.captured_regions == []
    assert image is not None
    assert image.data.shape == (60, 80, 3)
    assert metadata["width"] == 80
    assert metadata["height"] == 60
    assert metadata["source"] == "screen"
    assert metadata["color_space"] == "bgr"
    assert "captured_at" in metadata
    assert "region" not in metadata


# ==============================================================
# Region capture
# ==============================================================


@pytest.mark.asyncio
async def test_region_capture_delegates_to_capture_region():
    controller = StubScreenController()
    image, metadata = await _service(controller).capture_chart(
        left=5, top=10, width=40, height=30
    )

    assert controller.captured_regions == [(5, 10, 40, 30)]
    assert controller.full_captures == 0
    assert metadata["region"] == {"left": 5, "top": 10, "width": 40, "height": 30}
    assert image.data.shape[:2] == (30, 40)


@pytest.mark.asyncio
async def test_partial_region_arguments_rejected():
    service = _service(StubScreenController())
    with pytest.raises(TradingError, match="all four"):
        await service.capture_chart(left=5, top=10, width=40)


@pytest.mark.asyncio
async def test_non_positive_region_rejected():
    service = _service(StubScreenController())
    with pytest.raises(TradingError, match="positive"):
        await service.capture_chart(left=0, top=0, width=0, height=10)


# ==============================================================
# Honest failure
# ==============================================================


@pytest.mark.asyncio
async def test_capture_failure_becomes_typed_error():
    class FailingController(StubScreenController):
        def capture(self) -> np.ndarray:
            raise RuntimeError("display went away")

    service = _service(FailingController())
    with pytest.raises(TradingError, match="capture failed"):
        await service.capture_chart()


@pytest.mark.asyncio
async def test_empty_frame_rejected():
    class EmptyController(StubScreenController):
        def capture(self) -> np.ndarray:
            return np.zeros((0, 0, 3), dtype=np.uint8)

    service = _service(EmptyController())
    with pytest.raises(TradingError, match="empty frame"):
        await service.capture_chart()


@pytest.mark.asyncio
async def test_save_screenshot_returns_metadata_without_pixels():
    controller = StubScreenController()
    metadata = await _service(controller).save_screenshot()
    assert metadata["width"] == 80
    assert "region" not in metadata
