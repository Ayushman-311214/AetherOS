"""
CEOAgentService: the Trading CEO as a bounded, fenced tool-calling loop.

A scripted, deterministic fake LLM and a fake executor stand in for the real
ones (no network, no real tool stack), so these isolate the LOOP contract
(CLAUDE.md sections 2, 4, 5, 10, 28, 29): the LLM chooses tools and they run
through the executor, every number comes from a tool result, the loop is capped
at the tool-call budget, only permitted tools run, a malformed reply ends the
loop honestly, and with no LLM the investigation is an honest "needs an LLM".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.services.ceo_agent_service import CEOAgentService


@dataclass
class _Def:
    name: str
    description: str
    category: str = "trading.analysis"


class _FakeRegistry:
    def __init__(self, defs: list[_Def]) -> None:
        self._by_cat: dict[str, list[_Def]] = {}
        for d in defs:
            self._by_cat.setdefault(d.category, []).append(d)

    def by_category(self, category: str) -> list[_Def]:
        return list(self._by_cat.get(category, []))


@dataclass
class _Result:
    name: str
    ok: bool
    value: Any = None
    error: str | None = None


class _FakeExecutor:
    """Returns canned results per tool name; records what was executed."""

    def __init__(self, results: dict[str, _Result], defs: list[_Def]) -> None:
        self._results = results
        self.registry = _FakeRegistry(defs)
        self.executed: list[tuple[str, dict]] = []

    async def execute_safe(self, name: str, arguments: dict | None = None) -> _Result:
        self.executed.append((name, arguments or {}))
        return self._results.get(name, _Result(name=name, ok=False, error="unknown tool"))


class _ScriptedLLM:
    """Yields a fixed sequence of raw replies, one per generate() call."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = replies
        self._i = 0
        self.calls = 0

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-1"

    async def generate(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        self.calls += 1
        if self._i < len(self._replies):
            reply = self._replies[self._i]
            self._i += 1
            return reply
        return '{"final": "ran out of script"}'


_DEFS = [
    _Def("analyze_instrument", "Full analysis", "trading.analysis"),
    _Def("assess_risk", "Risk geometry", "trading.analysis"),
    _Def("analyze_news_sentiment", "News", "trading.analysis"),
    _Def("estimate_probability", "Probability", "trading.analysis"),
]


def _service(llm, results=None) -> CEOAgentService:
    executor = _FakeExecutor(results or {}, _DEFS)
    svc = CEOAgentService(executor, get_settings(), llm=llm)
    svc._test_executor = executor  # expose for assertions
    return svc


@pytest.mark.asyncio
async def test_no_llm_is_an_honest_needs_an_llm_result():
    inv = await _service(llm=None).investigate("look at AAPL")
    assert inv.stopped_reason == "no_llm"
    assert inv.grounded is False
    assert "needs an LLM" in inv.answer
    assert inv.narrated_by == "deterministic-fallback"


@pytest.mark.asyncio
async def test_llm_calls_a_tool_then_finalises():
    llm = _ScriptedLLM(
        [
            '{"tool": "analyze_instrument", "args": {"symbol": "AAPL"}}',
            '{"final": "AAPL is NO_TRADE on the analysis."}',
        ]
    )
    results = {"analyze_instrument": _Result("analyze_instrument", ok=True, value={"recommendation": "no_trade"})}
    svc = _service(llm, results)
    inv = await svc.investigate("look at AAPL")

    assert inv.stopped_reason == "final"
    assert inv.grounded is True
    assert "analyze_instrument" in inv.used_tools
    assert svc._test_executor.executed[0][0] == "analyze_instrument"
    assert inv.answer.startswith("AAPL is NO_TRADE")
    assert inv.narrated_by == "fake:fake-1"


@pytest.mark.asyncio
async def test_a_tool_outside_the_allowlist_is_refused():
    llm = _ScriptedLLM(
        [
            '{"tool": "delete_everything", "args": {}}',
            '{"final": "done"}',
        ]
    )
    svc = _service(llm)
    inv = await svc.investigate("do something dangerous")

    # The forbidden tool was never executed; the step is recorded as not permitted.
    assert ("delete_everything", {}) not in svc._test_executor.executed
    refused = [s for s in inv.steps if s.tool == "delete_everything"]
    assert refused and refused[0].ok is False
    assert refused[0].error == "tool not permitted"


@pytest.mark.asyncio
async def test_loop_is_bounded_by_the_tool_call_budget():
    # The LLM always asks for a tool and never finalises -> the loop must stop at
    # the budget rather than spinning forever.
    always_tool = '{"tool": "analyze_instrument", "args": {"symbol": "AAPL"}}'
    llm = _ScriptedLLM([always_tool] * 100)
    results = {"analyze_instrument": _Result("analyze_instrument", ok=True, value={})}
    svc = _service(llm, results)
    inv = await svc.investigate("loop forever")

    budget = get_settings().MAX_TOOL_CALLS
    assert inv.stopped_reason == "budget"
    assert len(inv.steps) == budget
    assert llm.calls == budget


@pytest.mark.asyncio
async def test_malformed_reply_ends_the_loop_honestly():
    llm = _ScriptedLLM(["I think you should buy, trust me (no JSON here)"])
    inv = await _service(llm).investigate("look at AAPL")
    assert inv.stopped_reason == "unparseable"
    assert inv.grounded is False


@pytest.mark.asyncio
async def test_quant_persona_fences_out_research_tools():
    # Under the quant persona, a news tool is not in the allowed set, so even if
    # the LLM asks for it, it is refused and never executed.
    llm = _ScriptedLLM(
        [
            '{"tool": "analyze_news_sentiment", "args": {"symbol": "AAPL"}}',
            '{"final": "done"}',
        ]
    )
    results = {"analyze_news_sentiment": _Result("analyze_news_sentiment", ok=True, value={})}
    svc = _service(llm, results)
    inv = await svc.investigate("news on AAPL", persona="quant")

    assert ("analyze_news_sentiment", {"symbol": "AAPL"}) not in svc._test_executor.executed
    refused = [s for s in inv.steps if s.tool == "analyze_news_sentiment"]
    assert refused and refused[0].error == "tool not permitted"


@pytest.mark.asyncio
async def test_quant_persona_allows_its_own_tools():
    llm = _ScriptedLLM(
        [
            '{"tool": "estimate_probability", "args": {"symbol": "AAPL"}}',
            '{"final": "quant read done"}',
        ]
    )
    results = {"estimate_probability": _Result("estimate_probability", ok=True, value={})}
    svc = _service(llm, results)
    inv = await svc.investigate("quant read AAPL", persona="quant")
    assert "estimate_probability" in inv.used_tools
    assert inv.stopped_reason == "final"
