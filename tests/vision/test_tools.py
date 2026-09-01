"""
Tests for the vision tools and their registry integration.

These exercise the real tool bodies. The only substitutions are the two genuinely
external dependencies — the OCR model and the OS screen grab — which are supplied
through the DI container exactly as bootstrap supplies the real ones. So a tool
resolving the wrong service, returning something the LLM layer cannot encode, or
letting a backend failure escape as an unhandled exception all fail here.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

# Importing the module is what registers the tools — the @tool decorator runs at
# import time. Bootstrap does the same thing; see _bootstrap_tools.
import aetheros.vision.tools as vision_tools
from aetheros.core.errors.tool_error import ToolError
from aetheros.core.errors.vision_error import VisionError
from aetheros.desktop.screen.controller import ScreenService
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import tool_registry
from aetheros.tools.schema import schema_generator
from aetheros.vision import selfcheck
from aetheros.vision.controller import VisionService
from aetheros.vision.image import Image
from aetheros.vision.models import Detection
from aetheros.vision.providers.opencv_provider import OpenCVProvider
from aetheros.vision.providers.template_provider import OpenCVTemplateProvider


VISION_TOOL_NAMES = (
    "read_screen_text",
    "read_image_text",
    "detect_screen_objects",
    "find_text",
    "analyze_screen",
)


# ============================================================================
# Wiring
# ============================================================================


@pytest.fixture
def executor() -> ToolExecutor:
    """
    An executor over the process-wide registry, which is where @tool registers.
    """

    return ToolExecutor()


@pytest.fixture
def wire(isolated_container, make_fake_ocr, make_fake_screen, sample_blocks):
    """
    Register a VisionService and a ScreenService with chosen backends.

    Mirrors what ``_bootstrap_vision`` and ``_bootstrap_desktop`` register, so
    the tools resolve their dependencies through the same container lookup they
    use in production.
    """

    def _wire(
        *,
        ocr: Any = None,
        detector: Any = None,
        screen: Any = None,
    ) -> SimpleNamespace:

        ocr = make_fake_ocr(sample_blocks) if ocr is None else ocr
        screen = make_fake_screen() if screen is None else screen

        vision = VisionService(
            ocr=ocr,
            cv=OpenCVProvider(),
            detector=detector,
            template=OpenCVTemplateProvider(),
        )

        screen_service = ScreenService(screen)

        isolated_container.register_singleton(
            VisionService,
            lambda: vision,
        )

        isolated_container.register_singleton(
            ScreenService,
            lambda: screen_service,
        )

        return SimpleNamespace(
            ocr=ocr,
            screen=screen,
            vision=vision,
        )

    return _wire


# ============================================================================
# Registration and discovery
# ============================================================================


class TestRegistration:
    @pytest.mark.parametrize("name", VISION_TOOL_NAMES)
    def test_tool_is_registered(self, name):
        assert name in tool_registry

    @pytest.mark.parametrize("name", VISION_TOOL_NAMES)
    def test_tool_is_in_the_vision_category(self, name):
        """
        The category is how an agent asks for "the vision tools" rather than
        naming each one, so a mis-categorised tool is effectively invisible.
        """

        assert tool_registry.get(name).category == "vision"

    @pytest.mark.parametrize("name", VISION_TOOL_NAMES)
    def test_tool_has_a_description(self, name):
        """
        The description is the only thing the model sees when choosing a tool.
        """

        assert tool_registry.get(name).description.strip()

    @pytest.mark.parametrize("name", VISION_TOOL_NAMES)
    def test_tool_is_enabled(self, name):
        assert tool_registry.get(name).enabled is True

    @pytest.mark.parametrize("name", VISION_TOOL_NAMES)
    def test_tool_is_async(self, name):
        """
        Every vision tool awaits a service. A definition marked sync would be
        pushed onto a worker thread and return an un-awaited coroutine.
        """

        assert tool_registry.get(name).is_async is True

    def test_discoverable_by_category(self):
        discovered = {
            definition.name
            for definition in tool_registry.by_category("vision")
        }

        assert set(VISION_TOOL_NAMES) <= discovered

    def test_registration_is_not_duplicated(self):
        """
        Re-importing the tool module must not register a second copy — the
        registry raises on a duplicate name, which would abort bootstrap.
        """

        before = tool_registry.count

        importlib.import_module(vision_tools.__name__)

        assert tool_registry.count == before

class TestSchema:
    @pytest.mark.parametrize("name", VISION_TOOL_NAMES)
    def test_schema_generates(self, name):
        schema = schema_generator.generate(tool_registry.get(name))

        assert schema["function"]["name"] == name
        assert schema["function"]["parameters"]["type"] == "object"

    def test_screen_tools_take_no_arguments(self):
        schema = schema_generator.generate(
            tool_registry.get("read_screen_text")
        )

        assert schema["function"]["parameters"]["properties"] == {}
        assert schema["function"]["parameters"]["required"] == []

    def test_path_argument_is_typed(self):
        """
        Resolved annotations are what make ``path`` advertise "string" instead of
        falling back to the untyped default.
        """

        parameters = schema_generator.generate(
            tool_registry.get("read_image_text")
        )["function"]["parameters"]

        assert parameters["properties"]["path"] == {"type": "string"}
        assert parameters["required"] == ["path"]

    @pytest.mark.parametrize("name", VISION_TOOL_NAMES)
    def test_schema_is_json_encodable(self, name):
        json.dumps(schema_generator.generate(tool_registry.get(name)))


# ============================================================================
# read_screen_text
# ============================================================================


class TestReadScreenText:
    @pytest.mark.asyncio
    async def test_returns_the_recognised_text(self, executor, wire):
        wire()

        result = await executor.execute("read_screen_text")

        assert result["count"] == 2
        assert result["text"] == "AETHEROS VISION TEST"
        assert result["width"] == 320
        assert result["height"] == 240

    @pytest.mark.asyncio
    async def test_captures_the_screen_once(self, executor, wire):
        wired = wire()

        await executor.execute("read_screen_text")

        assert wired.screen.captures == 1

    @pytest.mark.asyncio
    async def test_hands_the_ocr_backend_an_image(self, executor, wire):
        """
        The regression this guards: the tool used to pass the raw ndarray from
        ScreenService straight to the provider, which failed inside the provider
        with an AttributeError about a missing ``.data``.
        """

        wired = wire()

        await executor.execute("read_screen_text")

        assert len(wired.ocr.calls) == 1
        assert isinstance(wired.ocr.calls[0], Image)

    @pytest.mark.asyncio
    async def test_captured_frame_is_declared_bgr(self, executor, wire):
        """
        A frame tagged RGB here would be channel-swapped on its way to the OCR
        model, and the failure would look like poor recognition accuracy rather
        than a bug.
        """

        wired = wire()

        await executor.execute("read_screen_text")

        assert wired.ocr.calls[0].color_space == "bgr"

    @pytest.mark.asyncio
    async def test_blocks_are_serialised(self, executor, wire):
        wire()

        result = await executor.execute("read_screen_text")

        assert isinstance(result["blocks"][0], dict)
        assert result["blocks"][0]["text"] == "AETHEROS"
        assert "confidence" in result["blocks"][0]

    @pytest.mark.asyncio
    async def test_result_is_json_encodable(self, executor, wire):
        """
        Tool results are JSON-encoded for the model; a stray dataclass or
        ndarray in the payload breaks the whole turn.
        """

        wire()

        result = await executor.execute("read_screen_text")

        json.dumps(result)

    @pytest.mark.asyncio
    async def test_no_text_is_reported_as_empty(
        self,
        executor,
        wire,
        make_fake_ocr,
    ):
        wire(ocr=make_fake_ocr([]))

        result = await executor.execute("read_screen_text")

        assert result["count"] == 0
        assert result["text"] == ""
        assert result["blocks"] == []


# ============================================================================
# read_image_text
# ============================================================================


class TestReadImageText:
    @pytest.mark.asyncio
    async def test_reads_a_file_from_disk(
        self,
        executor,
        wire,
        tmp_path: Path,
    ):
        wired = wire()

        target = tmp_path / "chart.png"
        selfcheck.reference_image().save(target)

        result = await executor.execute(
            "read_image_text",
            {"path": str(target)},
        )

        assert result["path"] == str(target)
        assert result["width"] == 640
        assert result["count"] == 2
        assert len(wired.ocr.calls) == 1

    @pytest.mark.asyncio
    async def test_does_not_touch_the_screen(
        self,
        executor,
        wire,
        tmp_path: Path,
    ):
        """
        Reading a saved image is the path that works on a headless machine, so
        it must not resolve the screen at all.
        """

        wired = wire()

        target = tmp_path / "chart.png"
        selfcheck.reference_image().save(target)

        await executor.execute("read_image_text", {"path": str(target)})

        assert wired.screen.captures == 0

    @pytest.mark.asyncio
    async def test_missing_file_is_reported_as_a_failure(
        self,
        executor,
        wire,
        tmp_path: Path,
    ):
        wire()

        result = await executor.execute_safe(
            "read_image_text",
            {"path": str(tmp_path / "absent.png")},
        )

        assert result.ok is False
        assert result.error_type == "VisionError"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_missing_argument_is_rejected(self, executor, wire):
        wire()

        result = await executor.execute_safe("read_image_text")

        assert result.ok is False
        assert result.error_type == "InvalidArguments"

    @pytest.mark.asyncio
    async def test_wrong_argument_type_is_rejected(self, executor, wire):
        wire()

        result = await executor.execute_safe(
            "read_image_text",
            {"path": 7},
        )

        assert result.ok is False
        assert result.error_type == "InvalidArguments"

    @pytest.mark.asyncio
    async def test_unknown_argument_is_rejected(self, executor, wire):
        wire()

        result = await executor.execute_safe(
            "read_image_text",
            {"filename": "x.png"},
        )

        assert result.ok is False
        assert result.error_type == "InvalidArguments"


# ============================================================================
# find_text
# ============================================================================


class TestFindTextTool:
    @pytest.mark.asyncio
    async def test_reports_a_match(self, executor, wire):
        wire()

        result = await executor.execute("find_text", {"query": "VISION"})

        assert result["query"] == "VISION"
        assert result["found"] is True
        assert result["count"] == 1
        assert result["matches"][0]["text"] == "VISION TEST"

    @pytest.mark.asyncio
    async def test_reports_no_match_without_failing(self, executor, wire):
        """
        "Not on screen" is an answer the agent can act on, not an error.
        """

        wire()

        result = await executor.execute("find_text", {"query": "NIFTY"})

        assert result["found"] is False
        assert result["count"] == 0
        assert result["matches"] == []

    @pytest.mark.asyncio
    async def test_empty_query_is_rejected(self, executor, wire):
        wire()

        result = await executor.execute_safe("find_text", {"query": ""})

        assert result.ok is False
        assert result.error_type == "VisionError"


# ============================================================================
# detect_screen_objects
# ============================================================================


class TestDetectScreenObjects:
    @pytest.mark.asyncio
    async def test_returns_detections(
        self,
        executor,
        wire,
        make_fake_detector,
    ):
        wire(
            detector=make_fake_detector(
                [
                    Detection(
                        label="chart",
                        confidence=0.9,
                        left=0,
                        top=0,
                        right=100,
                        bottom=50,
                    )
                ]
            )
        )

        result = await executor.execute("detect_screen_objects")

        assert result["count"] == 1
        assert result["objects"][0]["label"] == "chart"

        json.dumps(result)

    @pytest.mark.asyncio
    async def test_absent_detector_fails_with_a_clear_error(
        self,
        executor,
        wire,
    ):
        """
        ultralytics and its weights are optional, so the agent has to be told
        the capability is missing rather than shown an empty result it would
        read as "nothing on screen".
        """

        wire()

        result = await executor.execute_safe("detect_screen_objects")

        assert result.ok is False
        assert result.error_type == "VisionError"
        assert "DETECTION_UNAVAILABLE" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_raises_a_tool_error(self, executor, wire):
        """
        execute() is the raising variant; execute_safe() is the one the agent
        loop uses.
        """

        wire()

        with pytest.raises(ToolError):
            await executor.execute("detect_screen_objects")


# ============================================================================
# analyze_screen
# ============================================================================


class TestAnalyzeScreen:
    @pytest.mark.asyncio
    async def test_reports_text_and_capabilities(self, executor, wire):
        wire()

        result = await executor.execute("analyze_screen")

        assert result["text"] == "AETHEROS VISION TEST"
        assert result["capabilities"]["ocr"] is True
        assert result["capabilities"]["detection"] is False

    @pytest.mark.asyncio
    async def test_degrades_instead_of_failing_without_a_detector(
        self,
        executor,
        wire,
    ):
        """
        A missing optional backend must not cost the caller the OCR result it
        would otherwise have got.
        """

        wire()

        result = await executor.execute("analyze_screen")

        assert result["objects"] == []
        assert result["blocks"]

    @pytest.mark.asyncio
    async def test_includes_objects_when_a_detector_exists(
        self,
        executor,
        wire,
        make_fake_detector,
    ):
        wire(
            detector=make_fake_detector(
                [
                    Detection(
                        label="candle",
                        confidence=0.7,
                        left=1,
                        top=2,
                        right=3,
                        bottom=4,
                    )
                ]
            )
        )

        result = await executor.execute("analyze_screen")

        assert result["capabilities"]["detection"] is True
        assert [o["label"] for o in result["objects"]] == ["candle"]

    @pytest.mark.asyncio
    async def test_captures_once_for_both_analyses(
        self,
        executor,
        wire,
        make_fake_detector,
    ):
        """
        Two grabs would be two different moments in a moving market.
        """

        wired = wire(detector=make_fake_detector())

        await executor.execute("analyze_screen")

        assert wired.screen.captures == 1

    @pytest.mark.asyncio
    async def test_result_is_json_encodable(self, executor, wire):
        wire()

        json.dumps(await executor.execute("analyze_screen"))


# ============================================================================
# Failure paths
# ============================================================================


class TestFailureHandling:
    @pytest.mark.asyncio
    async def test_unregistered_service_is_reported_not_raised(
        self,
        executor,
        isolated_container,
    ):
        """
        A vision tool invoked before bootstrap has run. The agent should get a
        readable failure, not an exception that ends the conversation.
        """

        result = await executor.execute_safe("read_screen_text")

        assert result.ok is False
        assert result.error_type == "KeyError"

    @pytest.mark.asyncio
    async def test_capture_failure_surfaces(
        self,
        executor,
        wire,
        make_fake_screen,
    ):
        wire(
            screen=make_fake_screen(
                error=VisionError(
                    code="CAPTURE_FAILED",
                    message="display disappeared",
                )
            )
        )

        result = await executor.execute_safe("read_screen_text")

        assert result.ok is False
        assert "CAPTURE_FAILED" in (result.error or "")

    @pytest.mark.asyncio
    async def test_ocr_failure_surfaces(
        self,
        executor,
        wire,
        make_fake_ocr,
    ):
        wire(
            ocr=make_fake_ocr(
                error=VisionError(
                    code="OCR_INIT_FAILED",
                    message="model weights unavailable",
                )
            )
        )

        result = await executor.execute_safe("read_screen_text")

        assert result.ok is False
        assert result.error_type == "VisionError"
        assert "OCR_INIT_FAILED" in (result.error or "")

    @pytest.mark.asyncio
    async def test_failure_records_a_duration(
        self,
        executor,
        wire,
        make_fake_ocr,
    ):
        """
        The duration is what makes a slow-then-failed tool distinguishable from
        one that failed immediately.
        """

        wire(ocr=make_fake_ocr(error=RuntimeError("boom")))

        result = await executor.execute_safe("read_screen_text")

        assert result.ok is False
        assert result.duration_ms >= 0.0
        assert result.name == "read_screen_text"
