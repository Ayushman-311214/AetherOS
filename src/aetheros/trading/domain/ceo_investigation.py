"""
CEO-investigation value object.

A :class:`CEOInvestigation` is the record of the Trading CEO running an agentic
tool-calling loop (CLAUDE.md sections 4, 5): the LLM is given the free-text
request and the catalogue of deterministic trading tools, and it chooses and
sequences the tools itself; each tool runs through the real ToolRegistry and its
result is fed back until the LLM produces a final answer or the step budget is
reached.

The division of labour and the honesty rules are the same as everywhere else
(sections 2, 3, 10, 28): the LLM decides *which analyses to run and how to
explain them*, but every number comes from a deterministic tool result, never
from the model. The full ``steps`` trace -- which tool ran with which arguments
and what it returned -- is retained as the auditable source of truth behind the
narrative, and ``grounded`` records whether at least one real tool actually ran
(an answer with no successful tool call is not grounded).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class CEOStep:
    """One tool call the CEO made during an investigation."""

    index: int
    tool: str
    arguments: dict[str, Any]
    ok: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "tool": self.tool,
            "arguments": self.arguments,
            "ok": self.ok,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class CEOInvestigation:
    """The record of an agentic, tool-calling CEO investigation."""

    request: str
    answer: str
    steps: tuple[CEOStep, ...]
    used_tools: tuple[str, ...]
    narrated_by: str  # "<provider>:<model>" or "deterministic-fallback"
    grounded: bool  # at least one real tool ran successfully
    stopped_reason: str  # "final" | "budget" | "unparseable" | "no_llm" | "error"
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "answer": self.answer,
            "steps": [s.to_dict() for s in self.steps],
            "used_tools": list(self.used_tools),
            "narrated_by": self.narrated_by,
            "grounded": self.grounded,
            "stopped_reason": self.stopped_reason,
            "created_at": self.created_at.isoformat(),
        }
