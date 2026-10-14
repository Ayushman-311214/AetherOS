"""
Tests for the vision providers' performance-oriented internals.

These pin the deterministic, model-free pieces of the two heavy providers so the
maths is verified in this CPU-only environment (no ultralytics / paddle / CUDA)
without ever running a model:

- ``YOLOProvider._resolve_device`` -- the device-selection policy, including the
  §13 rule that CUDA is never forced onto a build that does not have it;
- ``PaddleOCRProvider._maybe_downscale`` / ``_rescale_blocks`` -- the §3/§4
  downscale-and-remap coordinate maths, whose whole point is that a box found on
  a shrunken frame is reported in ORIGINAL pixel coordinates.

Construction of both providers is deliberately lazy (no model import), which is
what lets these run without the heavy packages installed.
"""

from __future__ import annotations

import numpy as np
import pytest

from aetheros.vision.models import TextBlock
from aetheros.vision.providers.paddleocr_provider import (
    PaddleOCRProvider,
    _rescale_blocks,
)
from aetheros.vision.providers.yolo_provider import YOLOProvider


# ============================================================================
# YOLO device resolution
# ============================================================================


def _force_cuda(monkeypatch, available: bool) -> None:
    """Make torch.cuda.is_available() report a chosen value."""
    import torch

    monkeypatch.setattr(torch.cuda, "is_available", lambda: available)


class TestResolveDeviceAuto:

    def test_empty_pref_picks_cuda_when_available(self, monkeypatch) -> None:
        _force_cuda(monkeypatch, True)
        provider = YOLOProvider(device="")

        assert provider._resolve_device() == "cuda:0"

    def test_empty_pref_falls_back_to_cpu(self, monkeypatch) -> None:
        _force_cuda(monkeypatch, False)
        provider = YOLOProvider(device="")

        assert provider._resolve_device() == "cpu"


class TestResolveDeviceExplicit:

    def test_cuda_honoured_when_available(self, monkeypatch) -> None:
        _force_cuda(monkeypatch, True)
        provider = YOLOProvider(device="cuda:1")

        assert provider._resolve_device() == "cuda:1"

    def test_cuda_never_forced_onto_a_cpu_build(self, monkeypatch) -> None:
        # §13: an explicit CUDA request on a CPU-only build must degrade to CPU
        # with a warning, never crash inference by forcing an absent device.
        _force_cuda(monkeypatch, False)
        provider = YOLOProvider(device="cuda:0")

        assert provider._resolve_device() == "cpu"

    def test_explicit_cpu_is_respected_even_with_cuda(self, monkeypatch) -> None:
        _force_cuda(monkeypatch, True)
        provider = YOLOProvider(device="cpu")

        assert provider._resolve_device() == "cpu"

    def test_pref_is_lowercased(self, monkeypatch) -> None:
        _force_cuda(monkeypatch, False)
        provider = YOLOProvider(device="CPU")

        assert provider._resolve_device() == "cpu"


class TestYoloConstructionIsCheap:

    def test_confidence_and_imgsz_are_stored(self) -> None:
        provider = YOLOProvider(imgsz=480, confidence=0.4)

        assert provider._imgsz == 480
        assert provider._confidence == pytest.approx(0.4)


# ============================================================================
# PaddleOCR downscale + coordinate remap
# ============================================================================


def _frame(width: int, height: int) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


class TestMaybeDownscale:

    def test_no_downscale_when_disabled(self) -> None:
        provider = PaddleOCRProvider(processing_width=0)
        frame = _frame(1920, 1080)

        out, scale = provider._maybe_downscale(frame)

        assert scale == 1.0
        assert out.shape == frame.shape

    def test_no_downscale_when_frame_narrower_than_target(self) -> None:
        provider = PaddleOCRProvider(processing_width=1280)
        frame = _frame(1000, 800)  # already narrower than 1280

        out, scale = provider._maybe_downscale(frame)

        assert scale == 1.0
        assert out.shape == frame.shape

    def test_downscale_preserves_aspect_ratio(self) -> None:
        provider = PaddleOCRProvider(processing_width=960)
        frame = _frame(1920, 1080)

        out, scale = provider._maybe_downscale(frame)

        # Width halved -> height halved; scale maps processed px back to source.
        assert out.shape[1] == 960
        assert out.shape[0] == 540
        assert scale == pytest.approx(1920 / 960)  # == 2.0

    def test_downscaled_frame_is_contiguous(self) -> None:
        # OpenCV/paddle input must be C-contiguous; a resize result may not be.
        provider = PaddleOCRProvider(processing_width=640)
        out, _ = provider._maybe_downscale(_frame(1920, 1080))

        assert out.flags["C_CONTIGUOUS"]


class TestRescaleBlocks:

    def _block(self) -> TextBlock:
        return TextBlock(
            text="NIFTY",
            confidence=0.9,
            left=10,
            top=20,
            right=30,
            bottom=40,
        )

    def test_scale_one_is_a_noop(self) -> None:
        block = self._block()
        _rescale_blocks([block], 1.0)

        assert (block.left, block.top, block.right, block.bottom) == (10, 20, 30, 40)

    def test_coordinates_scaled_back_to_original(self) -> None:
        block = self._block()
        _rescale_blocks([block], 2.0)

        # Every edge multiplied by the scale factor: a box found on a
        # half-size frame maps back onto the full-size original.
        assert (block.left, block.top, block.right, block.bottom) == (20, 40, 60, 80)

    def test_text_and_confidence_untouched(self) -> None:
        block = self._block()
        _rescale_blocks([block], 3.0)

        assert block.text == "NIFTY"
        assert block.confidence == pytest.approx(0.9)

    def test_rounds_to_nearest_pixel(self) -> None:
        block = TextBlock(
            text="x", confidence=0.5, left=10, top=10, right=10, bottom=10
        )
        _rescale_blocks([block], 1.5)  # 10 * 1.5 = 15.0 exactly

        assert block.left == 15

    def test_downscale_then_rescale_round_trips_to_source_scale(self) -> None:
        # Integration of the two helpers: shrink a frame, then the scale it
        # returns is exactly what maps a processed-frame box back to source.
        provider = PaddleOCRProvider(processing_width=960)
        _, scale = provider._maybe_downscale(_frame(1920, 1080))

        # A box at the far edge of the 960-wide processed frame...
        block = TextBlock(
            text="edge", confidence=0.8, left=940, top=520, right=960, bottom=540
        )
        _rescale_blocks([block], scale)

        # ...maps back to the far edge of the 1920-wide original.
        assert block.right == 1920
        assert block.bottom == 1080
