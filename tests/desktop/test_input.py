"""
Regression tests for the mouse and keyboard services, backends and tools.

Every fake in this file subclasses the abstract interface and implements *only*
its abstract methods. That is the whole point rather than a stylistic choice: the
bugs these tests exist to catch were all services reaching past their own
contract.

``KeyboardService.release()`` called ``controller.release()``, which no backend
defines, so the registered ``key_up`` tool raised AttributeError on every call --
and the ``release_modifiers`` recovery strategy, whose only job is to release
stuck modifiers, was dead on arrival. ``KeyboardService.tap()`` called a method
PyAutoGUI's backend happened to define outside the interface, so it worked purely
by luck. A fake that implements the interface and nothing else turns both of
those into an immediate AttributeError.

Nothing here sends real input. The service tests talk to fakes, and the two
backend tests monkeypatch the pyautogui functions they assert on, so no
keystroke or click reaches the machine.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pyautogui
import pytest

# Imported for the side effect: the @tool decorator registers on import, and
# these tests resolve tools out of the process-wide registry by name.
import aetheros.desktop.keyboard.tools  # noqa: F401
import aetheros.desktop.mouse.tools  # noqa: F401
from aetheros.core.container import container
from aetheros.core.interfaces.keyboard_controller import KeyboardController
from aetheros.core.interfaces.mouse_controller import MouseController
from aetheros.desktop.keyboard.controller import KeyboardService
from aetheros.desktop.keyboard.pyautogui_backend import PyAutoGuiKeyboard
from aetheros.desktop.mouse.controller import MouseService
from aetheros.tools.registry import tool_registry


# ==============================================================
# Fakes -- interface surface only, deliberately
# ==============================================================


class FakeKeyboard(KeyboardController):
    """
    Records calls instead of typing.

    Implements exactly the abstract methods, so any service that reaches for a
    method outside the contract fails loudly here.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def write(self, text: str, interval: float = 0.0) -> None:
        self.calls.append(("write", text, interval))

    def press(self, key: str) -> None:
        self.calls.append(("press", key))

    def press_many(self, keys: list[str]) -> None:
        self.calls.append(("press_many", tuple(keys)))

    def key_down(self, key: str) -> None:
        self.calls.append(("key_down", key))

    def key_up(self, key: str) -> None:
        self.calls.append(("key_up", key))

    def hotkey(self, *keys: str) -> None:
        self.calls.append(("hotkey", keys))

    def is_pressed(self, key: str) -> bool:
        self.calls.append(("is_pressed", key))
        return True

    def clear_modifiers(self) -> None:
        self.calls.append(("clear_modifiers",))


class FakeMouse(MouseController):
    """Records calls instead of moving the pointer."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def position(self) -> tuple[int, int]:
        self.calls.append(("position",))
        return (7, 11)

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        self.calls.append(("move_to", x, y, duration))

    def move_relative(self, dx: int, dy: int, duration: float = 0.0) -> None:
        self.calls.append(("move_relative", dx, dy, duration))

    def click(
        self,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
    ) -> None:
        self.calls.append(("click", button, clicks, interval))

    def double_click(self, button: str = "left") -> None:
        self.calls.append(("double_click", button))

    def right_click(self) -> None:
        self.calls.append(("right_click",))

    def middle_click(self) -> None:
        self.calls.append(("middle_click",))

    def drag_to(
        self,
        x: int,
        y: int,
        duration: float = 0.2,
        button: str = "left",
    ) -> None:
        self.calls.append(("drag_to", x, y, duration, button))

    def drag_relative(
        self,
        dx: int,
        dy: int,
        duration: float = 0.2,
        button: str = "left",
    ) -> None:
        self.calls.append(("drag_relative", dx, dy, duration, button))

    def mouse_down(self, button: str = "left") -> None:
        self.calls.append(("mouse_down", button))

    def mouse_up(self, button: str = "left") -> None:
        self.calls.append(("mouse_up", button))

    def scroll(self, clicks: int) -> None:
        self.calls.append(("scroll", clicks))

    def hscroll(self, clicks: int) -> None:
        self.calls.append(("hscroll", clicks))

    def is_pressed(self, button: str) -> bool:
        self.calls.append(("is_pressed", button))
        return False


# ==============================================================
# Fixtures
# ==============================================================


@contextmanager
def _swapped(key: Any, instance: Any) -> Iterator[None]:
    """
    Put a fake-backed service in the container, then put things back.

    Only an *already built* instance is captured for restoration: resolving to
    take the snapshot would construct a registered-but-unused service, and for
    these keys that means building a real PyAutoGUI backend during teardown. A
    registered-but-uninstantiated factory is not restored, which is safe here
    only because the suite never bootstraps.
    """

    previous = container.resolve(key) if container.is_instantiated(key) else None

    # register_singleton takes a factory, not an instance -- it stores the
    # callable and invokes it inside resolve(). Handing it the instance directly
    # would make resolve() try to call the service.
    container.register_singleton(key, lambda: instance)

    try:
        yield

    finally:
        container.remove(key)

        if previous is not None:
            container.register_singleton(key, lambda: previous)


@pytest.fixture
def keyboard() -> Iterator[FakeKeyboard]:
    backend = FakeKeyboard()

    with _swapped(KeyboardService, KeyboardService(backend)):
        yield backend


@pytest.fixture
def mouse() -> Iterator[FakeMouse]:
    backend = FakeMouse()

    with _swapped(MouseService, MouseService(backend)):
        yield backend


async def _call(name: str, **arguments: Any) -> Any:
    """
    Invoke a tool the way the executor does -- by name, out of the registry.

    Going through the registry rather than importing the function asserts the
    tool is actually registered, which is half of what can break.
    """

    return await tool_registry.get(name).function(**arguments)


# ==============================================================
# The contract the services broke
# ==============================================================


class TestFakesConstrainTheServices:

    def test_fakes_expose_nothing_beyond_the_interface(self) -> None:
        """
        Guard the guard.

        If a fake grew a ``release`` or ``tap`` method, every regression test
        below would keep passing while the real defect returned.
        """

        fake = FakeKeyboard()

        assert not hasattr(fake, "release")
        assert not hasattr(fake, "tap")


class TestKeyboardServiceMapsOntoTheInterface:

    @pytest.mark.asyncio
    async def test_key_up_reaches_the_backend(self, keyboard: FakeKeyboard) -> None:
        """
        The original defect: this called ``controller.release()``, which exists
        on no backend, so it raised AttributeError every time.
        """

        service = container.resolve(KeyboardService)

        await service.key_up("ctrl")

        assert keyboard.calls == [("key_up", "ctrl")]

    @pytest.mark.asyncio
    async def test_key_down_holds_rather_than_taps(
        self,
        keyboard: FakeKeyboard,
    ) -> None:
        service = container.resolve(KeyboardService)

        await service.key_down("shift")

        assert keyboard.calls == [("key_down", "shift")]

    @pytest.mark.asyncio
    async def test_press_taps(self, keyboard: FakeKeyboard) -> None:
        service = container.resolve(KeyboardService)

        await service.press("enter")

        assert keyboard.calls == [("press", "enter")]

    @pytest.mark.asyncio
    async def test_clear_modifiers_reaches_the_backend(
        self,
        keyboard: FakeKeyboard,
    ) -> None:
        service = container.resolve(KeyboardService)

        await service.clear_modifiers()

        assert keyboard.calls == [("clear_modifiers",)]


# ==============================================================
# Tools -- what the model actually calls
# ==============================================================


class TestKeyboardTools:

    @pytest.mark.asyncio
    async def test_key_down_tool_holds_the_key(
        self,
        keyboard: FakeKeyboard,
    ) -> None:
        """
        This tool is described to the model as "press and hold", but it called
        ``press()`` -- a press *and release*. So key_down/key_up could never
        compose a held-key sequence, and the description was a lie.
        """

        await _call("key_down", key="shift")

        assert keyboard.calls == [("key_down", "shift")]

    @pytest.mark.asyncio
    async def test_key_up_tool_releases_the_key(
        self,
        keyboard: FakeKeyboard,
    ) -> None:
        await _call("key_up", key="ctrl")

        assert keyboard.calls == [("key_up", "ctrl")]

    @pytest.mark.asyncio
    async def test_press_key_tool_taps(self, keyboard: FakeKeyboard) -> None:
        await _call("press_key", key="escape")

        assert keyboard.calls == [("press", "escape")]

    @pytest.mark.asyncio
    async def test_hotkey_tool_splats_the_key_list(
        self,
        keyboard: FakeKeyboard,
    ) -> None:
        await _call("hotkey", keys=["ctrl", "shift", "s"])

        assert keyboard.calls == [("hotkey", ("ctrl", "shift", "s"))]

    @pytest.mark.asyncio
    async def test_type_text_tool_writes(self, keyboard: FakeKeyboard) -> None:
        await _call("type_text", text="hello", interval=0.01)

        assert keyboard.calls == [("write", "hello", 0.01)]

    @pytest.mark.asyncio
    async def test_clear_input_selects_all_then_deletes(
        self,
        keyboard: FakeKeyboard,
    ) -> None:
        await _call("clear_input")

        assert keyboard.calls == [
            ("hotkey", ("ctrl", "a")),
            ("press", "delete"),
        ]

    @pytest.mark.asyncio
    async def test_clear_modifiers_tool_is_registered_and_works(
        self,
        keyboard: FakeKeyboard,
    ) -> None:
        """
        The ``release_modifiers`` recovery strategy calls this tool by name, so
        an unregistered name would make that strategy report unavailable.
        """

        await _call("clear_modifiers")

        assert keyboard.calls == [("clear_modifiers",)]


class TestMouseTools:

    @pytest.mark.asyncio
    async def test_mouse_down_tool_reaches_the_backend(
        self,
        mouse: FakeMouse,
    ) -> None:
        """
        The backend and interface both had mouse_down; MouseService dropped it,
        so no tool could exist and press-drag-release was unreachable.
        """

        await _call("mouse_down", button="left")

        assert mouse.calls == [("mouse_down", "left")]

    @pytest.mark.asyncio
    async def test_mouse_up_tool_reaches_the_backend(
        self,
        mouse: FakeMouse,
    ) -> None:
        await _call("mouse_up", button="right")

        assert mouse.calls == [("mouse_up", "right")]

    @pytest.mark.asyncio
    async def test_horizontal_scroll_tool_uses_hscroll(
        self,
        mouse: FakeMouse,
    ) -> None:
        await _call("horizontal_scroll", amount=-4)

        assert mouse.calls == [("hscroll", -4)]

    @pytest.mark.asyncio
    async def test_vertical_scroll_is_still_vertical(
        self,
        mouse: FakeMouse,
    ) -> None:
        """
        The pair matters more than either one: a horizontal_scroll wired to
        scroll() would move the wrong axis and read as an unresponsive app.
        """

        await _call("scroll", amount=3)

        assert mouse.calls == [("scroll", 3)]

    @pytest.mark.asyncio
    async def test_drag_relative_tool_reaches_the_backend(
        self,
        mouse: FakeMouse,
    ) -> None:
        await _call("drag_relative", dx=10, dy=-5)

        assert mouse.calls == [("drag_relative", 10, -5, 0.2, "left")]

    @pytest.mark.asyncio
    async def test_mouse_position_tool_reports_coordinates(
        self,
        mouse: FakeMouse,
    ) -> None:
        result = await _call("mouse_position")

        assert result == {"x": 7, "y": 11}


# ==============================================================
# Backend -- pyautogui calls, monkeypatched
# ==============================================================


class TestPyAutoGuiKeyboardBackend:
    """
    Asserts on the pyautogui functions the backend calls. Every function under
    test is replaced, so nothing reaches the real keyboard.
    """

    def test_press_many_presses_each_key_in_turn(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        This called ``pyautogui.hotKey(keys)``, wrong three ways: the function is
        ``hotkey`` (lowercase k), so it raised AttributeError immediately; it
        takes *keys, not a list; and a hotkey holds every key at once, which is
        the opposite of the "sequentially" the interface promises.
        """

        pressed: list[str] = []

        monkeypatch.setattr(pyautogui, "press", pressed.append)

        def forbidden(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("press_many must not go through hotkey")

        monkeypatch.setattr(pyautogui, "hotkey", forbidden)

        PyAutoGuiKeyboard().press_many(["a", "b", "c"])

        assert pressed == ["a", "b", "c"]

    def test_clear_modifiers_releases_both_sides_of_every_modifier(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Both sides deliberately: an interrupted hotkey may have left either the
        left or the right variant down, and releasing the generic name does not
        reliably clear a specific one.
        """

        released: list[str] = []

        monkeypatch.setattr(pyautogui, "keyUp", released.append)

        PyAutoGuiKeyboard().clear_modifiers()

        assert set(released) == {
            "ctrlleft",
            "ctrlright",
            "altleft",
            "altright",
            "shiftleft",
            "shiftright",
            "winleft",
            "winright",
        }

    def test_key_down_and_key_up_map_to_hold_and_release(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        held: list[str] = []
        freed: list[str] = []

        monkeypatch.setattr(pyautogui, "keyDown", held.append)
        monkeypatch.setattr(pyautogui, "keyUp", freed.append)

        backend = PyAutoGuiKeyboard()

        backend.key_down("ctrl")
        backend.key_up("ctrl")

        assert held == ["ctrl"]
        assert freed == ["ctrl"]
