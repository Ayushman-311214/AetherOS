"""
Recovery — bounded self-healing between step attempts.

A retry that changes nothing usually fails the same way. Windows desktop
automation has a small set of environmental faults that cause a *cascade* of
unrelated failures, and all of them are fixable without knowing anything about
the step that failed:

* **Stuck modifier keys.** ``pyautogui.hotkey("ctrl", "shift", "s")`` presses
  three keys and releases them in reverse. If it raises between the presses and
  the releases — a `FailSafeException`, a timeout, a cancelled task — Ctrl and
  Shift stay physically held down at the OS level. Every subsequent keystroke is
  then a shortcut: ``type_text("hello")`` becomes Ctrl+H, Ctrl+E, Ctrl+L… This
  is the single most destructive automation fault on Windows, and it is invisible
  in logs because each later tool reports success.
* **A modal dialog nobody expected.** An unsaved-changes prompt or a UAC-style
  window swallows input aimed at the window behind it.
* **Hover state.** A tooltip or flyout menu opened by the last mouse move sits
  over the coordinates the next click needs.
* **Timing.** The UI simply had not repainted yet.

Each strategy is expressed as a short sequence of ordinary tool calls, resolved
through the ToolRegistry at run time. Two consequences worth stating:

* Recovery cannot reach a callable the registry has not vetted, and inherits the
  registry's timeouts, validation and safety policy — the same guarantee the
  engine gets by routing steps through the executor.
* A strategy whose tools are not registered reports ``unavailable`` rather than
  quietly doing nothing. ``focus_active_window`` is deliberately declared before
  the window subsystem exists: today it reports unavailable, and the day
  ``get_active_window`` is registered it begins working with no change here. A
  recovery that silently no-ops is worse than no recovery, because the retry
  that follows looks like it was given a fresh start when it was not.

Bounding is the engine's job for *how many times* recovery runs (
``DESKTOP_RECOVERY_MAX_ATTEMPTS``); this module bounds how much one run can do.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from ...core.logging import get_logger
from ...tools.executor import ToolExecutor, tool_executor
from ...tools.registry import ToolRegistry, tool_registry

MAX_ACTIONS_PER_STRATEGY = 8
"""
Cap on the actions one strategy may perform, so recovery stays short next to
the step it is trying to rescue.
"""


@dataclass(frozen=True, slots=True)
class RecoveryAction:
    """
    One move within a recovery strategy.

    Either a tool call, or a pause, or both — a pause after the call is the
    common shape, since the point of most of these is to let the UI settle.
    """

    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    wait_seconds: float = 0.0
    optional: bool = False
    """
    Whether a missing tool or a failed call is acceptable.

    ``True`` for best-effort cleanup: releasing Shift when Shift was never held
    reports a failure on some backends, and that is not a reason to abandon the
    rest of the strategy.
    """


@dataclass(frozen=True, slots=True)
class RecoveryStrategy:
    """
    A named, context-free repair applied between attempts.

    Context-free is a design decision, not a limitation. A repair that needs to
    know *which* window or *which* file belongs in the step's ``fallback``, where
    it is fully specified data that can be validated up front. Recovery handles
    the environment; fallback handles the intent.
    """

    name: str
    description: str
    actions: tuple[RecoveryAction, ...]

    def __post_init__(self) -> None:

        if len(self.actions) > MAX_ACTIONS_PER_STRATEGY:
            # Defensive: these are declared as literals below, so tripping this
            # means someone extended a strategy past the point where it is still
            # cheap enough to run between every attempt.
            object.__setattr__(
                self,
                "actions",
                self.actions[:MAX_ACTIONS_PER_STRATEGY],
            )

    @property
    def required_tools(self) -> tuple[str, ...]:
        """
        Tools that must exist for this strategy to do anything at all.

        Optional actions are excluded: they are allowed to be missing.
        """

        return tuple(
            action.tool
            for action in self.actions
            if action.tool and not action.optional
        )


@dataclass(frozen=True, slots=True)
class RecoveryOutcome:
    """
    What one strategy achieved.

    ``applied`` is false for both "the tools are missing" and "the actions
    failed", but ``detail`` distinguishes them, because the two call for
    completely different responses from whoever reads the log.
    """

    strategy: str
    applied: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "applied": self.applied,
            "detail": self.detail,
        }


# ==============================================================
# Built-in strategies
# ==============================================================

STRATEGIES: dict[str, RecoveryStrategy] = {
    "settle": RecoveryStrategy(
        name="settle",
        description=(
            "Pause briefly to let the UI finish repainting. The cheapest repair, "
            "and often the only one needed for a step that raced the interface."
        ),
        actions=(RecoveryAction(wait_seconds=0.4),),
    ),
    "release_modifiers": RecoveryStrategy(
        name="release_modifiers",
        description=(
            "Release Ctrl, Alt, Shift and Win. Use after any failed hotkey: a "
            "modifier left held turns every later keystroke into a shortcut, "
            "which corrupts subsequent steps while they all report success."
        ),
        # One required call rather than four optional ones. The earlier version
        # sent key_up for the generic "ctrl"/"alt"/"shift"/"win" names, which was
        # wrong twice: releasing VK_CONTROL does not necessarily clear a stuck
        # *left* Control, and marking all four optional meant the strategy
        # reported itself applied even when every action failed -- so a genuinely
        # stuck modifier looked repaired. clear_modifiers releases both the left
        # and right variant of all four, and failing loudly here is correct: if
        # modifiers cannot be released, the steps that follow cannot be trusted.
        actions=(
            RecoveryAction(tool="clear_modifiers"),
            RecoveryAction(wait_seconds=0.1),
        ),
    ),
    "dismiss_dialog": RecoveryStrategy(
        name="dismiss_dialog",
        description=(
            "Press Escape once to close an unexpected modal or flyout that is "
            "swallowing input aimed at the window behind it. Escape is chosen "
            "over Enter deliberately — it cancels rather than confirms, so it "
            "cannot accept a dialog the user did not intend to accept."
        ),
        actions=(
            RecoveryAction(tool="press_key", arguments={"key": "escape"}),
            RecoveryAction(wait_seconds=0.2),
        ),
    ),
    "clear_hover": RecoveryStrategy(
        name="clear_hover",
        description=(
            "Move the pointer to the top-left corner to dismiss a tooltip or "
            "hover menu covering the coordinates the next click needs."
        ),
        actions=(
            RecoveryAction(
                tool="move_mouse",
                arguments={"x": 1, "y": 1},
            ),
            RecoveryAction(wait_seconds=0.15),
        ),
    ),
    "focus_active_window": RecoveryStrategy(
        name="focus_active_window",
        description=(
            "Re-assert focus on the foreground window, for a step whose input "
            "went to the wrong place. Requires the window subsystem; reports "
            "unavailable until those tools are registered."
        ),
        actions=(
            RecoveryAction(tool="get_active_window"),
            RecoveryAction(tool="focus_window", arguments={"active": True}),
            RecoveryAction(wait_seconds=0.2),
        ),
    ),
}


def describe_strategies() -> dict[str, str]:
    """
    Strategy name to description.

    Read by the ``run_workflow`` tool description and the health check, so the
    list the model is offered cannot drift from the strategies that exist.
    """

    return {
        name: strategy.description
        for name, strategy in sorted(STRATEGIES.items())
    }


# ==============================================================
# Runner
# ==============================================================


class RecoveryRunner:
    """
    Applies recovery strategies by name.

    Never raises for a recovery-level problem. Recovery runs *because* something
    already went wrong; a failure inside it must not replace the original error
    with a less informative one, so every outcome comes back as data and the
    caller retries — or gives up — on the strength of the original failure.
    """

    def __init__(
        self,
        executor: ToolExecutor = tool_executor,
        registry: ToolRegistry = tool_registry,
    ) -> None:

        self._executor = executor
        self._registry = registry
        self._logger = get_logger("desktop.recovery")

    # ----------------------------------------------------------

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(STRATEGIES))

    def unknown(self, names: tuple[str, ...]) -> tuple[str, ...]:
        """
        Which of ``names`` are not recovery strategies.

        Used by the dry-run path so a typo in ``recovery`` is caught during
        validation instead of surfacing hours later, at the one moment the
        workflow actually needed to repair itself.
        """

        return tuple(name for name in names if name not in STRATEGIES)

    def availability(self) -> dict[str, bool]:
        """
        Which strategies can currently do anything, given the registered tools.
        """

        return {
            name: self._is_available(strategy)
            for name, strategy in sorted(STRATEGIES.items())
        }

    # ----------------------------------------------------------

    async def run(
        self,
        names: tuple[str, ...],
        *,
        execution_id: str,
        step_name: str,
    ) -> tuple[RecoveryOutcome, ...]:
        """
        Apply each named strategy in order, once.
        """

        outcomes: list[RecoveryOutcome] = []

        for name in names:

            strategy = STRATEGIES.get(name)

            if strategy is None:
                outcomes.append(
                    RecoveryOutcome(
                        strategy=name,
                        applied=False,
                        detail=(
                            f"No recovery strategy named '{name}'. "
                            f"Available: {', '.join(self.names)}."
                        ),
                    )
                )
                continue

            outcomes.append(
                await self._apply(
                    strategy,
                    execution_id=execution_id,
                    step_name=step_name,
                )
            )

        return tuple(outcomes)

    # ----------------------------------------------------------

    async def _apply(
        self,
        strategy: RecoveryStrategy,
        *,
        execution_id: str,
        step_name: str,
    ) -> RecoveryOutcome:

        missing = [
            name
            for name in strategy.required_tools
            if not self._registry.exists(name)
        ]

        if missing:
            detail = (
                f"unavailable: tool(s) not registered: {', '.join(sorted(set(missing)))}"
            )

            self._logger.bind(
                execution_id=execution_id,
                step=step_name,
                strategy=strategy.name,
                missing_tools=sorted(set(missing)),
            ).warning("Recovery strategy unavailable.")

            return RecoveryOutcome(
                strategy=strategy.name,
                applied=False,
                detail=detail,
            )

        performed = 0
        problems: list[str] = []

        for action in strategy.actions:

            if action.tool:

                if not self._registry.exists(action.tool):
                    # Only reachable for optional actions; required ones were
                    # screened above.
                    continue

                try:
                    result = await self._executor.execute_safe(
                        action.tool,
                        dict(action.arguments),
                    )

                except asyncio.CancelledError:
                    # Shutdown or Ctrl-C. Propagate — a cancelled recovery must
                    # not be reported as a completed one.
                    raise

                if result.ok:
                    performed += 1

                elif not action.optional:
                    problems.append(f"{action.tool}: {result.error}")

            if action.wait_seconds > 0:
                await asyncio.sleep(action.wait_seconds)
                performed += 1

        applied = performed > 0 and not problems

        detail = (
            f"applied {performed} action(s)"
            if applied
            else "; ".join(problems) or "no action had any effect"
        )

        self._logger.bind(
            execution_id=execution_id,
            step=step_name,
            strategy=strategy.name,
            applied=applied,
            actions=performed,
        ).info("Recovery strategy finished.")

        return RecoveryOutcome(
            strategy=strategy.name,
            applied=applied,
            detail=detail,
        )

    # ----------------------------------------------------------

    def _is_available(self, strategy: RecoveryStrategy) -> bool:

        return all(
            self._registry.exists(name)
            for name in strategy.required_tools
        )


recovery_runner = RecoveryRunner()
"""
Process-wide recovery runner.
"""


__all__ = [
    "MAX_ACTIONS_PER_STRATEGY",
    "STRATEGIES",
    "RecoveryAction",
    "RecoveryOutcome",
    "RecoveryRunner",
    "RecoveryStrategy",
    "describe_strategies",
    "recovery_runner",
]
