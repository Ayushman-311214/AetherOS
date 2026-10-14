"""
End-to-end integration tests for the vision engine.

Everything here runs the real PaddleOCR backend against a deterministically
rendered image. That is the only way to catch the failure mode this suite exists
for: the provider returning an empty list for every image while raising no error
at all, which every mocked test in the suite passes cleanly.

Marked ``integration`` and skipped when paddleocr or paddlepaddle is absent, so
the default ``pytest`` run stays offline and fast. Run them explicitly with::

    pytest -m integration tests/vision

The first run may download the recognition models, which needs network access.
Nothing else in the suite does.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from aetheros.core.errors.vision_error import VisionError
from aetheros.tools.executor import ToolExecutor
from aetheros.vision import selfcheck
from aetheros.vision.controller import VisionService
from aetheros.vision.image import Image
from aetheros.vision.models import TextBlock
from aetheros.vision.providers.opencv_provider import OpenCVProvider
from aetheros.vision.providers.paddleocr_provider import PaddleOCRProvider
from aetheros.vision.providers.template_provider import OpenCVTemplateProvider

# Importing registers the vision tools; see tests/vision/test_tools.py.
import aetheros.vision.tools  # noqa: F401


_MISSING = [
    package
    for package in ("paddleocr", "paddle")
    if importlib.util.find_spec(package) is None
]

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        bool(_MISSING),
        reason=f"real OCR backend unavailable: {', '.join(_MISSING)} not installed",
    ),
]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def ocr_provider() -> Iterator[PaddleOCRProvider]:
    """
    One provider for the whole module.

    Building the models is the expensive part of an OCR call; a fresh provider
    per test would pay it repeatedly for no extra coverage.
    """

    provider = PaddleOCRProvider()

    if not provider.available:
        pytest.skip("PaddleOCR reports itself unavailable")

    yield provider

    provider.close()


@pytest.fixture(scope="module")
def real_vision(ocr_provider: PaddleOCRProvider) -> VisionService:
    """
    A VisionService with a real OCR backend — no fakes anywhere in the path.
    """

    return VisionService(
        ocr=ocr_provider,
        cv=OpenCVProvider(),
        template=OpenCVTemplateProvider(),
    )


@pytest.fixture(scope="module")
def recognised(real_vision: VisionService) -> list[TextBlock]:
    """
    The reference image read once, through the whole service.
    """

    return asyncio.run(
        real_vision.read_text(selfcheck.reference_image())
    )


# ============================================================================
# Test Image -> Vision Engine -> OCR -> Structured Result
# ============================================================================


class TestReferenceImage:
    def test_text_is_recognised(self, recognised: list[TextBlock]):
        """
        The core assertion: the pipeline returns text, not an empty list.
        """

        assert recognised

    def test_result_is_structured(self, recognised: list[TextBlock]):
        """
        Blocks, not a flat string — the caller needs positions to act on them.
        """

        assert all(isinstance(block, TextBlock) for block in recognised)

        for block in recognised:
            assert block.text.strip()
            assert 0.0 <= block.confidence <= 1.0
            assert block.width > 0
            assert block.height > 0

    def test_expected_words_are_read(self, recognised: list[TextBlock]):
        """
        Compared as a normalised word set rather than exact strings: OCR spacing
        and punctuation vary between engine versions, and pinning them would
        fail for reasons unrelated to whether the pipeline works.
        """

        text = " ".join(block.text for block in recognised)

        found = selfcheck.recognised_words(text)

        expected = selfcheck.expected_words()

        missing = expected - found

        assert not missing, (
            f"OCR did not recognise {sorted(missing)}; "
            f"it read {sorted(found)}"
        )

    def test_blocks_are_positioned_within_the_image(
        self,
        recognised: list[TextBlock],
    ):
        """
        Coordinates outside the frame mean the polygon-to-rectangle conversion is
        wrong, which would send a click to the wrong place.
        """

        image = selfcheck.reference_image()

        for block in recognised:
            assert 0 <= block.left < block.right <= image.width
            assert 0 <= block.top < block.bottom <= image.height

    def test_blocks_read_top_to_bottom(self, recognised: list[TextBlock]):
        """
        The reference lines are stacked vertically, so the first recognised block
        must sit above the last. A provider that returned them in an arbitrary
        order would make the joined text nonsense.
        """

        if len(recognised) < 2:
            pytest.skip("engine merged the lines into a single block")

        assert recognised[0].top < recognised[-1].top

    def test_result_is_json_encodable(self, recognised: list[TextBlock]):
        json.dumps([block.to_dict() for block in recognised])


# ============================================================================
# Colour handling against a real model
# ============================================================================


class TestColourSpaceEndToEnd:
    @pytest.mark.asyncio
    async def test_rgb_input_reads_the_same_text(
        self,
        real_vision: VisionService,
        recognised: list[TextBlock],
    ):
        """
        The same picture declared RGB must produce the same reading.

        BGR-to-RGB is its own inverse, so a channel swap in the wrong place is
        invisible in the pixel values and shows up only as degraded accuracy on
        coloured input. Black-on-white text is symmetric under the swap, which is
        precisely why it must match here.
        """

        reference = selfcheck.reference_image()

        as_rgb = reference.rgb()

        blocks = await real_vision.read_text(as_rgb)

        assert selfcheck.recognised_words(
            " ".join(block.text for block in blocks)
        ) == selfcheck.recognised_words(
            " ".join(block.text for block in recognised)
        )

    @pytest.mark.asyncio
    async def test_grayscale_input_is_accepted(
        self,
        real_vision: VisionService,
    ):
        """
        A single-channel image must be expanded, not rejected: preprocessing
        chains commonly hand OCR a grayscale frame.
        """

        gray = await real_vision.grayscale(selfcheck.reference_image())

        blocks = await real_vision.read_text(gray)

        assert "AETHEROS" in selfcheck.recognised_words(
            " ".join(block.text for block in blocks)
        )


# ============================================================================
# Degenerate input against a real model
# ============================================================================


class TestDegenerateInput:
    @pytest.mark.asyncio
    async def test_blank_image_returns_no_text(
        self,
        real_vision: VisionService,
    ):
        """
        A blank frame is an empty result, not an error — and not a hallucinated
        block either.
        """

        blank = Image.from_numpy(
            np.full((120, 240, 3), 255, dtype=np.uint8),
            source="blank",
            color_space="bgr",
        )

        assert await real_vision.read_text(blank) == []

    @pytest.mark.asyncio
    async def test_tiny_image_does_not_crash(
        self,
        real_vision: VisionService,
    ):
        """
        A 2x2 frame is smaller than the detector's receptive field. Whatever the
        engine does with it must arrive as a list or a VisionError, never as a
        raw exception from inside paddle.
        """

        tiny = Image.from_numpy(
            np.zeros((2, 2, 3), dtype=np.uint8),
            source="tiny",
            color_space="bgr",
        )

        try:
            result = await real_vision.read_text(tiny)

        except VisionError as exc:
            assert exc.code.startswith("VISION_")

        else:
            assert isinstance(result, list)


# ============================================================================
# Through the tool layer
# ============================================================================


class TestToolPathEndToEnd:
    @pytest.mark.asyncio
    async def test_read_image_text_returns_the_reference_text(
        self,
        isolated_container,
        real_vision: VisionService,
        tmp_path: Path,
    ):
        """
        The full production path minus the display: registry -> executor ->
        validator -> tool -> Image.open -> real OCR -> serialised result.
        """

        isolated_container.register_singleton(
            VisionService,
            lambda: real_vision,
        )

        target = tmp_path / "reference.png"

        selfcheck.reference_image().save(target)

        result = await ToolExecutor().execute(
            "read_image_text",
            {"path": str(target)},
        )

        assert result["count"] > 0

        assert selfcheck.expected_words() <= selfcheck.recognised_words(
            result["text"]
        )

        json.dumps(result)

    @pytest.mark.asyncio
    async def test_saved_and_reloaded_image_reads_the_same(
        self,
        real_vision: VisionService,
        tmp_path: Path,
        recognised: list[TextBlock],
    ):
        """
        A round trip through PNG must not change what OCR reads. If save() and
        open() disagreed about channel order, this is where it would show.
        """

        target = tmp_path / "roundtrip.png"

        selfcheck.reference_image().save(target)

        blocks = await real_vision.read_text(Image.open(target))

        assert selfcheck.recognised_words(
            " ".join(block.text for block in blocks)
        ) == selfcheck.recognised_words(
            " ".join(block.text for block in recognised)
        )
