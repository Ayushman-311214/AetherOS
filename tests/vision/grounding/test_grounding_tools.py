"""
Tests for the grounding tools through the registry and executor.

These run the real tool bodies. The only substitutions are the genuinely
external edges -- the OCR model, the OS screen grab, and the mouse/keyboard
actuators -- supplied through the DI container exactly as bootstrap supplies the
real ones. So the guarantees that matter are exercised for real: a grounded
click never lands unless the match was safe, typing never echoes its text back
(it routinely carries secrets), and a failed grounding is a structured
observation the agent can read rather than an exception that ends the turn.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

# Importing the module registers the tools via the @tool decorator, exactly as
# _bootstrap_tools does at startup.
import aetheros.vision.grounding.tools as grounding_tools  # noqa: F401
from aetheros.desktop.keyboard.controller import KeyboardService
from aetheros.desktop.mouse.controller import MouseService
from aetheros.desktop.screen.controller import ScreenService
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import tool_registry
from aetheros.tools.schema import schema_generator
from aetheros.vision.controller import VisionService
from aetheros.vision.models import TextBlock
from aetheros.vision.providers.opencv_provider import OpenCVProvider
from aetheros.vision.providers.template_provider import OpenCVTemplateProvider


GROUNDING_TOOL_NAMES = (
    "ground_target",
    "click_grounded_target",
    "type_into_grounded_target",
)


def _block(text, left, top, right, bottom, confidence=0.95):
    return TextBlock(
        text=text,
        confidence=confidence,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
    )


class RecordingMouse:
    """Records moves and clicks instead of driving a real pointer."""

    def __init__(self) -> None:
        self.moves: list[tuple[int, int]] = []
        self.clicks: list[str] = []

    async def move(self, x: int, y: int, duration: float = 0.0) -> None:
        self.moves.append((x, y))

    async def click(
        self, button: str = "left", clicks: int = 1, interval: float = 0.0
    ) -> None:
        self.clicks.append(button)


class RecordingKeyboard:
    """Records what it was asked to type, so a test can prove the keyboard
    received the real text while the tool payload does not echo it back."""

    def __init__(self) -> None:
        self.texts: list[str] = []

    async def write(self, text: str, interval: float = 0.0) -> None:
        self.texts.append(text)


@pytest.fixture
def executor() -> ToolExecutor:
    return ToolExecutor()


@pytest.fixture
def wire(isolated_container, make_fake_ocr, make_fake_detector, make_fake_screen):
    """Register the services the grounding tools resolve, with fake edges.

    Mirrors what bootstrap registers -- a VisionService, a ScreenService and the
    mouse/keyboard services -- so the tools find their dependencies through the
    same container lookup they use in production.
    """

    def _wire(*, blocks=None, detections=None) -> SimpleNamespace:
        ocr = make_fake_ocr(blocks or [])
        detector = (
            make_fake_detector(detections) if detections is not None else None
        )
        vision = VisionService(
            ocr=ocr,
            cv=OpenCVProvider(),
            detector=detector,
            template=OpenCVTemplateProvider(),
        )
        screen = ScreenService(make_fake_screen())
        mouse = RecordingMouse()
        keyboard = RecordingKeyboard()

        isolated_container.register_singleton(VisionService, lambda: vision)
        isolated_container.register_singleton(ScreenService, lambda: screen)
        isolated_container.register_singleton(MouseService, lambda: mouse)
        isolated_container.register_singleton(KeyboardService, lambda: keyboard)

        return SimpleNamespace(mouse=mouse, keyboard=keyboard, screen=screen)

    return _wire


class TestRegistration:
    @pytest.mark.parametrize("name", GROUNDING_TOOL_NAMES)
    def test_tool_is_registered(self, name):
        assert name in tool_registry

    @pytest.mark.parametrize("name", GROUNDING_TOOL_NAMES)
    def test_tool_is_in_the_grounding_category(self, name):
        assert tool_registry.get(name).category == "vision.grounding"

    @pytest.mark.parametrize("name", GROUNDING_TOOL_NAMES)
    def test_tool_has_a_description(self, name):
        assert tool_registry.get(name).description.strip()

    @pytest.mark.parametrize("name", GROUNDING_TOOL_NAMES)
    def test_tool_is_async(self, name):
        assert tool_registry.get(name).is_async is True


class TestSchema:
    @pytest.mark.parametrize("name", GROUNDING_TOOL_NAMES)
    def test_schema_is_json_encodable(self, name):
        json.dumps(schema_generator.generate(tool_registry.get(name)))

    def test_ground_target_requires_only_the_target(self):
        params = schema_generator.generate(
            tool_registry.get("ground_target")
        )["function"]["parameters"]

        assert params["properties"]["target"] == {"type": "string"}
        assert params["required"] == ["target"]

    def test_type_tool_requires_target_and_text(self):
        params = schema_generator.generate(
            tool_registry.get("type_into_grounded_target")
        )["function"]["parameters"]

        assert set(params["required"]) == {"target", "text"}


class TestGroundTarget:
    @pytest.mark.asyncio
    async def test_returns_a_structured_safe_match(self, executor, wire):
        wire(blocks=[_block("Search", 100, 50, 180, 90)])

        result = await executor.execute(
            "ground_target", {"target": "the Search button"}
        )

        assert result["success"] is True
        assert result["safe_to_act"] is True
        assert result["confidence_band"] == "HIGH"
        assert result["center"] == {"x": 140, "y": 70}
        json.dumps(result)

    @pytest.mark.asyncio
    async def test_grounding_alone_never_actuates_the_mouse(self, executor, wire):
        wired = wire(blocks=[_block("Search", 100, 50, 180, 90)])

        await executor.execute("ground_target", {"target": "the Search button"})

        assert wired.mouse.moves == []
        assert wired.mouse.clicks == []

    @pytest.mark.asyncio
    async def test_not_found_is_a_structured_result_not_an_error(
        self, executor, wire
    ):
        wire(blocks=[_block("File", 0, 0, 40, 20)])

        result = await executor.execute_safe(
            "ground_target", {"target": "Nonexistent"}
        )

        # The tool call itself succeeds; the grounding failed *inside* the result
        # so the agent gets a readable observation, not a raised ToolError.
        assert result.ok is True
        assert result.value["success"] is False
        assert result.value["safe_to_act"] is False
        assert result.value["center"] is None


class TestClickGroundedTarget:
    @pytest.mark.asyncio
    async def test_safe_match_moves_then_clicks(self, executor, wire):
        wired = wire(blocks=[_block("Search", 100, 50, 180, 90)])

        result = await executor.execute(
            "click_grounded_target", {"target": "the Search button"}
        )

        assert result["action"] == "click"
        assert wired.mouse.moves == [(140, 70)]
        assert wired.mouse.clicks == ["left"]

    @pytest.mark.asyncio
    async def test_unsafe_match_does_not_click(self, executor, wire):
        # Two identical "Save" labels -> ambiguous -> not safe_to_act.
        wired = wire(
            blocks=[
                _block("Save", 0, 0, 60, 30),
                _block("Save", 200, 0, 260, 30),
            ]
        )

        result = await executor.execute(
            "click_grounded_target", {"target": "Save"}
        )

        assert result["action"] == "none"
        assert wired.mouse.moves == []
        assert wired.mouse.clicks == []

    @pytest.mark.asyncio
    async def test_not_found_does_not_click(self, executor, wire):
        wired = wire(blocks=[_block("File", 0, 0, 40, 20)])

        result = await executor.execute(
            "click_grounded_target", {"target": "Nonexistent"}
        )

        assert result["success"] is False
        assert result["action"] == "none"
        assert wired.mouse.moves == []


class TestTypeIntoGroundedTarget:
    @pytest.mark.asyncio
    async def test_safe_match_focuses_and_types(self, executor, wire):
        wired = wire(blocks=[_block("Search", 100, 50, 180, 90)])

        result = await executor.execute(
            "type_into_grounded_target",
            {"target": "the Search field", "text": "hunter2secret"},
        )

        assert result["action"] == "type"
        # The keyboard received the real text (typing actually happened)...
        assert wired.keyboard.texts == ["hunter2secret"]
        assert wired.mouse.moves == [(140, 70)]
        assert wired.mouse.clicks == ["left"]

    @pytest.mark.asyncio
    async def test_typed_text_is_never_echoed_in_the_result(self, executor, wire):
        wire(blocks=[_block("Search", 100, 50, 180, 90)])

        result = await executor.execute(
            "type_into_grounded_target",
            {"target": "the Search field", "text": "hunter2secret"},
        )

        # ...but the secret must not appear anywhere in the payload handed back
        # to the model, only its length.
        assert "hunter2secret" not in json.dumps(result)
        assert "13 character" in result["action_reason"]

    @pytest.mark.asyncio
    async def test_unsafe_match_types_nothing(self, executor, wire):
        wired = wire(blocks=[_block("File", 0, 0, 40, 20)])

        result = await executor.execute(
            "type_into_grounded_target",
            {"target": "Nonexistent", "text": "secret"},
        )

        assert result["action"] == "none"
        assert wired.keyboard.texts == []
        assert wired.mouse.moves == []





