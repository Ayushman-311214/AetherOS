"""
Tests for the Vision Engine.

Run with:
    pytest tests/vision/
"""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest

from aetheros.vision import (
    BaseVisionProvider,
    Detection,
    DetectionProvider,
    Image,
    OCRProvider,
    OpenCVProvider,
    OpenCVTemplateProvider,
    PaddleOCRProvider,
    TemplateMatch,
    TemplateProvider,
    TextBlock,
    VisionProvider,
    VisionService,
    YOLOProvider,
)


def _installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


# ============================================================================
# Package structure
# ============================================================================


class TestVisionPackageStructure:
    def test_core_exports(self):
        assert VisionService is not None
        assert Image is not None

    def test_model_exports(self):
        assert Detection is not None
        assert TemplateMatch is not None
        assert TextBlock is not None

    def test_provider_interfaces(self):
        for iface in (
            BaseVisionProvider,
            VisionProvider,
            OCRProvider,
            DetectionProvider,
            TemplateProvider,
        ):
            assert issubclass(iface, BaseVisionProvider)

    def test_concrete_providers_implement_interfaces(self):
        assert issubclass(OpenCVProvider, VisionProvider)
        assert issubclass(PaddleOCRProvider, OCRProvider)
        assert issubclass(OpenCVTemplateProvider, TemplateProvider)
        assert issubclass(YOLOProvider, DetectionProvider)


# ============================================================================
# Image
# ============================================================================


class TestImage:
    def test_dimensions_from_array(self):
        img = Image(
            data=np.zeros((200, 300, 3), dtype=np.uint8),
            source="test",
        )

        assert img.width == 300
        assert img.height == 200
        assert img.channels == 3
        assert img.shape == (200, 300, 3)

    def test_grayscale_channels(self):
        img = Image(
            data=np.zeros((50, 60), dtype=np.uint8),
            source="test",
        )

        assert img.channels == 1
        assert img.width == 60
        assert img.height == 50

    def test_crop(self):
        img = Image(
            data=np.zeros((100, 100, 3), dtype=np.uint8),
            source="test",
        )

        cropped = img.crop(x=10, y=20, width=30, height=40)

        assert cropped.width == 30
        assert cropped.height == 40

    def test_resize(self):
        img = Image(
            data=np.zeros((100, 100, 3), dtype=np.uint8),
            source="test",
        )

        resized = img.resize(width=50, height=25)

        assert resized.width == 50
        assert resized.height == 25

    def test_copy_is_independent(self):
        img = Image(
            data=np.zeros((10, 10, 3), dtype=np.uint8),
            source="test",
        )

        duplicate = img.copy()
        duplicate.data[0, 0] = 255

        assert img.data[0, 0].sum() == 0


# ============================================================================
# Models
# ============================================================================


class TestDetection:
    def test_geometry(self):
        det = Detection(
            label="person",
            confidence=0.95,
            left=10,
            top=20,
            right=110,
            bottom=220,
        )

        assert det.label == "person"
        assert det.confidence == 0.95
        assert det.width == 100
        assert det.height == 200
        assert det.area == 20_000
        assert det.center == (60, 120)


class TestTemplateMatch:
    def test_center(self):
        match = TemplateMatch(
            x=10,
            y=20,
            width=100,
            height=200,
            confidence=0.90,
        )

        assert match.center == (60, 120)

    def test_bbox(self):
        match = TemplateMatch(
            x=10,
            y=20,
            width=100,
            height=200,
            confidence=0.90,
        )

        assert match.bbox == (10, 20, 110, 220)

    def test_to_dict(self):
        match = TemplateMatch(
            x=1,
            y=2,
            width=3,
            height=4,
            confidence=0.5,
        )

        payload = match.to_dict()

        assert payload["x"] == 1
        assert payload["confidence"] == 0.5
        assert payload["bbox"] == (1, 2, 4, 6)


class TestTextBlock:
    def test_creation(self):
        block = TextBlock(
            text="Hello",
            confidence=0.95,
            left=10,
            top=20,
            right=100,
            bottom=50,
        )

        assert block.text == "Hello"
        assert block.confidence == 0.95


# ============================================================================
# Template matching (deterministic, real OpenCV)
# ============================================================================


@pytest.mark.skipif(not _installed("cv2"), reason="OpenCV not installed")
class TestTemplateMatching:
    def test_provider_metadata(self):
        provider = OpenCVTemplateProvider()
        assert "Template" in provider.name

    @pytest.mark.asyncio
    async def test_finds_known_patch(self):
        # Low-contrast noise background, plus a distinctive high-contrast
        # patch. The patch must be non-uniform: TM_CCOEFF_NORMED is
        # degenerate for a zero-variance template.
        rng = np.random.default_rng(42)
        canvas = rng.integers(0, 40, (100, 100, 3), dtype=np.uint8)

        patch = rng.integers(180, 256, (20, 20, 3), dtype=np.uint8)
        canvas[30:50, 40:60] = patch

        image = Image(data=canvas, source="canvas")
        template = Image(data=canvas[30:50, 40:60].copy(), source="patch")

        matches = await OpenCVTemplateProvider().find(
            image,
            template,
            threshold=0.98,
        )

        assert len(matches) >= 1
        top_match = matches[0]
        assert top_match.confidence >= 0.98
        # Template matching returns top-left corner
        assert top_match.x == 40
        assert top_match.y == 30
        assert top_match.width == 20
        assert top_match.height == 20

    @pytest.mark.asyncio
    async def test_distinct_patterns_no_match(self):
        # Vertical stripes
        image_data = np.zeros((100, 100, 3), dtype=np.uint8)
        image_data[:, ::2] = 255

        # Horizontal stripes
        template_data = np.zeros((20, 20, 3), dtype=np.uint8)
        template_data[::2, :] = 255

        image = Image(data=image_data, source="vert")
        template = Image(data=template_data, source="horiz")

        matches = await OpenCVTemplateProvider().find(
            image,
            template,
            threshold=0.90,
        )

        # Very different patterns should not match
        assert len(matches) == 0


# ============================================================================
# Optional providers
# ============================================================================


@pytest.mark.skipif(not _installed("cv2"), reason="OpenCV not installed")
def test_opencv_provider_metadata():
    assert OpenCVProvider().name == "OpenCV"


@pytest.mark.skipif(
    not (_installed("paddleocr") and _installed("paddle")),
    reason="PaddleOCR backend (paddle) not installed",
)
def test_paddleocr_provider_metadata():
    assert PaddleOCRProvider().name == "PaddleOCR"


@pytest.mark.skipif(
    not _installed("ultralytics"),
    reason="Ultralytics not installed",
)
def test_yolo_provider_metadata():
    assert "YOLO" in YOLOProvider().name
