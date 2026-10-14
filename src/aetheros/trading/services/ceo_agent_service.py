"""
CEO agent service -- the Trading CEO as an agentic tool-calling loop.

This is the multi-step face of the Trading CEO (CLAUDE.md sections 4, 5): the LLM
is handed the free-text request and the catalogue of deterministic trading tools,
and it *chooses and sequences the tools itself* -- analyse, assess risk, check
the calendar, explain -- with each tool running through the real ToolRegistry and
its result fed back, until the model produces a final answer or the step budget
is reached.

The spec's division of labour is enforced structurally (sections 2, 3, 10, 28):

* **The LLM orchestrates; the tools compute.** The model decides which analyses
  to run and how to narrate them, but every number comes from a deterministic
  tool result -- the model never produces a price, probability or signal.
* **Bounded.** The loop runs at most ``MAX_TOOL_CALLS`` steps, so an agent cannot
  spin forever (section 29 -- autonomy stays bounded).
* **Fenced.** Only tools in the allowed trading categories are exposed and
  callable; a request for any other tool is refused and reported back, so the
  CEO cannot reach desktop/vision/other subsystems.
* **Degrade-safe.** With no LLM wired the investigation returns an honest "needs
  an LLM" result pointing at the deterministic ``analyze``/``brief`` paths rather
  than failing; a malformed model reply ends the loop honestly rather than
  guessing.

The full tool trace is retained on the :class:`CEOInvestigation` as the auditable
source of truth behind the narrative.
"""

from __future__ import annotations

import json

from ...config.settings import Settings
from ...core.interfaces.llm_provider import LLMProvider
from ...core.logging import get_logger
from ...tools.executor import ToolExecutor
from ..domain.ceo_investigation import CEOInvestigation, CEOStep
from ..domain.ceo_persona import Persona, resolve_persona

logger = get_logger("trading.ceo_agent")

_DEFAULT_CATEGORIES = ("trading.data", "trading.analysis", "trading.audit")

_SYSTEM_TEMPLATE = (
    "You are the Trading CEO. Investigate the user's request by calling the "
    "deterministic trading tools below -- you choose which to call and in what "
    "order. Every number in your final answer MUST come from a tool result; "
    "never invent prices, probabilities or signals. Never upgrade a NO_TRADE or "
    "unreliable read into a trade. Probabilities are estimates, not guarantees; "
    "this is analysis, not advice.\n\n"
    "Reply with ONLY a single JSON object, nothing else:\n"
    '  to call a tool: {{"tool": "<name>", "args": {{...}}}}\n'
    '  when done:      {{"final": "<your grounded answer>"}}\n\n'
    "{role}\n"
    "You have at most {budget} tool calls. Available tools:\n{catalog}"
)


class CEOAgentService:
    """Runs the Trading CEO as a bounded, fenced, tool-calling loop."""

    def __init__(
        self,
        executor: ToolExecutor,
        settings: Settings,
        *,
        llm: LLMProvider | None = None,
        categories: tuple[str, ...] = _DEFAULT_CATEGORIES,
    ) -> None:
        self._executor = executor
        self._settings = settings
        self._llm = llm
        self._categories = categories

    async def investigate(
        self, request: str, *, persona: str | None = None
    ) -> CEOInvestigation:
        role = resolve_persona(persona)
        allowed = self._allowed_tools(role)
        if self._llm is None:
            return CEOInvestigation(
                request=request,
                answer=(
                    "An agentic CEO investigation needs an LLM, which is not "
                    "configured. Use the deterministic 'analyze <symbol>' or "
                    "'brief <request>' instead."
                ),
                steps=(),
                used_tools=(),
                narrated_by="deterministic-fallback",
                grounded=False,
                stopped_reason="no_llm",
            )

        budget = max(1, int(self._settings.MAX_TOOL_CALLS))
        messages = [
            {"role": "system", "content": self._system_prompt(allowed, budget, role)},
            {"role": "user", "content": request},
        ]

        steps: list[CEOStep] = []
        used: list[str] = []
        answer = ""
        stopped = "budget"

        for i in range(budget):
            try:
                raw = await self._llm.generate(messages)
            except Exception:
                logger.exception("CEO agent LLM call failed")
                answer = self._fallback_answer(steps)
                stopped = "error"
                break

            action = self._parse(raw)
            messages.append({"role": "assistant", "content": raw})

            if action is None:
                answer = self._fallback_answer(steps)
                stopped = "unparseable"
                break

            if "final" in action:
                answer = str(action.get("final") or "").strip() or self._fallback_answer(steps)
                stopped = "final"
                break

            tool = str(action.get("tool") or "").strip()
            args = action.get("args") if isinstance(action.get("args"), dict) else {}

            if tool not in allowed:
                step = CEOStep(
                    index=i,
                    tool=tool or "<none>",
                    arguments=args,
                    ok=False,
                    error="tool not permitted",
                )
                steps.append(step)
                messages.append(self._observation(tool, {"error": "tool not permitted"}))
                continue

            result = await self._executor.execute_safe(tool, args)
            steps.append(
                CEOStep(
                    index=i,
                    tool=tool,
                    arguments=args,
                    ok=result.ok,
                    error=None if result.ok else (result.error or "tool failed"),
                )
            )
            if result.ok:
                used.append(tool)
                messages.append(self._observation(tool, {"ok": True, "result": result.value}))
            else:
                messages.append(
                    self._observation(tool, {"ok": False, "error": result.error})
                )

        if stopped == "budget" and not answer:
            answer = self._fallback_answer(steps)

        grounded = any(s.ok for s in steps)
        narrated_by = (
            f"{self._llm.name}:{self._llm.model}" if stopped == "final" and grounded
            else "deterministic-fallback" if stopped in ("no_llm", "error", "unparseable")
            else f"{self._llm.name}:{self._llm.model}"
        )

        return CEOInvestigation(
            request=request,
            answer=answer,
            steps=tuple(steps),
            used_tools=tuple(dict.fromkeys(used)),
            narrated_by=narrated_by,
            grounded=grounded,
            stopped_reason=stopped,
        )

    # ------------------------------------------------------------------

    def _allowed_tools(self, persona: Persona) -> dict[str, str]:
        """name -> description for the tools this persona may call.

        Starts from every tool in the CEO's allowed trading categories, then
        narrows to the persona's subset (if any) -- a persona can only ever
        restrict, never widen beyond the fenced categories.
        """
        catalog: dict[str, str] = {}
        for category in self._categories:
            for definition in self._executor.registry.by_category(category):
                catalog[definition.name] = definition.description
        if persona.tool_names is not None:
            catalog = {n: d for n, d in catalog.items() if n in persona.tool_names}
        return catalog

    def _system_prompt(
        self, allowed: dict[str, str], budget: int, persona: Persona
    ) -> str:
        catalog = "\n".join(f"- {name}: {desc}" for name, desc in allowed.items())
        return _SYSTEM_TEMPLATE.format(
            budget=budget, catalog=catalog, role=persona.role
        )

    @staticmethod
    def _observation(tool: str, payload: dict) -> dict:
        return {
            "role": "user",
            "content": f"TOOL RESULT [{tool}]:\n" + json.dumps(payload, default=str),
        }

    @staticmethod
    def _parse(raw: str) -> dict | None:
        if not isinstance(raw, str):
            return None
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            return None
        try:
            data = json.loads(raw[start : end + 1])
        except (ValueError, TypeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _fallback_answer(steps: list[CEOStep]) -> str:
        if not steps:
            return (
                "The investigation produced no tool results to ground an answer. "
                "Try the deterministic 'analyze <symbol>' directly."
            )
        ran = ", ".join(dict.fromkeys(s.tool for s in steps if s.ok)) or "none"
        return (
            "The investigation did not reach a clean final answer. Deterministic "
            f"tools that ran: {ran}. Their results above are the source of truth; "
            "re-run 'analyze <symbol>' for a direct report. Analysis, not advice."
        )
