"""
Unit tests for VisionService.

The service is the real implementation throughout; only the OCR backend is
faked, because that is the one dependency that needs a downloaded model. The
OpenCV and template providers are real, so these tests also cover the
service-to-provider boundary rather than just the service in isolation.
"""

from __future__ import annotations

import numpy as np
import pytest

from aetheros.core.errors.vision_error import VisionError
from aetheros.vision.controller import VisionService
from aetheros.vision.image import Image
from aetheros.vision.models import Detection, TextBlock
from aetheros.vision.providers.opencv_provider import OpenCVProvider


# ============================================================================
# Construction and capabilities
# ============================================================================


class TestServiceInitialisation:
    def test_requires_keyword_arguments(self, make_fake_ocr):
        """
        Positional wiring is rejected: ``VisionService(ocr, cv)`` and
        ``VisionService(cv, ocr)`` are indistinguishable at a call site, and
        getting them the wrong way round fails much later.
        """

        with pytest.raises(TypeError):
            VisionService(make_fake_ocr(), OpenCVProvider())  # type: ignore[misc]

    def test_optional_providers_default_to_absent(self, make_vision_service):
        service = make_vision_service(template=None)

        assert service.has_detector is False
        assert service.has_template is False

    def test_capabilities_reports_the_provider_mix(self, vision_service):
        capabilities = vision_service.capabilities()

        assert capabilities == {
            "ocr": True,
            "detection": False,
            "template": True,
            "image_processing": True,
        }

    def test_capabilities_is_serialisable(self, vision_service):
        assert all(
            isinstance(value, bool)
            for value in vision_service.capabilities().values()
        )

    def test_has_ocr_follows_the_backend(
        self,
        make_vision_service,
        make_fake_ocr,
    ):
        service = make_vision_service(
            ocr=make_fake_ocr(available=False),
        )

        assert service.has_ocr is False

    def test_has_detector_requires_an_available_backend(
        self,
        make_vision_service,
        make_fake_detector,
    ):
        service = make_vision_service(
            detector=make_fake_detector(available=False),
        )

        assert service.has_detector is False


# ============================================================================
# OCR
# ============================================================================


class TestReadText:
    @pytest.mark.asyncio
    async def test_returns_the_backend_blocks(
        self,
        vision_service,
        bgr_image,
        sample_blocks,
    ):
        blocks = await vision_service.read_text(bgr_image)

        assert len(blocks) == len(sample_blocks)
        assert blocks[0].text == "AETHEROS"
        assert all(isinstance(block, TextBlock) for block in blocks)

    @pytest.mark.asyncio
    async def test_passes_the_image_through_untouched(
        self,
        vision_service,
        fake_ocr,
        bgr_image,
    ):
        await vision_service.read_text(bgr_image)

        assert fake_ocr.calls == [bgr_image]

    @pytest.mark.asyncio
    async def test_empty_result_is_valid(
        self,
        make_vision_service,
        make_fake_ocr,
        bgr_image,
    ):
        """
        No readable text is an outcome, not a failure.
        """

        service = make_vision_service(ocr=make_fake_ocr([]))

        assert await service.read_text(bgr_image) == []

    @pytest.mark.asyncio
    async def test_rejects_none(self, vision_service):
        with pytest.raises(VisionError) as excinfo:
            await vision_service.read_text(None)  # type: ignore[arg-type]

        assert excinfo.value.code == "VISION_INVALID_IMAGE"
        assert excinfo.value.context.operation == "read_text"

    @pytest.mark.asyncio
    async def test_rejects_a_raw_array(self, vision_service, fake_ocr):
        """
        The type boundary that used to fail inside a provider with
        ``AttributeError: 'ndarray' object has no attribute 'data'``.
        """

        with pytest.raises(VisionError) as excinfo:
            await vision_service.read_text(
                np.zeros((4, 4, 3), dtype=np.uint8),  # type: ignore[arg-type]
            )

        assert excinfo.value.code == "VISION_INVALID_IMAGE"
        assert fake_ocr.calls == []

    @pytest.mark.asyncio
    async def test_backend_vision_error_propagates(
        self,
        make_vision_service,
        make_fake_ocr,
        bgr_image,
    ):
        failure = VisionError(
            code="OCR_FAILED",
            message="model blew up",
        )

        service = make_vision_service(ocr=make_fake_ocr(error=failure))

        with pytest.raises(VisionError) as excinfo:
            await service.read_text(bgr_image)

        assert excinfo.value is failure

    @pytest.mark.asyncio
    async def test_unexpected_backend_error_is_not_swallowed(
        self,
        make_vision_service,
        make_fake_ocr,
        bgr_image,
    ):
        service = make_vision_service(
            ocr=make_fake_ocr(error=RuntimeError("segfault-ish")),
        )

        with pytest.raises(RuntimeError):
            await service.read_text(bgr_image)


class TestFindText:
    @pytest.mark.asyncio
    async def test_filters_to_matching_blocks(self, vision_service, bgr_image):
        matches = await vision_service.find_text(bgr_image, "vision")

        assert len(matches) == 1
        assert matches[0].text == "VISION TEST"

    @pytest.mark.asyncio
    async def test_case_sensitive_search(self, vision_service, bgr_image):
        assert await vision_service.find_text(
            bgr_image,
            "vision",
            case_sensitive=True,
        ) == []

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self, vision_service, bgr_image):
        assert await vision_service.find_text(bgr_image, "NIFTY") == []

    @pytest.mark.asyncio
    async def test_rejects_empty_query(self, vision_service, bgr_image):
        with pytest.raises(VisionError) as excinfo:
            await vision_service.find_text(bgr_image, "")

        assert excinfo.value.code == "VISION_INVALID_ARGUMENT"

    @pytest.mark.asyncio
    async def test_rejects_invalid_image(self, vision_service):
        with pytest.raises(VisionError) as excinfo:
            await vision_service.find_text(None, "text")  # type: ignore[arg-type]

        assert excinfo.value.code == "VISION_INVALID_IMAGE"


# ============================================================================
# Object detection
# ============================================================================


class TestDetectObjects:
    @pytest.mark.asyncio
    async def test_unconfigured_detector_raises_a_specific_error(
        self,
        vision_service,
        bgr_image,
    ):
        with pytest.raises(VisionError) as excinfo:
            await vision_service.detect_objects(bgr_image)

        assert excinfo.value.code == "VISION_DETECTION_UNAVAILABLE"
        assert excinfo.value.hint is not None

    @pytest.mark.asyncio
    async def test_delegates_to_the_detector(
        self,
        make_vision_service,
        make_fake_detector,
        bgr_image,
    ):
        detector = make_fake_detector(
            [
                Detection(
                    label="candle",
                    confidence=0.8,
                    left=1,
                    top=2,
                    right=11,
                    bottom=22,
                )
            ]
        )

        service = make_vision_service(detector=detector)

        detections = await service.detect_objects(bgr_image)

        assert [d.label for d in detections] == ["candle"]
        assert detector.calls == [bgr_image]

    @pytest.mark.asyncio
    async def test_rejects_invalid_image_before_delegating(
        self,
        make_vision_service,
        make_fake_detector,
    ):
        detector = make_fake_detector()

        service = make_vision_service(detector=detector)

        with pytest.raises(VisionError):
            await service.detect_objects(None)  # type: ignore[arg-type]

        assert detector.calls == []


# ============================================================================
# Template matching
# ============================================================================


class TestFindTemplate:
    @pytest.mark.asyncio
    async def test_unconfigured_template_provider_raises(
        self,
        make_vision_service,
        bgr_image,
    ):
        service = make_vision_service(template=None)

        with pytest.raises(VisionError) as excinfo:
            await service.find_template(bgr_image, bgr_image)

        assert excinfo.value.code == "VISION_TEMPLATE_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_validates_both_images(self, vision_service, bgr_image):
        with pytest.raises(VisionError) as excinfo:
            await vision_service.find_template(bgr_image, None)  # type: ignore[arg-type]

        assert excinfo.value.code == "VISION_INVALID_IMAGE"

    @pytest.mark.asyncio
    async def test_finds_a_known_patch(self, vision_service):
        rng = np.random.default_rng(7)

        canvas = rng.integers(0, 40, (60, 60, 3), dtype=np.uint8)
        canvas[20:36, 24:40] = rng.integers(
            180, 256, (16, 16, 3), dtype=np.uint8
        )

        image = Image.from_numpy(canvas, source="canvas")
        template = Image.from_numpy(
            canvas[20:36, 24:40].copy(),
            source="patch",
        )

        matches = await vision_service.find_template(
            image,
            template,
            threshold=0.98,
        )

        assert matches
        assert (matches[0].x, matches[0].y) == (24, 20)


# ============================================================================
# Image processing
# ============================================================================


class TestImageProcessing:
    @pytest.mark.asyncio
    async def test_grayscale_declares_its_colour_space(
        self,
        vision_service,
        bgr_image,
    ):
        """
        A single-channel result tagged BGR would make a later rgb() call try to
        reorder channels that no longer exist.
        """

        gray = await vision_service.grayscale(bgr_image)

        assert gray.channels == 1
        assert gray.color_space == "gray"

    @pytest.mark.asyncio
    async def test_resize(self, vision_service, bgr_image):
        resized = await vision_service.resize(bgr_image, 6, 4)

        assert (resized.width, resized.height) == (6, 4)

    @pytest.mark.asyncio
    async def test_blur_keeps_shape(self, vision_service, bgr_image):
        blurred = await vision_service.blur(bgr_image, kernel=3)

        assert blurred.shape == bgr_image.shape

    @pytest.mark.asyncio
    async def test_edges_returns_single_channel(
        self,
        vision_service,
        bgr_image,
    ):
        edges = await vision_service.edges(bgr_image)

        assert edges.channels == 1
        assert edges.color_space == "gray"

    @pytest.mark.asyncio
    async def test_grayscale_of_gray_input_is_accepted(self, vision_service):
        gray = Image.from_numpy(np.zeros((6, 6), dtype=np.uint8))

        assert (await vision_service.grayscale(gray)).channels == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "operation, arguments",
        [
            ("resize", (0, 10)),
            ("blur", (4,)),
            ("edges", (200, 100)),
        ],
    )
    async def test_invalid_arguments_are_rejected(
        self,
        vision_service,
        bgr_image,
        operation,
        arguments,
    ):
        with pytest.raises(VisionError) as excinfo:
            await getattr(vision_service, operation)(bgr_image, *arguments)

        assert excinfo.value.code == "VISION_INVALID_ARGUMENT"

    @pytest.mark.asyncio
    async def test_processing_rejects_invalid_image(self, vision_service):
        for operation in ("resize", "grayscale", "blur", "edges"):

            arguments = (4, 4) if operation == "resize" else ()

            with pytest.raises(VisionError):
                await getattr(vision_service, operation)(None, *arguments)


# ============================================================================
# Lifecycle
# ============================================================================


class TestShutdown:
    @pytest.mark.asyncio
    async def test_closes_every_provider(
        self,
        make_vision_service,
        make_fake_ocr,
        make_fake_detector,
    ):
        ocr = make_fake_ocr()
        detector = make_fake_detector()

        service = make_vision_service(ocr=ocr, detector=detector)

        await service.shutdown()

        assert ocr.closed is True
        assert detector.closed is True

    @pytest.mark.asyncio
    async def test_one_failing_provider_does_not_block_the_others(
        self,
        make_vision_service,
        make_unclosable_ocr,
        make_fake_detector,
    ):
        detector = make_fake_detector()

        service = make_vision_service(
            ocr=make_unclosable_ocr(),
            detector=detector,
        )

        await service.shutdown()

        assert detector.closed is True

    @pytest.mark.asyncio
    async def test_tolerates_absent_optional_providers(
        self,
        make_vision_service,
    ):
        service = make_vision_service(template=None)

        await service.shutdown()
