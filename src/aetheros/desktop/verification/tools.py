"""
The generic verification tool.

Every action tool verifies itself, so this exists for the cases that cannot be
covered that way: confirming a precondition *before* acting ("is Notepad already
running?"), waiting for a slow UI to settle, and checking the result of something
AetherOS did not do itself — a user's manual step, or an action taken through the
browser subsystem.

It is also the tool an agent reaches for when it does not trust a result. That is
a feature: a model that can independently re-check state does not have to take a
previous step's word for it.
"""

from __future__ import annotations

from typing import Any

from ...tools import tool
from .strategy import (
    STRATEGIES,
    MatchMode,
    VerificationRequest,
    parse_mode,
    parse_region,
)
from .verifier import verifier


def _method_list() -> str:
    """
    Render the available methods for the tool description.

    Built from the strategy table rather than typed out, so a method cannot be
    added, removed or renamed without the model's description following it.
    """

    return " ".join(
        f"'{name}' ({cls.description})" for name, cls in sorted(STRATEGIES.items())
    )


@tool(
    category="desktop.verification",
    description=(
        "Check the real state of the machine and report whether a condition "
        "holds. Use this to confirm a precondition before acting, to wait for a "
        "slow interface to settle, or to independently re-check something you "
        "were told succeeded. "
        f"Available methods: {_method_list()} "
        "Set 'mode' to choose the comparison: equals, contains, not_contains, "
        "exists, absent, changed, unchanged. Give 'target' as the path, window "
        "title, or process name to inspect. Give a positive 'timeout_seconds' to "
        "poll until the condition holds instead of checking once. Prefer the "
        "cheapest method that can answer the question: 'file' and 'clipboard' "
        "are instant and exact, while 'ocr' is slow and can miss small text."
    ),
)
async def verify_action(
    method: str,
    mode: str = "equals",
    expected: str | None = None,
    target: str | None = None,
    tolerance: float = 0.0,
    region: list[int] | None = None,
    timeout_seconds: float = 0.0,
    condition: str | None = None,
) -> dict[str, Any]:

    request = VerificationRequest(
        method=method.strip().lower(),
        mode=parse_mode(mode),
        expected=expected,
        target=target,
        tolerance=tolerance,
        region=parse_region(region),
        condition=condition,
    )

    if timeout_seconds > 0:
        result = await verifier.wait_until(
            request,
            timeout_seconds=timeout_seconds,
        )

    else:
        # force=True: DESKTOP_VERIFY_ACTIONS switches off *automatic* read-back
        # after actions. Letting it disable the tool whose only job is to verify
        # would turn an explicit request into a silent "skipped".
        result = await verifier.verify(request, force=True)

    return result.to_dict()


@tool(
    category="desktop.verification",
    description=(
        "List the verification methods available on this machine, with a short "
        "description of each. Call this if a verify_action attempt was rejected "
        "for an unknown method."
    ),
)
async def list_verification_methods() -> dict[str, Any]:

    return {
        "methods": verifier.describe_methods(),
        "modes": sorted(item.value for item in MatchMode),
    }
