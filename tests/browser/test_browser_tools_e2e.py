"""
End-to-end validation of the browser tools through the Agent Core.

This mirrors ``tests/cli/test_agent_e2e.py`` for the browser subsystem, with a
fake only at the one legitimate boundary -- the browser backend:

    Agent -> planner (scripted LLM) -> Policy -> ToolExecutor
        -> the real ``open_browser`` / ``goto_url`` / ``page_title`` @tool
        -> the real ``BrowserService``
        -> fake ``BrowserProvider`` (records the calls, returns a title)
        -> result -> Agent -> LLM -> final answer

Everything above the provider is production: the real ``@tool`` definitions
copied out of the process-wide ``tool_registry`` (so the planner sees the
production schema), a real ``PolicyEngine``, the real ``ToolExecutor`` (wrapped
only to witness delegation) and the real ``AgentCore``. Only two things are
doubled, both legitimate: the LLM (scripted, so the turn is deterministic) and
the ``BrowserProvider`` (recording, so no Chromium is launched). The fake
provider is the honest witness -- a URL reaches ``goto`` only if it travelled
the whole chain, and ``page_title`` returns a value only if the tool ran.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

import pytest

from aetheros.agents.core import AgentCore
from aetheros.agents.policy import PolicyConfig, PolicyEngine
from aetheros.agents.state import STOP_FINAL_ANSWER
from aetheros.browser import tools as _browser_tools  # noqa: F401 - registers tools
from aetheros.browser.controller import BrowserService
from aetheros.browser.providers.base import BrowserProvider
from aetheros.core.container import container
from aetheros.tools import tool_registry
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry
from aetheros.tools.schema import ToolSchemaGenerator


# ==============================================================
# Fakes: the two legitimate boundaries (backend + model)
# ==============================================================


class _RecordingProvider(BrowserProvider):
    """A ``BrowserProvider`` sitting where Playwright would.

    Records every call so ``calls`` is proof an operation travelled the full
    chain, and answers the read methods with fixed values.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.launched = False

    def _record(self, name: str, *args: Any) -> None:
        self.calls.append((name, args))

    @property
    def name(self) -> str:
        return "recording"

    @property
    def version(self) -> str:
        return "0"

    async def launch(self, *, headless: bool = False) -> None:
        self._record("launch", headless)
        self.launched = True

    async def close(self) -> None:
        self._record("close")
        self.launched = False

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
        return "Example Domain\nThis domain is for use in examples."

    async def title(self) -> str:
        self._record("title")
        return "Example Domain"

    async def url(self) -> str:
        self._record("url")
        return "https://example.com/"

    async def html(self) -> str:
        self._record("html")
        return "<html><body>Example Domain</body></html>"

    async def screenshot(self, path: str | Path) -> None:
        self._record("screenshot", path)

    async def element_screenshot(self, selector: str, path: str | Path) -> None:
        self._record("element_screenshot", selector, path)

    async def evaluate(self, script: str) -> Any:
        self._record("evaluate", script)
        return None

    async def wait_for_selector(self, selector: str) -> None:
        self._record("wait_for_selector", selector)

    async def wait(self, milliseconds: int) -> None:
        self._record("wait", milliseconds)

    async def new_tab(self) -> None:
        self._record("new_tab")

    async def pages(self) -> list[Any]:
        self._record("pages")
        return []

    async def download(self, selector: str, path: str | Path) -> None:
        self._record("download", selector, path)


class _CountingExecutor(ToolExecutor):
    """The real executor, recording every tool it was actually asked to run.

    A name reaches ``asked`` only after the coordinator's policy gate returns
    ALLOW, so it witnesses that the call passed Policy and went *through*
    ``ToolExecutor`` rather than around it.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        super().__init__(registry=registry, timeout_seconds=None)
        self.asked: list[str] = []

    async def execute_safe(self, name: str, arguments: dict[str, Any]) -> Any:
        self.asked.append(name)
        return await super().execute_safe(name, arguments)


# ==============================================================
# Helpers
# ==============================================================


@contextlib.contextmanager
def _fake_browser():
    """Bind the ``BrowserService`` the tools resolve to a recording provider.

    Every browser tool does ``container.resolve(BrowserService)`` at call time,
    so the seam is swapped here and removed afterwards -- no global state leaks
    between tests, and no Playwright is imported.
    """

    provider = _RecordingProvider()
    container.register_singleton(
        BrowserService,
        lambda: BrowserService(provider),
    )
    try:
        yield provider
    finally:
        container.remove(BrowserService)


def _with_real_tools(registry: ToolRegistry, *names: str) -> ToolRegistry:
    """Copy production tool definitions into an isolated registry."""

    for name in names:
        registry.register(tool_registry.get(name))
    return registry


def _build(
    provider: Any,
    registry: ToolRegistry,
    policy: PolicyEngine,
) -> tuple[AgentCore, _CountingExecutor]:
    executor = _CountingExecutor(registry)
    core = AgentCore.from_provider(
        provider,
        registry=registry,
        executor=executor,
        policy=policy,
        system_prompt="Test system prompt.",
    )
    return core, executor


# ==============================================================
# 0. Registration and schema -- what `tools` shows and the planner is offered
# ==============================================================


class TestBrowserToolRegistration:
    def test_the_lifecycle_tools_are_registered_under_browser(self) -> None:
        # Importing aetheros.browser.tools (top of this module) is what the
        # bootstrapper's tool phase does; the required verbs must all be present.
        for name in (
            "open_browser",
            "goto_url",
            "current_url",
            "close_browser",
            "browser_back",
            "browser_forward",
            "browser_reload",
            "page_title",
            "page_text",
            "click_element",
            "fill_input",
            "browser_press_key",
            "browser_screenshot",
        ):
            tool = tool_registry.get(name)
            assert tool.category == "browser"

    def test_the_production_schemas_are_correct(self) -> None:
        gen = ToolSchemaGenerator()

        goto = gen.generate(tool_registry.get("goto_url"))
        assert goto["function"]["name"] == "goto_url"
        assert goto["function"]["parameters"]["properties"]["url"] == {
            "type": "string"
        }
        assert goto["function"]["parameters"]["required"] == ["url"]

        title = gen.generate(tool_registry.get("page_title"))
        assert title["function"]["parameters"]["required"] == []

        text = gen.generate(tool_registry.get("page_text"))
        assert text["function"]["parameters"]["required"] == []

        press = gen.generate(tool_registry.get("browser_press_key"))
        assert set(press["function"]["parameters"]["required"]) == {
            "selector",
            "key",
        }


# ==============================================================
# 1. "Open example.com and tell me the page title." -- the full chain
# ==============================================================


class TestBrowserTitleE2E:
    @pytest.mark.asyncio
    async def test_open_navigate_and_read_title_through_the_agent(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        tool_calls: Any,
        answer: Any,
    ) -> None:
        policy = PolicyEngine(PolicyConfig())
        _with_real_tools(registry, "open_browser", "goto_url", "page_title")

        provider = make_provider(
            [
                tool_calls(("open_browser", {"headless": True})),
                tool_calls(("goto_url", {"url": "https://example.com"})),
                tool_calls(("page_title", {})),
                answer('The page title is "Example Domain".'),
            ]
        )
        core, executor = _build(provider, registry, policy)

        with _fake_browser() as browser:
            result = await core.run(
                "Open example.com and tell me the page title.",
            )

        # LLM -> Agent -> Policy -> ToolExecutor: each tool passed the gate and
        # ran through the executor, in order.
        assert executor.asked == ["open_browser", "goto_url", "page_title"]

        # ...-> real tool -> BrowserService -> provider: the arguments survived
        # every hop and reached the backend seam. The turn never asked to close,
        # so the browser is still open.
        assert ("launch", (True,)) in browser.calls
        assert ("goto", ("https://example.com",)) in browser.calls
        assert ("title", ()) in browser.calls
        assert ("close", ()) not in browser.calls
        assert browser.launched is True

        # ...-> result -> LLM -> final answer.
        assert result.stopped_reason == STOP_FINAL_ANSWER
        assert result.final_response == 'The page title is "Example Domain".'

    @pytest.mark.asyncio
    async def test_the_provider_is_the_only_seam(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        tool_calls: Any,
        answer: Any,
    ) -> None:
        # The read-a-page path: page_text must resolve to a body read on the
        # provider, never to page HTML or a Playwright call.
        policy = PolicyEngine(PolicyConfig())
        _with_real_tools(registry, "open_browser", "goto_url", "page_text")

        provider = make_provider(
            [
                tool_calls(("open_browser", {})),
                tool_calls(("goto_url", {"url": "https://example.com"})),
                tool_calls(("page_text", {})),
                answer("The page is about example domains."),
            ]
        )
        core, executor = _build(provider, registry, policy)

        with _fake_browser() as browser:
            result = await core.run("Open example.com and read it to me.")

        assert executor.asked == ["open_browser", "goto_url", "page_text"]
        assert ("text", ("body",)) in browser.calls
        assert result.final_response == "The page is about example domains."
