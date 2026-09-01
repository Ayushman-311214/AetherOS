"""
Fixtures for the vision test suite.

The fakes here implement the real provider interfaces rather than using
``MagicMock``. A MagicMock accepts any call at all, so it cannot catch the class
of bug this suite exists to prevent — a service calling a method the interface
does not have, or handing a provider a raw ndarray where an :class:`Image` is
required. Subclassing the ABC means a fake stops working the moment the
interface changes, which is the point.

Only the layers that are genuinely external are faked: the OCR model and the OS
screen grab. Everything that *is* the vision engine — ``Image``,
``VisionService``, the OpenCV providers — is the real implementation under test.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from aetheros.core.container.container import ServiceContainer
from aetheros.core.container.registry import container
from aetheros.core.interfaces.screen_controller import ScreenController
from aetheros.vision.controller import VisionService
from aetheros.vision.image import Image
from aetheros.vision.models import Detection, TextBlock
from aetheros.vision.providers.base import (
    DetectionProvider,
    OCRProvider,
)
from aetheros.vision.providers.opencv_provider import OpenCVProvider
from aetheros.vision.providers.template_provider import OpenCVTemplateProvider


# ==============================================================
# Fake OCR backend
# ==============================================================


class FakeOCRProvider(OCRProvider):
    """
    An OCR provider that returns pre-set blocks instead of running a model.

    Records every image it was given so a test can assert the service passed
    through the object it was handed, not a copy or a bare array.
    """

    def __init__(
        self,
        blocks: list[TextBlock] | None = None,
        *,
        available: bool = True,
        error: Exception | None = None,
        version: str = "fake-1.0",
    ) -> None:

        self._blocks = list(blocks or [])
        self._available = available
        self._error = error
        self._version = version

        self.calls: list[Image] = []
        self.closed = False

    @property
    def name(self) -> str:
        return "FakeOCR"

    @property
    def version(self) -> str:
        return self._version

    @property
    def available(self) -> bool:
        return self._available

    async def read_text(self, image: Image) -> list[TextBlock]:

        self.calls.append(image)

        if self._error is not None:
            raise self._error

        return list(self._blocks)

    def close(self) -> None:
        self.closed = True


class UnclosableOCRProvider(FakeOCRProvider):
    """
    Raises from ``close()``.

    Shutdown must survive a provider that cannot release its model.
    """

    def close(self) -> None:
        raise RuntimeError("model handle is stuck")


# ==============================================================
# Fake detection backend
# ==============================================================


class FakeDetectionProvider(DetectionProvider):

    def __init__(
        self,
        detections: list[Detection] | None = None,
        *,
        available: bool = True,
        error: Exception | None = None,
    ) -> None:

        self._detections = list(detections or [])
        self._available = available
        self._error = error

        self.calls: list[Image] = []
        self.closed = False

    @property
    def name(self) -> str:
        return "FakeDetector"

    @property
    def version(self) -> str:
        return "fake-1.0"

    @property
    def available(self) -> bool:
        return self._available

    async def detect(self, image: Image) -> list[Detection]:

        self.calls.append(image)

        if self._error is not None:
            raise self._error

        return list(self._detections)

    def close(self) -> None:
        self.closed = True


# ==============================================================
# Fake screen backend
# ==============================================================


class FakeScreen(ScreenController):
    """
    A screen controller backed by a fixed array instead of a display.

    Lets the capture path be exercised on a headless machine and makes the
    "screen" deterministic, which a real grab never is.
    """

    def __init__(
        self,
        frame: np.ndarray | None = None,
        *,
        error: Exception | None = None,
        size: tuple[int, int] = (320, 240),
    ) -> None:

        self._frame = (
            frame
            if frame is not None
            else np.zeros((size[1], size[0], 3), dtype=np.uint8)
        )

        self._error = error
        self._size = size

        self.captures = 0
        self.regions: list[tuple[int, int, int, int]] = []
        self.saved: list[Path] = []
        self.closed = False

    def capture(self) -> np.ndarray:

        if self._error is not None:
            raise self._error

        self.captures += 1

        return self._frame.copy()

    def capture_region(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> np.ndarray:

        if self._error is not None:
            raise self._error

        self.regions.append((left, top, width, height))

        return self._frame[
            top: top + height,
            left: left + width,
        ].copy()

    def save(
        self,
        image: np.ndarray,
        path: str | Path,
    ) -> None:

        if self._error is not None:
            raise self._error

        self.saved.append(Path(path))

    def size(self) -> tuple[int, int]:
        return self._size

    def monitors(self) -> list[dict[str, Any]]:
        return [
            {
                "index": 0,
                "left": 0,
                "top": 0,
                "width": self._size[0],
                "height": self._size[1],
            }
        ]

    def close(self) -> None:
        self.closed = True


# ==============================================================
# Image fixtures
# ==============================================================


@pytest.fixture
def bgr_image() -> Image:
    """
    A small BGR image whose channels are all different.

    Uniform grey would hide a channel swap; distinct per-channel values make a
    BGR/RGB mix-up visible in an assertion.
    """

    data = np.zeros((8, 12, 3), dtype=np.uint8)

    data[:, :, 0] = 10   # blue
    data[:, :, 1] = 20   # green
    data[:, :, 2] = 30   # red

    return Image.from_numpy(data, source="fixture", color_space="bgr")


@pytest.fixture
def sample_blocks() -> list[TextBlock]:

    return [
        TextBlock(
            text="AETHEROS",
            confidence=0.99,
            left=10,
            top=10,
            right=210,
            bottom=60,
        ),
        TextBlock(
            text="VISION TEST",
            confidence=0.95,
            left=10,
            top=70,
            right=260,
            bottom=120,
        ),
    ]


# ==============================================================
# Service fixtures
# ==============================================================


@pytest.fixture
def fake_ocr(sample_blocks: list[TextBlock]) -> FakeOCRProvider:

    return FakeOCRProvider(sample_blocks)


@pytest.fixture
def vision_service(fake_ocr: FakeOCRProvider) -> VisionService:
    """
    A real VisionService with a fake OCR backend.

    The OpenCV and template providers are the real ones: OpenCV is a local
    library with no model download and no network, so faking it would only
    reduce what the tests actually check.
    """

    return VisionService(
        ocr=fake_ocr,
        cv=OpenCVProvider(),
        template=OpenCVTemplateProvider(),
    )


@pytest.fixture
def make_vision_service():
    """
    Factory for services with a specific provider mix (factory-as-fixture).
    """

    def factory(
        *,
        ocr: OCRProvider | None = None,
        detector: DetectionProvider | None = None,
        template: Any = "default",
    ) -> VisionService:

        return VisionService(
            ocr=ocr or FakeOCRProvider(),
            cv=OpenCVProvider(),
            detector=detector,
            template=(
                OpenCVTemplateProvider()
                if template == "default"
                else template
            ),
        )

    return factory


# ==============================================================
# Container fixtures
# ==============================================================


@pytest.fixture
def isolated_container() -> Iterator[ServiceContainer]:
    """
    Yield the process-wide container with its registrations saved and restored.

    Vision tools resolve their services from the module-level ``container``
    singleton by design, so a tool test has to register into that exact object.
    Snapshotting the three registration dicts keeps the mutation from leaking
    into the rest of the session.
    """

    saved = (
        dict(container._singletons),
        dict(container._singleton_factories),
        dict(container._factories),
    )

    container.clear()

    try:
        yield container

    finally:
        container.clear()

        container._singletons.update(saved[0])
        container._singleton_factories.update(saved[1])
        container._factories.update(saved[2])


@pytest.fixture
def wired_container(
    isolated_container: ServiceContainer,
    vision_service: VisionService,
) -> ServiceContainer:
    """
    A container holding the fake-backed VisionService and a fake ScreenService.

    This is what lets the @tool functions run without a display or an OCR model
    while still executing their real bodies.
    """

    from aetheros.desktop.screen.controller import ScreenService

    screen = ScreenService(FakeScreen())

    isolated_container.register_singleton(
        VisionService,
        lambda: vision_service,
    )

    isolated_container.register_singleton(
        ScreenService,
        lambda: screen,
    )

    return isolated_container


# ==============================================================
# Fake classes, as fixtures
# ==============================================================
#
# Exposed through fixtures rather than imported from this module directly:
# tests/ has no __init__.py, so `from .conftest import ...` has no parent package
# to resolve against. This is also the pattern tests/llm/conftest.py uses for
# FakeLLMProvider.


@pytest.fixture
def make_fake_ocr() -> type[FakeOCRProvider]:
    return FakeOCRProvider


@pytest.fixture
def make_unclosable_ocr() -> type[UnclosableOCRProvider]:
    return UnclosableOCRProvider


@pytest.fixture
def make_fake_detector() -> type[FakeDetectionProvider]:
    return FakeDetectionProvider


@pytest.fixture
def make_fake_screen() -> type[FakeScreen]:
    return FakeScreen
