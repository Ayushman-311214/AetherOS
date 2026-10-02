"""
CEO sub-agent personas.

The agentic CEO can run under a *persona*: a role framing plus a fenced subset of
the trading tools, so a focused sub-agent sees only the tools its job needs
(CLAUDE.md section 5 -- specialized agents rather than one giant agent). A
research agent sees the news/calendar/fundamentals tools; a quant agent sees the
statistical/model tools; a critic agent sees the report/critique/track-record
tools. The default ``full`` persona exposes every trading tool (the original
single-agent behaviour).

A persona only ever *narrows* what is callable and adds role framing to the
prompt; it never grants a tool outside the CEO's allowed trading categories, so
the fencing guarantee is preserved (sections 11, 29).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Persona:
    """A CEO sub-agent role: a prompt framing plus an allowed tool subset."""

    name: str
    role: str  # one line appended to the system prompt
    # Tool names this persona may call. None = every tool in the CEO's allowed
    # categories (the full agent).
    tool_names: frozenset[str] | None = None


_RESEARCH = Persona(
    name="research",
    role=(
        "You are the research sub-agent: focus on news, scheduled events and "
        "fundamentals to build the qualitative picture."
    ),
    tool_names=frozenset(
        {
            "analyze_instrument",
            "analyze_market_structure",
            "analyze_news_sentiment",
            "get_market_events",
            "analyze_fundamentals",
            "analyze_macro_context",
        }
    ),
)

_QUANT = Persona(
    name="quant",
    role=(
        "You are the quant sub-agent: focus on the statistical and model-based "
        "reads -- probability, backtest, regime, relative strength, anomalies, "
        "analogues, divergence, breakout, multi-timeframe."
    ),
    tool_names=frozenset(
        {
            "analyze_instrument",
            "estimate_probability",
            "backtest_signal",
            "detect_market_regime",
            "analyze_relative_strength",
            "detect_anomalies",
            "find_historical_analogues",
            "detect_divergence",
            "detect_breakout",
            "analyze_multi_timeframe",
        }
    ),
)

_CRITIC = Persona(
    name="critic",
    role=(
        "You are the critic sub-agent: challenge the signal -- compose the full "
        "report, critique it, explain it, and weigh it against the recorded "
        "track record."
    ),
    tool_names=frozenset(
        {
            "generate_trading_report",
            "critique_signal",
            "explain_signal",
            "evaluate_track_record",
            "run_monitoring_pass",
        }
    ),
)

_FULL = Persona(
    name="full",
    role="You are the Trading CEO with access to the full trading toolset.",
    tool_names=None,
)

PERSONAS: dict[str, Persona] = {
    "research": _RESEARCH,
    "quant": _QUANT,
    "critic": _CRITIC,
    "full": _FULL,
}


def resolve_persona(name: str | None) -> Persona:
    """Resolve a persona key to a Persona, defaulting to the full agent."""
    if not name:
        return _FULL
    return PERSONAS.get(name.strip().lower(), _FULL)
