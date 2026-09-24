"""
Policy configuration: the rules the engine evaluates against.

Deliberately data, not behaviour. A :class:`PolicyConfig` says *what* is allowed
-- which tools, how many iterations, how long, which arguments are acceptable --
and the engine says *whether* a given call fits. Keeping the two apart is what
lets a deployment tighten policy by handing over a different config, and lets a
test vary one rule without rebuilding the engine.

No tool names are baked in here. Every allow/deny/confirm set defaults empty, so
the out-of-the-box policy restricts nothing by name; a deployment fills them from
its own configuration. An empty ``allowed_tools`` means "no allowlist" (any tool
may run unless denied), which is distinct from a set that happens to list every
tool.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Callable

from ...core.errors.agent_error import AgentError

# An argument validation hook. Given the tool name and its arguments, it returns
# something falsy/None/True for "acceptable", or a non-empty string naming what
# is wrong. It must not mutate the arguments and must not run the tool -- it is a
# check, not a step. A hook that raises is treated as a policy failure (denied,
# fail-closed) rather than trusted; see PolicyEngine._validate_arguments.
ArgumentValidator = Callable[[str, Mapping[str, Any]], "str | bool | None"]


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    """The rule set one :class:`PolicyEngine` evaluates against.

    Frozen: a policy that could be edited after the engine started reading it is
    a policy nobody can reason about. Sets are normalised to ``frozenset`` and
    the validator map is copied, so a caller cannot mutate the rules out from
    under a running engine by holding the collection it passed in.
    """

    #: Tools permitted to run. Empty means "no allowlist" -- any tool may run
    #: unless it is denied -- not "nothing may run".
    allowed_tools: Iterable[str] = frozenset()

    #: Tools that may never run. Takes precedence over everything but the
    #: emergency stop, so listing a tool here denies it even if it is also
    #: allowed -- a deny is not silently overridden by an allow.
    denied_tools: Iterable[str] = frozenset()

    #: Tools permitted only with explicit confirmation. Absent confirmation the
    #: engine answers REQUIRE_CONFIRMATION rather than running them.
    confirmation_tools: Iterable[str] = frozenset()

    #: Hard ceiling on execution iterations. ``None`` means the policy sets no
    #: cap of its own (the run's own budget in AgentState still applies).
    max_iterations: int | None = None

    #: Advisory per-call timeout the engine reports. ``None`` falls back to the
    #: configured ``TOOL_TIMEOUT_SECONDS`` at evaluation time.
    timeout_seconds: float | None = None

    #: Per-tool argument validators, keyed by tool name.
    argument_validators: Mapping[str, ArgumentValidator] = field(
        default_factory=dict
    )

    #: Validators applied to every tool, before any per-tool one.
    global_argument_validators: Sequence[ArgumentValidator] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_tools", frozenset(self.allowed_tools))
        object.__setattr__(self, "denied_tools", frozenset(self.denied_tools))
        object.__setattr__(
            self, "confirmation_tools", frozenset(self.confirmation_tools)
        )
        object.__setattr__(
            self, "argument_validators", dict(self.argument_validators)
        )
        object.__setattr__(
            self,
            "global_argument_validators",
            tuple(self.global_argument_validators),
        )

        if self.max_iterations is not None and self.max_iterations < 0:
            raise AgentError(
                code="POLICY_INVALID_CONFIG",
                message=(
                    "PolicyConfig.max_iterations must be >= 0 or None, got "
                    f"{self.max_iterations}."
                ),
            )

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise AgentError(
                code="POLICY_INVALID_CONFIG",
                message=(
                    "PolicyConfig.timeout_seconds must be > 0 or None, got "
                    f"{self.timeout_seconds}."
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        """Log-safe summary. Validators are reported by count, not identity --
        they are callables, and a function object is not serialisable anyway."""

        return {
            "allowed_tools": sorted(self.allowed_tools),
            "denied_tools": sorted(self.denied_tools),
            "confirmation_tools": sorted(self.confirmation_tools),
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "argument_validators": sorted(self.argument_validators),
            "global_argument_validators": len(self.global_argument_validators),
        }


__all__ = [
    "ArgumentValidator",
    "PolicyConfig",
]
