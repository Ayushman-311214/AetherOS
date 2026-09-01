"""
Tests for vision's bootstrap and dependency-injection wiring.

These call the individual ``_bootstrap_*`` steps rather than ``start()``. The full
startup sequence also initialises the LLM layer, which reads provider credentials
from the environment and issues a health check over the network — a test suite
must not depend on either. The vision steps themselves are offline and
display-free, which is exactly the property being asserted here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from aetheros.bootstrap.bootstrapper import Bootstrapper
from aetheros.core.errors.vision_error import VisionError
from aetheros.desktop.screen import mss_backend
from aetheros.desktop.screen.controller import ScreenService
from aetheros.tools.registry import tool_registry
from aetheros.vision.controller import VisionService
from aetheros.vision.providers.opencv_provider import OpenCVProvider
from aetheros.vision.providers.paddleocr_provider import PaddleOCRProvider
from aetheros.vision.providers.template_provider import OpenCVTemplateProvider
from aetheros.vision.providers.yolo_provider import YOLOProvider

_HAS_PYAUTOGUI = importlib.util.find_spec("pyautogui") is not None


@pytest.fixture
def bootstrapper(isolated_container, monkeypatch) -> Bootstrapper:
    """
    A bootstrapper over the isolated container, with detection opted out.

    ``Bootstrapper.__init__`` binds the process-wide container, which
    ``isolated_container`` has already emptied and will restore. Clearing
    AETHEROS_YOLO_WEIGHTS keeps the default path deterministic on a developer
    machine that happens to have weights configured.
    """

    monkeypatch.delenv("AETHEROS_YOLO_WEIGHTS", raising=False)

    return Bootstrapper()


# ============================================================================
# Vision registration
# ============================================================================


class TestVisionBootstrap:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "service",
        [
            VisionService,
            OpenCVProvider,
            OpenCVTemplateProvider,
            PaddleOCRProvider,
        ],
    )
    async def test_registers_the_service(self, bootstrapper, service):
        await bootstrapper._bootstrap_vision()

        assert bootstrapper.container.has(service)

    @pytest.mark.asyncio
    async def test_vision_service_resolves(self, bootstrapper):
        await bootstrapper._bootstrap_vision()

        assert isinstance(
            bootstrapper.container.resolve(VisionService),
            VisionService,
        )

    @pytest.mark.asyncio
    async def test_registration_is_lazy(self, bootstrapper):
        """
        Nothing may be constructed at registration time. An eagerly built
        VisionService would drag in the OCR provider, and shutdown would then
        have to load a model purely in order to close it.
        """

        await bootstrapper._bootstrap_vision()

        assert bootstrapper.container.is_instantiated(VisionService) is False

    @pytest.mark.asyncio
    async def test_vision_service_is_a_singleton(self, bootstrapper):
        await bootstrapper._bootstrap_vision()

        first = bootstrapper.container.resolve(VisionService)
        second = bootstrapper.container.resolve(VisionService)

        assert first is second

    @pytest.mark.asyncio
    async def test_providers_are_not_duplicated(self, bootstrapper):
        """
        The service must be wired with the *registered* provider instances.

        Constructing its own would give the process two PaddleOCR providers and
        therefore two loaded models — the kind of duplication that shows up as
        doubled memory rather than as a failure. There is no public accessor for
        the wired providers, so the private attributes are read directly.
        """

        await bootstrapper._bootstrap_vision()

        container = bootstrapper.container

        service = container.resolve(VisionService)

        assert service._ocr is container.resolve(PaddleOCRProvider)
        assert service._cv is container.resolve(OpenCVProvider)
        assert service._template is container.resolve(OpenCVTemplateProvider)

    @pytest.mark.asyncio
    async def test_running_twice_is_harmless(self, bootstrapper):
        """
        Registration overwrites rather than raising, so a re-entered bootstrap
        must not leave the container half-configured.
        """

        await bootstrapper._bootstrap_vision()
        await bootstrapper._bootstrap_vision()

        assert isinstance(
            bootstrapper.container.resolve(VisionService),
            VisionService,
        )

    @pytest.mark.asyncio
    async def test_does_not_need_screen_capture(self, bootstrapper):
        """
        Vision must come up on a machine with no display. Only the capture-based
        tools depend on ScreenService, and they fail individually.
        """

        await bootstrapper._bootstrap_vision()

        assert bootstrapper.container.has(ScreenService) is False
        assert bootstrapper.container.resolve(VisionService).has_template is True

    @pytest.mark.asyncio
    async def test_capabilities_are_reported(self, bootstrapper):
        await bootstrapper._bootstrap_vision()

        capabilities = bootstrapper.container.resolve(
            VisionService
        ).capabilities()

        assert capabilities["image_processing"] is True
        assert capabilities["template"] is True
        assert capabilities["detection"] is False


# ============================================================================
# Optional object detection
# ============================================================================


class TestDetectorBootstrap:
    def test_disabled_without_configured_weights(self, bootstrapper):
        """
        ultralytics downloads weights on first use, so detection stays off until
        a path is configured — startup must never reach for the network.
        """

        assert bootstrapper._build_detector() is None

    def test_disabled_when_weights_are_missing(
        self,
        bootstrapper,
        monkeypatch,
        tmp_path: Path,
    ):
        monkeypatch.setenv(
            "AETHEROS_YOLO_WEIGHTS",
            str(tmp_path / "absent.pt"),
        )

        assert bootstrapper._build_detector() is None

    def test_detector_is_not_registered_when_disabled(self, bootstrapper):
        bootstrapper._build_detector()

        assert bootstrapper.container.has(YOLOProvider) is False

    @pytest.mark.asyncio
    async def test_service_reports_detection_off(
        self,
        bootstrapper,
        bgr_image,
    ):
        await bootstrapper._bootstrap_vision()

        service = bootstrapper.container.resolve(VisionService)

        assert service.has_detector is False

        # A refusal, not a silent empty result an agent would read as "nothing
        # on screen".
        with pytest.raises(VisionError) as excinfo:
            await service.detect_objects(bgr_image)

        assert excinfo.value.code == "VISION_DETECTION_UNAVAILABLE"


# ============================================================================
# Tool registration
# ============================================================================


@pytest.mark.skipif(
    not _HAS_PYAUTOGUI,
    reason="the tool bootstrap imports the pyautogui-backed desktop tools",
)
class TestToolBootstrap:
    @pytest.mark.asyncio
    async def test_registers_the_vision_category(self, bootstrapper):
        await bootstrapper._bootstrap_tools()

        assert "vision" in tool_registry.categories()

    @pytest.mark.asyncio
    async def test_registers_the_screen_category(self, bootstrapper):
        """
        Vision's screen-reading tools are useless without capture tools beside
        them, and both are imported by the same bootstrap step.
        """

        await bootstrapper._bootstrap_tools()

        assert "desktop.screen" in tool_registry.categories()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "name",
        [
            "read_screen_text",
            "read_image_text",
            "detect_screen_objects",
            "find_text",
            "analyze_screen",
        ],
    )
    async def test_vision_tool_is_discoverable(self, bootstrapper, name):
        await bootstrapper._bootstrap_tools()

        assert tool_registry.exists(name)

    @pytest.mark.asyncio
    async def test_running_twice_does_not_double_register(self, bootstrapper):
        """
        The registry raises on a duplicate name, so a second bootstrap would
        abort startup if the tool modules were re-executed.
        """

        await bootstrapper._bootstrap_tools()

        count = tool_registry.count

        await bootstrapper._bootstrap_tools()

        assert tool_registry.count == count


# ============================================================================
# Screen capture registration
# ============================================================================


@pytest.mark.skipif(
    not _HAS_PYAUTOGUI,
    reason="desktop bootstrap constructs the pyautogui backends",
)
class TestDesktopBootstrap:
    @pytest.mark.asyncio
    async def test_registers_screen_capture(
        self,
        bootstrapper,
        monkeypatch,
        make_fake_screen,
    ):
        """
        ScreenService is what every capture-based vision tool resolves, so its
        registration is part of the vision integration contract.
        """

        screen = make_fake_screen()

        monkeypatch.setattr(
            mss_backend,
            "MSSScreen",
            lambda: screen,
        )

        await bootstrapper._bootstrap_desktop()

        assert bootstrapper.container.has(ScreenService)

        assert await bootstrapper.container.resolve(
            ScreenService
        ).size() == (320, 240)

    @pytest.mark.asyncio
    async def test_headless_machine_still_boots(
        self,
        bootstrapper,
        monkeypatch,
    ):
        """
        mss raises without a display. Startup must survive that: the
        trading-analysis core does not need a screen, and only the capture tools
        should lose functionality.
        """

        def unavailable():
            raise VisionError(
                code="SCREEN_UNAVAILABLE",
                message="no display",
            )

        monkeypatch.setattr(mss_backend, "MSSScreen", unavailable)

        await bootstrapper._bootstrap_desktop()

        assert bootstrapper.container.has(ScreenService) is False

    @pytest.mark.asyncio
    async def test_unexpected_capture_failure_is_not_swallowed(
        self,
        bootstrapper,
        monkeypatch,
    ):
        """
        Only VisionError means "no display". Anything else is a real defect and
        must not be hidden behind the headless fallback.
        """

        def broken():
            raise RuntimeError("mss is mis-installed")

        monkeypatch.setattr(mss_backend, "MSSScreen", broken)

        with pytest.raises(RuntimeError):
            await bootstrapper._bootstrap_desktop()


# ============================================================================
# Shutdown
# ============================================================================


class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_without_a_resolved_service_is_a_no_op(
        self,
        bootstrapper,
    ):
        """
        Shutdown must not resolve VisionService just to close it — that would
        build an OCR model on the way out of the process.
        """

        await bootstrapper._bootstrap_vision()

        await bootstrapper._shutdown_vision()

        assert bootstrapper.container.is_instantiated(VisionService) is False

    @pytest.mark.asyncio
    async def test_shutdown_closes_a_resolved_service(
        self,
        bootstrapper,
        make_fake_ocr,
    ):
        ocr = make_fake_ocr()

        await bootstrapper._bootstrap_vision()

        bootstrapper.container.register_singleton(
            VisionService,
            lambda: VisionService(
                ocr=ocr,
                cv=OpenCVProvider(),
                template=OpenCVTemplateProvider(),
            ),
        )

        bootstrapper.container.resolve(VisionService)

        await bootstrapper._shutdown_vision()

        assert ocr.closed is True

    @pytest.mark.asyncio
    async def test_shutdown_survives_a_failing_provider(
        self,
        bootstrapper,
        make_unclosable_ocr,
    ):
        bootstrapper.container.register_singleton(
            VisionService,
            lambda: VisionService(
                ocr=make_unclosable_ocr(),
                cv=OpenCVProvider(),
            ),
        )

        bootstrapper.container.resolve(VisionService)

        await bootstrapper._shutdown_vision()

    @pytest.mark.asyncio
    async def test_shutdown_with_nothing_registered(self, bootstrapper):
        await bootstrapper._shutdown_vision()
        await bootstrapper._shutdown_desktop()

    @pytest.mark.asyncio
    async def test_shutdown_clears_the_container(self, bootstrapper):
        """
        The container is process-wide. Leaving resolved singletons behind would
        let a later start() hand out instances that had already been closed.
        """

        await bootstrapper._bootstrap_vision()

        bootstrapper.container.resolve(VisionService)

        await bootstrapper._shutdown_container()

        assert bootstrapper.container is None
