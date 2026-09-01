"""
Unit tests for the concrete vision providers.

The OpenCV and template providers run for real — they are local libraries with
no model download and no network, so there is nothing worth faking.

For PaddleOCR and YOLO only the model construction is replaced. Everything the
provider itself does — deciding it is unavailable, coercing the frame, parsing
the result — is the real code path, because that is where the defects were:
the provider used to hand the model an RGB frame while the model expected BGR,
and used to read its results off a ``{"res": ...}`` envelope that never held the
fields it was looking for. Both bugs are silent, and a mocked provider would
reproduce neither.
"""

from __future__ import annotations

import builtins
import importlib.util
import os
import sys
import types
from typing import Any

import numpy as np
import pytest

from aetheros.core.errors.vision_error import VisionError
from aetheros.vision.image import Image
from aetheros.vision.providers import paddleocr_provider as paddle_module
from aetheros.vision.providers import yolo_provider as yolo_module
from aetheros.vision.providers.opencv_provider import OpenCVProvider
from aetheros.vision.providers.paddleocr_provider import PaddleOCRProvider
from aetheros.vision.providers.template_provider import OpenCVTemplateProvider
from aetheros.vision.providers.yolo_provider import YOLOProvider


# ============================================================================
# Helpers
# ============================================================================


_REAL_FIND_SPEC = importlib.util.find_spec


def _hide_package(monkeypatch, module, package: str) -> None:
    """
    Make one package look uninstalled to a provider's availability check.

    Narrow on purpose: everything except ``package`` still resolves normally, so
    an unrelated import inside the test is unaffected.
    """

    def fake_find_spec(name: str, *args: Any, **kwargs: Any):
        if name == package:
            return None

        return _REAL_FIND_SPEC(name, *args, **kwargs)

    monkeypatch.setattr(
        module.importlib.util,
        "find_spec",
        fake_find_spec,
    )


def _show_package(monkeypatch, module, package: str) -> None:
    """
    The inverse: make one package look installed even when it is not.

    Lets the "package present but weights missing" branch be tested on a machine
    that has neither.
    """

    def fake_find_spec(name: str, *args: Any, **kwargs: Any):
        if name == package:
            return object()

        return _REAL_FIND_SPEC(name, *args, **kwargs)

    monkeypatch.setattr(
        module.importlib.util,
        "find_spec",
        fake_find_spec,
    )


def _force_available(monkeypatch, absent: str | None = None) -> None:
    """
    Make the OCR provider's required packages look installed, except ``absent``.

    Patches all of them in one call on purpose: ``_show_package`` falls back to
    the *original* find_spec, so calling it twice would discard the first patch.
    Lets the tests that exercise ``_build`` behave identically on a machine with
    paddle installed and on one without it.
    """

    def fake_find_spec(name: str, *args: Any, **kwargs: Any):
        if name == absent:
            return None

        if name in paddle_module._REQUIRED_PACKAGES:
            return object()

        return _REAL_FIND_SPEC(name, *args, **kwargs)

    monkeypatch.setattr(
        paddle_module.importlib.util,
        "find_spec",
        fake_find_spec,
    )


class StubOCRModel:
    """
    Stands in for a built PaddleOCR pipeline.

    Records the frame it was handed so a test can assert the channel order that
    actually reached the model.
    """

    def __init__(
        self,
        results: Any,
        *,
        error: Exception | None = None,
    ) -> None:

        self._results = results
        self._error = error

        self.frames: list[np.ndarray] = []
        self.closed = False

    def predict(self, frame: np.ndarray) -> Any:

        self.frames.append(frame)

        if self._error is not None:
            raise self._error

        return self._results

    def close(self) -> None:
        self.closed = True


class EnvelopeResult:
    """
    A PaddleOCR 3.x result seen through its documented ``json`` accessor.

    The accessor wraps the recognition fields in ``{"res": ...}``. Reading
    ``rec_texts`` straight off that wrapper is how the provider came to report
    zero text for every image while raising no error at all.
    """

    def __init__(self, fields: dict[str, Any]) -> None:
        self._fields = fields

    @property
    def json(self) -> dict[str, Any]:
        return {"res": self._fields}


def _ocr_with(monkeypatch, model: StubOCRModel) -> PaddleOCRProvider:
    """
    A real provider whose model construction is replaced by a stub.

    ``_build`` is the seam because it is exactly the step that needs paddle
    installed and the weights downloaded. Preparation, inference dispatch and
    result parsing all stay real.
    """

    provider = PaddleOCRProvider()

    monkeypatch.setattr(provider, "_build", lambda: model)

    return provider


# ============================================================================
# OpenCV image processing
# ============================================================================


class TestOpenCVProviderMetadata:
    def test_reports_the_library_version(self):
        import cv2

        provider = OpenCVProvider()

        assert provider.name == "OpenCV"
        assert provider.version == cv2.__version__

    def test_is_always_available(self):
        assert OpenCVProvider().available is True


class TestOpenCVOperations:
    @pytest.mark.asyncio
    async def test_resize(self, bgr_image: Image):
        resized = await OpenCVProvider().resize(bgr_image, 24, 16)

        assert resized.shape == (16, 24, 3)

    @pytest.mark.asyncio
    async def test_resize_keeps_provenance(self, bgr_image: Image):
        resized = await OpenCVProvider().resize(bgr_image, 4, 4)

        assert resized.source == bgr_image.source
        assert resized.color_space == "bgr"

    @pytest.mark.asyncio
    async def test_grayscale_declares_gray(self, bgr_image: Image):
        gray = await OpenCVProvider().grayscale(bgr_image)

        assert gray.channels == 1
        assert gray.color_space == "gray"

    @pytest.mark.asyncio
    async def test_grayscale_respects_declared_channel_order(self):
        """
        A fixed COLOR_BGR2GRAY would weight red and blue the wrong way round for
        RGB input, so the two must not produce the same luminance.
        """

        data = np.zeros((4, 4, 3), dtype=np.uint8)
        data[:, :, 0] = 10
        data[:, :, 1] = 20
        data[:, :, 2] = 30

        provider = OpenCVProvider()

        as_bgr = await provider.grayscale(
            Image(data=data.copy(), color_space="bgr")
        )

        as_rgb = await provider.grayscale(
            Image(data=data.copy(), color_space="rgb")
        )

        assert as_bgr.data[0, 0] != as_rgb.data[0, 0]

    @pytest.mark.asyncio
    async def test_blur_preserves_shape(self, bgr_image: Image):
        blurred = await OpenCVProvider().blur(bgr_image, kernel=3)

        assert blurred.shape == bgr_image.shape
        assert blurred.color_space == "bgr"

    @pytest.mark.asyncio
    async def test_edges_are_gray(self, bgr_image: Image):
        edges = await OpenCVProvider().edges(bgr_image)

        assert edges.channels == 1
        assert edges.color_space == "gray"

    @pytest.mark.asyncio
    async def test_edges_find_a_real_boundary(self):
        data = np.zeros((40, 40, 3), dtype=np.uint8)
        data[:, 20:] = 255

        edges = await OpenCVProvider().edges(
            Image.from_numpy(data),
            50,
            150,
        )

        assert int(edges.data.max()) == 255

    @pytest.mark.asyncio
    async def test_threshold_is_gray_and_binary(self):
        data = np.full((10, 10, 3), 200, dtype=np.uint8)

        result = await OpenCVProvider().threshold(
            Image.from_numpy(data),
            value=100,
        )

        assert result.color_space == "gray"
        assert set(np.unique(result.data)) <= {0, 255}

    @pytest.mark.asyncio
    async def test_dilate_and_erode(self, bgr_image: Image):
        provider = OpenCVProvider()

        assert (
            await provider.dilate(bgr_image)
        ).shape == bgr_image.shape

        assert (
            await provider.erode(bgr_image)
        ).shape == bgr_image.shape


class TestOpenCVValidation:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "operation, arguments",
        [
            ("resize", (0, 4)),
            ("resize", (4, -2)),
            # An even kernel makes cv2.GaussianBlur raise a bare cv2.error.
            ("blur", (4,)),
            ("blur", (0,)),
            ("edges", (150, 100)),
            ("edges", (-1, 100)),
            ("threshold", (256,)),
            ("threshold", (-1,)),
            ("dilate", (0,)),
            ("erode", (-3,)),
        ],
    )
    async def test_rejects_invalid_arguments(
        self,
        bgr_image: Image,
        operation,
        arguments,
    ):
        with pytest.raises(VisionError) as excinfo:
            await getattr(OpenCVProvider(), operation)(
                bgr_image,
                *arguments,
            )

        assert excinfo.value.code == "VISION_INVALID_ARGUMENT"

    @pytest.mark.asyncio
    async def test_error_names_the_operation(self, bgr_image: Image):
        with pytest.raises(VisionError) as excinfo:
            await OpenCVProvider().blur(bgr_image, kernel=2)

        assert excinfo.value.context.operation == "blur"
        assert excinfo.value.context.module == "vision.processing"


# ============================================================================
# Template matching
# ============================================================================


class TestTemplateProvider:
    def test_metadata(self):
        import cv2

        provider = OpenCVTemplateProvider()

        assert provider.name == "OpenCV Template Matching"
        assert provider.version == cv2.__version__
        assert provider.available is True

    @pytest.mark.asyncio
    async def test_finds_an_exact_patch(self):
        rng = np.random.default_rng(11)

        canvas = rng.integers(0, 60, (80, 80, 3), dtype=np.uint8)
        canvas[30:46, 12:28] = rng.integers(
            190, 256, (16, 16, 3), dtype=np.uint8
        )

        matches = await OpenCVTemplateProvider().find(
            Image.from_numpy(canvas),
            Image.from_numpy(canvas[30:46, 12:28].copy()),
            threshold=0.99,
        )

        assert matches
        assert (matches[0].x, matches[0].y) == (12, 30)
        assert (matches[0].width, matches[0].height) == (16, 16)

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self):
        # Two independent noise patterns. Correlating one against the other at
        # 0.99 is effectively impossible, and both seeds are fixed, so the
        # result is deterministic. A flat template would be worse than useless
        # here: its zero variance makes normalised correlation undefined.
        image = Image.from_numpy(
            np.random.default_rng(101).integers(
                0, 256, (40, 40, 3), dtype=np.uint8
            )
        )

        template = Image.from_numpy(
            np.random.default_rng(202).integers(
                0, 256, (8, 8, 3), dtype=np.uint8
            )
        )

        assert await OpenCVTemplateProvider().find(
            image,
            template,
            threshold=0.99,
        ) == []

    @pytest.mark.asyncio
    async def test_rejects_oversized_template(self, bgr_image: Image):
        template = Image.from_numpy(
            np.zeros((40, 40, 3), dtype=np.uint8)
        )

        with pytest.raises(VisionError) as excinfo:
            await OpenCVTemplateProvider().find(bgr_image, template)

        assert excinfo.value.code == "VISION_TEMPLATE_TOO_LARGE"
        assert "40x40" in excinfo.value.message

    @pytest.mark.asyncio
    @pytest.mark.parametrize("threshold", [-0.1, 1.5])
    async def test_rejects_out_of_range_threshold(
        self,
        bgr_image: Image,
        threshold,
    ):
        with pytest.raises(VisionError) as excinfo:
            await OpenCVTemplateProvider().find(
                bgr_image,
                bgr_image,
                threshold=threshold,
            )

        assert excinfo.value.code == "VISION_INVALID_ARGUMENT"

    @pytest.mark.asyncio
    async def test_multiscale_skips_impossible_scales(self):
        """
        Scales that would make the template larger than the image are dropped
        rather than reaching find() and raising TEMPLATE_TOO_LARGE.
        """

        rng = np.random.default_rng(3)

        canvas = rng.integers(0, 255, (60, 60, 3), dtype=np.uint8)

        image = Image.from_numpy(canvas)
        template = Image.from_numpy(canvas[10:26, 10:26].copy())

        matches = await OpenCVTemplateProvider().find_multiscale(
            image,
            template,
            threshold=0.99,
            scales=[1.0, 8.0],
        )

        assert matches
        assert matches[0].confidence == pytest.approx(1.0, abs=1e-3)


# ============================================================================
# PaddleOCR — availability
# ============================================================================


class TestPaddleAvailability:
    def test_construction_never_imports_paddle(self):
        """
        Constructing the provider must not pull in the paddle runtime: it is
        built during bootstrap on machines that may not have it at all.
        """

        provider = PaddleOCRProvider()

        assert provider._ocr is None

    def test_name_is_stable(self):
        assert PaddleOCRProvider().name == "PaddleOCR"

    def test_unavailable_when_package_is_missing(self, monkeypatch):
        _hide_package(monkeypatch, paddle_module, "paddleocr")

        provider = PaddleOCRProvider()

        assert provider.available is False
        assert provider.version == "unavailable"

    def test_unavailable_when_only_the_runtime_is_missing(self, monkeypatch):
        """
        paddleocr without paddle is not a usable OCR install.

        This is a real and easily-reached state — paddlepaddle has no wheel for
        every Python version, so ``pip install paddleocr`` alone succeeds and
        leaves the runtime absent. Reporting it as available sends the eventual
        failure down the model-initialization path, whose hint talks about
        network access and the model cache; an operator following that hint
        would never find the missing runtime.
        """

        _force_available(monkeypatch, absent="paddle")

        assert PaddleOCRProvider().available is False

    def test_missing_runtime_is_named_in_the_error(self, monkeypatch):
        """
        The error has to say *which* package is absent, not just that OCR is
        unusable — that name is the whole diagnostic value of the message.
        """

        _force_available(monkeypatch, absent="paddle")

        with pytest.raises(VisionError) as excinfo:
            PaddleOCRProvider()._build()

        assert excinfo.value.code == "VISION_OCR_UNAVAILABLE"

        # Compared against the segment after the colon, not the whole message:
        # the prose ahead of it already says "PaddleOCR", so searching the full
        # string could not tell a listed package from a mentioned one.
        listed = excinfo.value.message.split(":", 1)[1].strip()

        assert listed == "paddle not installed."

    def test_model_source_probe_is_disabled_before_import(self, monkeypatch):
        """
        PaddleX probes its model hosts as the package loads, so the switch has
        to be in the environment before ``import paddleocr`` — not merely before
        ``PaddleOCR(...)`` is constructed.

        Asserted by watching the environment at the moment the provider looks
        the package up for import, which is the last point at which setting it
        can still have any effect.
        """

        monkeypatch.delenv(
            paddle_module._MODEL_SOURCE_CHECK_ENV,
            raising=False,
        )

        _force_available(monkeypatch)

        at_import: list[str | None] = []

        real_import = builtins.__import__

        # __import__ is what the `from paddleocr import PaddleOCR` statement
        # inside _build() actually calls — including when the module is already
        # in sys.modules. Failing it keeps this test offline and model-free: the
        # ordering is the whole assertion, and loading paddle costs seconds.
        def fake_import(name: str, *args: Any, **kwargs: Any):
            if name == "paddleocr":
                at_import.append(
                    os.environ.get(paddle_module._MODEL_SOURCE_CHECK_ENV)
                )
                raise ImportError("stopped before loading paddleocr")

            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(VisionError) as excinfo:
            PaddleOCRProvider()._build()

        assert excinfo.value.code == "VISION_OCR_UNAVAILABLE"
        assert at_import == ["True"]

    def test_onednn_is_disabled_when_the_pipeline_is_built(self, monkeypatch):
        """
        oneDNN must be switched off through the constructor.

        PaddleOCR enables it by default on CPU, and paddlepaddle 3.x then cannot
        lower the detection model under the PIR executor — every predict() call
        raises ``NotImplementedError``, which this provider reports as
        ``VISION_OCR_FAILED`` for every image. The environment flag
        ``FLAGS_use_mkldnn=0`` does not help, because PaddleX passes an explicit
        ``run_mode="mkldnn"`` that overrides it. So the kwarg is the fix, and it
        is worth pinning: dropping it silently breaks all text recognition while
        every mocked test in this suite keeps passing.
        """

        captured: dict[str, Any] = {}

        class FakePaddleOCR:
            def __init__(self, **kwargs: Any) -> None:
                captured.update(kwargs)

        module = types.ModuleType("paddleocr")
        module.PaddleOCR = FakePaddleOCR
        module.__version__ = "3.4.1-fake"

        monkeypatch.setitem(sys.modules, "paddleocr", module)
        _force_available(monkeypatch)

        PaddleOCRProvider(language="en")._build()

        assert captured["enable_mkldnn"] is False
        assert captured["lang"] == "en"
        # The three extra models stay off: each is a separate download.
        assert captured["use_doc_orientation_classify"] is False
        assert captured["use_doc_unwarping"] is False
        assert captured["use_textline_orientation"] is False

    def test_version_is_read_from_the_package(self):
        provider = PaddleOCRProvider()

        if not provider.available:
            pytest.skip("paddleocr is not installed")

        import paddleocr

        assert provider.version == str(
            getattr(paddleocr, "__version__", "unknown")
        )

    def test_build_raises_a_specific_error_when_missing(self, monkeypatch):
        _hide_package(monkeypatch, paddle_module, "paddleocr")

        with pytest.raises(VisionError) as excinfo:
            PaddleOCRProvider()._build()

        assert excinfo.value.code == "VISION_OCR_UNAVAILABLE"
        assert excinfo.value.hint is not None

    @pytest.mark.asyncio
    async def test_read_text_surfaces_unavailability(self, monkeypatch, bgr_image):
        """
        The graceful-degradation contract: OCR on a machine without PaddleOCR
        fails with a named error, not an ImportError from deep inside a library.
        """

        _hide_package(monkeypatch, paddle_module, "paddleocr")

        with pytest.raises(VisionError) as excinfo:
            await PaddleOCRProvider().read_text(bgr_image)

        assert excinfo.value.code == "VISION_OCR_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_rejects_none_image(self):
        with pytest.raises(VisionError) as excinfo:
            await PaddleOCRProvider().read_text(None)  # type: ignore[arg-type]

        assert excinfo.value.code == "VISION_INVALID_IMAGE"


# ============================================================================
# PaddleOCR — frame preparation
# ============================================================================


class TestPaddlePrepare:
    @pytest.mark.asyncio
    async def test_bgr_frame_reaches_the_model_unswapped(
        self,
        monkeypatch,
        bgr_image: Image,
    ):
        """
        The channel-order regression.

        PaddleX's reader defaults to ``format="BGR"`` and passes a bare ndarray
        through untouched, so it treats whatever it is handed as already BGR.
        Converting to RGB first — as this provider used to — swaps red and blue
        on every frame before recognition, which degrades accuracy without
        raising anything.
        """

        model = StubOCRModel([])

        await _ocr_with(monkeypatch, model).read_text(bgr_image)

        frame = model.frames[0]

        # Fixture is B=10, G=20, R=30.
        assert tuple(int(v) for v in frame[0, 0]) == (10, 20, 30)

    @pytest.mark.asyncio
    async def test_rgb_input_is_converted_before_inference(self, monkeypatch):
        data = np.zeros((4, 4, 3), dtype=np.uint8)
        data[:, :, 0] = 30   # red, because this image declares RGB
        data[:, :, 1] = 20
        data[:, :, 2] = 10

        model = StubOCRModel([])

        await _ocr_with(monkeypatch, model).read_text(
            Image(data=data, color_space="rgb")
        )

        assert tuple(
            int(v) for v in model.frames[0][0, 0]
        ) == (10, 20, 30)

    @pytest.mark.asyncio
    async def test_alpha_is_dropped(self, monkeypatch):
        data = np.zeros((4, 4, 4), dtype=np.uint8)
        data[:, :, 3] = 255

        model = StubOCRModel([])

        await _ocr_with(monkeypatch, model).read_text(
            Image.from_numpy(data)
        )

        assert model.frames[0].shape == (4, 4, 3)

    @pytest.mark.asyncio
    async def test_grayscale_is_expanded_to_three_channels(self, monkeypatch):
        model = StubOCRModel([])

        await _ocr_with(monkeypatch, model).read_text(
            Image.from_numpy(
                np.full((6, 8), 128, dtype=np.uint8)
            )
        )

        frame = model.frames[0]

        assert frame.shape == (6, 8, 3)
        assert int(frame[0, 0, 0]) == 128

    @pytest.mark.asyncio
    async def test_frame_is_contiguous(self, monkeypatch, bgr_image: Image):
        """
        The native recognition model reads the buffer directly; a view with
        negative or non-standard strides is a segfault risk.
        """

        model = StubOCRModel([])

        await _ocr_with(monkeypatch, model).read_text(bgr_image)

        assert model.frames[0].flags["C_CONTIGUOUS"]

    @pytest.mark.asyncio
    async def test_rejects_non_uint8_data(self, monkeypatch):
        model = StubOCRModel([])

        with pytest.raises(VisionError) as excinfo:
            await _ocr_with(monkeypatch, model).read_text(
                Image.from_numpy(
                    np.zeros((4, 4, 3), dtype=np.float32)
                )
            )

        assert excinfo.value.code == "VISION_INVALID_IMAGE"
        # Rejected before the model was ever asked to run.
        assert model.frames == []


# ============================================================================
# PaddleOCR — result parsing
# ============================================================================


_FIELDS: dict[str, Any] = {
    "rec_texts": ["AETHEROS", "VISION TEST"],
    "rec_scores": [0.99, 0.95],
    "rec_boxes": [
        [30, 20, 240, 70],
        [30, 110, 300, 160],
    ],
}


class TestPaddleParsing:
    @pytest.mark.asyncio
    async def test_parses_a_dict_result(self, monkeypatch, bgr_image: Image):
        model = StubOCRModel([dict(_FIELDS)])

        blocks = await _ocr_with(monkeypatch, model).read_text(bgr_image)

        assert [block.text for block in blocks] == [
            "AETHEROS",
            "VISION TEST",
        ]

        assert blocks[0].confidence == pytest.approx(0.99)
        assert blocks[0].bbox == (30, 20, 240, 70)

    @pytest.mark.asyncio
    async def test_parses_the_json_envelope(
        self,
        monkeypatch,
        bgr_image: Image,
    ):
        """
        The empty-result regression: fields live under ``json["res"]``, so a
        provider reading ``json["rec_texts"]`` finds nothing and reports no text
        for every image while raising no error.
        """

        model = StubOCRModel([EnvelopeResult(dict(_FIELDS))])

        blocks = await _ocr_with(monkeypatch, model).read_text(bgr_image)

        assert [block.text for block in blocks] == [
            "AETHEROS",
            "VISION TEST",
        ]

    @pytest.mark.asyncio
    async def test_falls_back_to_polygons(self, monkeypatch, bgr_image: Image):
        """
        ``rec_boxes`` comes back empty when document preprocessing is disabled —
        which it is, deliberately — leaving the four-point polygons as the only
        source of coordinates.
        """

        model = StubOCRModel(
            [
                {
                    "rec_texts": ["AETHEROS"],
                    "rec_scores": [0.9],
                    "rec_boxes": [],
                    "rec_polys": [
                        [[30, 20], [240, 22], [238, 70], [31, 68]],
                    ],
                }
            ]
        )

        blocks = await _ocr_with(monkeypatch, model).read_text(bgr_image)

        assert blocks[0].bbox == (30, 20, 240, 70)

    @pytest.mark.asyncio
    async def test_normalises_inverted_boxes(
        self,
        monkeypatch,
        bgr_image: Image,
    ):
        model = StubOCRModel(
            [
                {
                    "rec_texts": ["X"],
                    "rec_scores": [0.5],
                    "rec_boxes": [[240, 70, 30, 20]],
                }
            ]
        )

        blocks = await _ocr_with(monkeypatch, model).read_text(bgr_image)

        assert blocks[0].bbox == (30, 20, 240, 70)
        assert blocks[0].width > 0
        assert blocks[0].height > 0

    @pytest.mark.asyncio
    async def test_skips_empty_strings(self, monkeypatch, bgr_image: Image):
        model = StubOCRModel(
            [
                {
                    "rec_texts": ["", "REAL"],
                    "rec_scores": [0.1, 0.9],
                    "rec_boxes": [[0, 0, 5, 5], [10, 10, 20, 20]],
                }
            ]
        )

        blocks = await _ocr_with(monkeypatch, model).read_text(bgr_image)

        assert [block.text for block in blocks] == ["REAL"]

    @pytest.mark.asyncio
    async def test_parses_the_legacy_2x_shape(
        self,
        monkeypatch,
        bgr_image: Image,
    ):
        model = StubOCRModel(
            [
                [
                    [
                        [[30, 20], [240, 20], [240, 70], [30, 70]],
                        ("AETHEROS", 0.98),
                    ],
                ]
            ]
        )

        blocks = await _ocr_with(monkeypatch, model).read_text(bgr_image)

        assert blocks[0].text == "AETHEROS"
        assert blocks[0].confidence == pytest.approx(0.98)
        assert blocks[0].bbox == (30, 20, 240, 70)

    @pytest.mark.asyncio
    async def test_empty_model_output_is_an_empty_list(
        self,
        monkeypatch,
        bgr_image: Image,
    ):
        model = StubOCRModel([])

        assert await _ocr_with(monkeypatch, model).read_text(bgr_image) == []

    @pytest.mark.asyncio
    async def test_none_entries_are_skipped(
        self,
        monkeypatch,
        bgr_image: Image,
    ):
        """
        PaddleOCR 2.x returned ``[None]`` for a page with no text at all.
        """

        model = StubOCRModel([None])

        assert await _ocr_with(monkeypatch, model).read_text(bgr_image) == []

    @pytest.mark.asyncio
    async def test_unrecognised_result_shape_yields_nothing(
        self,
        monkeypatch,
        bgr_image: Image,
    ):
        model = StubOCRModel(["not a result"])

        assert await _ocr_with(monkeypatch, model).read_text(bgr_image) == []


# ============================================================================
# PaddleOCR — failure and lifecycle
# ============================================================================


class TestPaddleFailures:
    @pytest.mark.asyncio
    async def test_inference_failure_becomes_a_vision_error(
        self,
        monkeypatch,
        bgr_image: Image,
    ):
        model = StubOCRModel([], error=RuntimeError("kernel crash"))

        with pytest.raises(VisionError) as excinfo:
            await _ocr_with(monkeypatch, model).read_text(bgr_image)

        assert excinfo.value.code == "VISION_OCR_FAILED"
        assert isinstance(excinfo.value.cause, RuntimeError)
        # The failing frame's dimensions are recorded; the pixels are not.
        assert excinfo.value.context.details["width"] == bgr_image.width

    @pytest.mark.asyncio
    async def test_model_is_built_once(self, monkeypatch, bgr_image: Image):
        model = StubOCRModel([])

        provider = PaddleOCRProvider()

        builds = {"count": 0}

        def build():
            builds["count"] += 1
            return model

        monkeypatch.setattr(provider, "_build", build)

        await provider.read_text(bgr_image)
        await provider.read_text(bgr_image)

        assert builds["count"] == 1

    def test_close_before_any_use_is_a_noop(self):
        PaddleOCRProvider().close()

    @pytest.mark.asyncio
    async def test_close_releases_the_model(
        self,
        monkeypatch,
        bgr_image: Image,
    ):
        model = StubOCRModel([])

        provider = _ocr_with(monkeypatch, model)

        await provider.read_text(bgr_image)

        provider.close()

        assert model.closed is True
        assert provider._ocr is None

    @pytest.mark.asyncio
    async def test_close_survives_a_stuck_model(
        self,
        monkeypatch,
        bgr_image: Image,
    ):
        """
        Shutdown must not raise: a model that will not release its handle would
        otherwise mask whatever the process was shutting down for.
        """

        class StubbornModel(StubOCRModel):
            def close(self) -> None:
                raise RuntimeError("handle is stuck")

        model = StubbornModel([])

        provider = _ocr_with(monkeypatch, model)

        await provider.read_text(bgr_image)

        provider.close()

        assert provider._ocr is None


# ============================================================================
# YOLO detection
# ============================================================================


class TestYOLOProvider:
    def test_metadata(self):
        provider = YOLOProvider()

        assert provider.name == "Ultralytics YOLO"
        assert provider.weights.name == "yolo11n.pt"

    def test_unavailable_without_the_package(self, monkeypatch):
        _hide_package(monkeypatch, yolo_module, "ultralytics")

        provider = YOLOProvider()

        assert provider.available is False
        assert provider.version == "unavailable"

    def test_unavailable_without_weights(self, monkeypatch, tmp_path):
        _show_package(monkeypatch, yolo_module, "ultralytics")

        provider = YOLOProvider(model=tmp_path / "absent.pt")

        assert provider.available is False

    def test_available_with_package_and_weights(self, monkeypatch, tmp_path):
        _show_package(monkeypatch, yolo_module, "ultralytics")

        weights = tmp_path / "present.pt"
        weights.write_bytes(b"not really weights")

        assert YOLOProvider(model=weights).available is True

    def test_allow_download_reports_available(self, monkeypatch, tmp_path):
        _show_package(monkeypatch, yolo_module, "ultralytics")

        provider = YOLOProvider(
            model=tmp_path / "absent.pt",
            allow_download=True,
        )

        assert provider.available is True

    @pytest.mark.asyncio
    async def test_missing_package_error(self, monkeypatch, bgr_image: Image):
        _hide_package(monkeypatch, yolo_module, "ultralytics")

        with pytest.raises(VisionError) as excinfo:
            await YOLOProvider().detect(bgr_image)

        assert excinfo.value.code == "VISION_DETECTION_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_missing_weights_error(
        self,
        monkeypatch,
        tmp_path,
        bgr_image: Image,
    ):
        """
        Weights are never fetched implicitly: a silent download would put an
        internet dependency into startup and into the test suite.
        """

        _show_package(monkeypatch, yolo_module, "ultralytics")

        with pytest.raises(VisionError) as excinfo:
            await YOLOProvider(model=tmp_path / "absent.pt").detect(bgr_image)

        assert excinfo.value.code == "VISION_DETECTION_MODEL_MISSING"
        assert excinfo.value.hint is not None

    @pytest.mark.asyncio
    async def test_rejects_none_image(self):
        with pytest.raises(VisionError) as excinfo:
            await YOLOProvider().detect(None)  # type: ignore[arg-type]

        assert excinfo.value.code == "VISION_INVALID_IMAGE"

    def test_close_before_use_is_a_noop(self):
        YOLOProvider().close()
