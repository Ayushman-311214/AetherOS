"""
Unit tests for :class:`BrowserService`.

The service owns no browser of its own: it coordinates and delegates every
operation to an injected :class:`BrowserProvider`. These tests bind a recording
fake in the provider's place -- the legitimate seam, standing where Playwright
would -- and assert two things the service is actually responsible for:

    * every call reaches the provider, with its arguments intact, and
    * the lifecycle bookkeeping (`launch`/`close`/`shutdown`) is correct, so a
      session that never opened a browser is not torn down as if it had.

Nothing here touches Playwright or a real browser process.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aetheros.browser.controller import BrowserService
from aetheros.browser.providers.base import BrowserProvider


# ==============================================================
# Fake: the provider seam (where Playwright would sit)
# ==============================================================


class _RecordingProvider(BrowserProvider):
    """A ``BrowserProvider`` that records calls instead of driving a browser.

    Every method appends ``(name, args)`` to ``calls``, so a test can prove the
    service delegated -- and the read methods return fixed values so callers can
    assert the service passes them straight back.
    """

    def __init__(self, *, close_error: Exception | None = None) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self._close_error = close_error

    def _record(self, name: str, *args: Any) -> None:
        self.calls.append((name, args))

    @property
    def name(self) -> str:
        return "recording"

    @property
    def version(self) -> str:
        return "0"

    # -- lifecycle --
    async def launch(self, *, headless: bool = False) -> None:
        self._record("launch", headless)

    async def close(self) -> None:
        self._record("close")
        if self._close_error is not None:
            raise self._close_error

    # -- navigation --
    async def goto(self, url: str) -> None:
        self._record("goto", url)

    async def back(self) -> None:
        self._record("back")

    async def forward(self) -> None:
        self._record("forward")

    async def reload(self) -> None:
        self._record("reload")

    async def wait_for_load(self) -> None:
        self._record("wait_for_load")

    # -- DOM --
    async def click(self, selector: str) -> None:
        self._record("click", selector)

    async def fill(self, selector: str, text: str) -> None:
        self._record("fill", selector, text)

    async def press(self, selector: str, key: str) -> None:
        self._record("press", selector, key)

    async def hover(self, selector: str) -> None:
        self._record("hover", selector)

    async def text(self, selector: str) -> str:
        self._record("text", selector)
        return f"text:{selector}"

    # -- information --
    async def title(self) -> str:
        self._record("title")
        return "Example Domain"

    async def url(self) -> str:
        self._record("url")
        return "https://example.com/"

    async def html(self) -> str:
        self._record("html")
        return "<html></html>"

    # -- screenshots --
    async def screenshot(self, path: str | Path) -> None:
        self._record("screenshot", path)

    async def element_screenshot(self, selector: str, path: str | Path) -> None:
        self._record("element_screenshot", selector, path)

    # -- javascript --
    async def evaluate(self, script: str) -> Any:
        self._record("evaluate", script)
        return {"script": script}

    # -- waiting --
    async def wait_for_selector(self, selector: str) -> None:
        self._record("wait_for_selector", selector)

    async def wait(self, milliseconds: int) -> None:
        self._record("wait", milliseconds)

    # -- tabs --
    async def new_tab(self) -> None:
        self._record("new_tab")

    async def pages(self) -> list[Any]:
        self._record("pages")
        return []

    # -- downloads --
    async def download(self, selector: str, path: str | Path) -> None:
        self._record("download", selector, path)


def _service() -> tuple[BrowserService, _RecordingProvider]:
    provider = _RecordingProvider()
    return BrowserService(provider), provider


# ==============================================================
# Lifecycle
# ==============================================================


class TestBrowserServiceLifecycle:
    @pytest.mark.asyncio
    async def test_launch_delegates_and_records_open(self) -> None:
        service, provider = _service()

        await service.launch(headless=True)

        assert provider.calls == [("launch", (True,))]

    @pytest.mark.asyncio
    async def test_close_delegates(self) -> None:
        service, provider = _service()

        await service.launch()
        await service.close()

        assert provider.calls == [("launch", (False,)), ("close", ())]

    @pytest.mark.asyncio
    async def test_shutdown_without_launch_touches_nothing(self) -> None:
        # A session that never opened a browser must not have one constructed
        # and closed on its behalf.
        service, provider = _service()

        await service.shutdown()

        assert provider.calls == []

    @pytest.mark.asyncio
    async def test_shutdown_after_launch_closes(self) -> None:
        service, provider = _service()

        await service.launch()
        await service.shutdown()

        assert ("close", ()) in provider.calls

    @pytest.mark.asyncio
    async def test_shutdown_swallows_a_failing_close(self) -> None:
        # A browser that refuses to close must not stop the rest of shutdown.
        provider = _RecordingProvider(close_error=RuntimeError("stuck"))
        service = BrowserService(provider)

        await service.launch()

        # Does not raise.
        await service.shutdown()

        assert ("close", ()) in provider.calls


# ==============================================================
# Delegation
# ==============================================================


class TestBrowserServiceDelegation:
    @pytest.mark.asyncio
    async def test_navigation_delegates_with_arguments(self) -> None:
        service, provider = _service()

        await service.goto("https://example.com")
        await service.back()
        await service.forward()
        await service.reload()
        await service.wait_for_load()

        assert provider.calls == [
            ("goto", ("https://example.com",)),
            ("back", ()),
            ("forward", ()),
            ("reload", ()),
            ("wait_for_load", ()),
        ]

    @pytest.mark.asyncio
    async def test_dom_actions_delegate_with_arguments(self) -> None:
        service, provider = _service()

        await service.click("#go")
        await service.fill("#q", "aetheros")
        await service.press("#q", "Enter")
        await service.hover(".menu")

        assert provider.calls == [
            ("click", ("#go",)),
            ("fill", ("#q", "aetheros")),
            ("press", ("#q", "Enter")),
            ("hover", (".menu",)),
        ]

    @pytest.mark.asyncio
    async def test_information_delegates_and_returns(self) -> None:
        service, provider = _service()

        assert await service.title() == "Example Domain"
        assert await service.url() == "https://example.com/"
        assert await service.html() == "<html></html>"
        assert await service.text("h1") == "text:h1"

    @pytest.mark.asyncio
    async def test_page_text_reads_the_body(self) -> None:
        # The whole-page text capability reuses the element-text seam against
        # ``body`` rather than widening the provider interface.
        service, provider = _service()

        assert await service.page_text() == "text:body"
        assert ("text", ("body",)) in provider.calls

    @pytest.mark.asyncio
    async def test_screenshot_and_evaluate_delegate(self) -> None:
        service, provider = _service()

        await service.screenshot("out.png")
        result = await service.evaluate("1 + 1")

        assert ("screenshot", ("out.png",)) in provider.calls
        assert result == {"script": "1 + 1"}
