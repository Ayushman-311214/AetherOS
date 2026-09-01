"""
The result contract every desktop tool returns.

Before this module every desktop action tool returned ``None``. A model calling
``click`` therefore received the same answer whether the click landed, whether
pyautogui silently no-oped against an unfocused window, or whether the
coordinates were off-screen and clamped. There was no way to tell, and an agent
that cannot tell will happily build ten more steps on top of a failure.

Two values are reported separately and deliberately:

``success``
    The operation executed without raising, *and* verification did not actively
    contradict it.

``verified``
    An independent read-back confirmed the new state. This is the stronger
    claim, and it is only ever true when a strategy actually checked something.

They are separate because collapsing them would force a lie in one direction or
the other: some actions genuinely cannot be verified (``scroll`` leaves no
queryable state), and reporting those as unverified-but-successful is the honest
answer. What must never happen is ``verified: true`` without a real check — see
:class:`VerificationStatus.UNSUPPORTED`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class VerificationStatus(str, Enum):
    """
    Outcome of the verification pass for a single action.

    ``str`` mixin so the value survives JSON encoding for the model without a
    custom encoder.
    """

    VERIFIED = "verified"
    """Read-back confirmed the expected state."""

    FAILED = "failed"
    """Read-back contradicted the expected state. The action did not take."""

    UNSUPPORTED = "unsupported"
    """
    No verification is possible for this action.

    ``scroll`` and ``key_up`` are the honest examples: the OS exposes no state
    to read back. Distinct from SKIPPED because this is a permanent property of
    the action, not a runtime choice.
    """

    SKIPPED = "skipped"
    """Verification was available but switched off by configuration or caller."""

    ERROR = "error"
    """
    The verification attempt itself raised.

    Deliberately not the same as FAILED: a broken *check* is not evidence that
    the *action* failed, and conflating them would report false negatives on a
    machine where, say, the window backend is unavailable.
    """


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """
    What was checked, what was expected, and what was actually observed.

    The four fields ``verified`` / ``condition`` / ``expected`` / ``actual`` are
    the shape the ``verify_action`` tool contract requires, and they are what
    makes a failure diagnosable rather than merely reported: "expected (785,963),
    actual (785,0)" tells an agent the Y coordinate was clamped, where
    "verification failed" tells it nothing.
    """

    status: VerificationStatus
    condition: str
    method: str = "none"
    expected: Any = None
    actual: Any = None
    detail: str | None = None

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def verified(self) -> bool:
        """
        True only for a real, passing check.

        UNSUPPORTED and SKIPPED are both false here. That is the whole point:
        "we did not look" must never read as "we looked and it was fine".
        """

        return self.status is VerificationStatus.VERIFIED

    @property
    def contradicted(self) -> bool:
        """
        True when read-back actively disagreed with the expectation.

        This is the only status that can turn a tool result into a failure.
        """

        return self.status is VerificationStatus.FAILED

    # ==========================================================
    # Constructors
    # ==========================================================

    @classmethod
    def passed(
        cls,
        condition: str,
        *,
        method: str,
        expected: Any = None,
        actual: Any = None,
        detail: str | None = None,
    ) -> VerificationResult:

        return cls(
            status=VerificationStatus.VERIFIED,
            condition=condition,
            method=method,
            expected=expected,
            actual=actual,
            detail=detail,
        )

    @classmethod
    def failed(
        cls,
        condition: str,
        *,
        method: str,
        expected: Any = None,
        actual: Any = None,
        detail: str | None = None,
    ) -> VerificationResult:

        return cls(
            status=VerificationStatus.FAILED,
            condition=condition,
            method=method,
            expected=expected,
            actual=actual,
            detail=detail,
        )

    @classmethod
    def unsupported(
        cls,
        condition: str,
        *,
        detail: str | None = None,
    ) -> VerificationResult:
        """
        Declare that this action cannot be verified, and say why.

        The ``detail`` is not optional in spirit: an agent reading
        ``unsupported`` needs to know whether to retry, look at the screen, or
        accept the result.
        """

        return cls(
            status=VerificationStatus.UNSUPPORTED,
            condition=condition,
            method="none",
            detail=detail,
        )

    @classmethod
    def skipped(
        cls,
        condition: str,
        *,
        detail: str | None = None,
    ) -> VerificationResult:

        return cls(
            status=VerificationStatus.SKIPPED,
            condition=condition,
            method="none",
            detail=detail,
        )

    @classmethod
    def errored(
        cls,
        condition: str,
        *,
        method: str,
        detail: str,
    ) -> VerificationResult:

        return cls(
            status=VerificationStatus.ERROR,
            condition=condition,
            method=method,
            detail=detail,
        )

    # ==========================================================
    # Serialisation
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:

        return {
            "verified": self.verified,
            "status": self.status.value,
            "condition": self.condition,
            "method": self.method,
            "expected": self.expected,
            "actual": self.actual,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class ToolResult:
    """
    Outcome of one desktop action, as the model sees it.

    Distinct from :class:`~aetheros.tools.executor.ToolExecutionResult`, which
    describes the *invocation* (unknown tool, bad arguments, timeout) and is
    produced by the executor. This describes the *action*, and is produced by the
    tool itself. A tool returns this as a dict; the executor then wraps that dict.
    """

    action: str
    executed: bool
    verification: VerificationResult
    value: Any = None
    error: str | None = None
    duration_ms: float = 0.0

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def success(self) -> bool:
        """
        Whether the caller may proceed as if the action happened.

        False when the backend raised, and false when read-back actively
        contradicted the action. An unverifiable action that executed cleanly is
        a success with ``verified: false`` — the caller gets both facts and can
        decide.
        """

        return self.executed and not self.verification.contradicted

    # ==========================================================
    # Constructors
    # ==========================================================

    @classmethod
    def ok(
        cls,
        action: str,
        *,
        verification: VerificationResult,
        value: Any = None,
        duration_ms: float = 0.0,
    ) -> ToolResult:
        """
        The action executed. ``verification`` still decides ``success``.

        There is no overload that skips verification: passing a
        :meth:`VerificationResult.unsupported` is an explicit, reviewable
        admission, where a defaulted argument would let unverified actions
        accumulate silently.
        """

        return cls(
            action=action,
            executed=True,
            verification=verification,
            value=value,
            duration_ms=duration_ms,
        )

    @classmethod
    def failure(
        cls,
        action: str,
        *,
        error: str,
        verification: VerificationResult | None = None,
        value: Any = None,
        duration_ms: float = 0.0,
    ) -> ToolResult:
        """
        The action did not execute. ``success`` is false regardless of anything
        else in the result.
        """

        return cls(
            action=action,
            executed=False,
            verification=(
                verification
                or VerificationResult.skipped(
                    action,
                    detail="Action did not execute; nothing to verify.",
                )
            ),
            value=value,
            error=error,
            duration_ms=duration_ms,
        )

    # ==========================================================
    # Serialisation
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        The JSON shape the model receives.

        ``verified`` is lifted to the top level alongside ``success`` because a
        model reading a nested object will reliably notice the outer key and
        unreliably notice the inner one.
        """

        payload: dict[str, Any] = {
            "action": self.action,
            "success": self.success,
            "verified": self.verification.verified,
            "verification": self.verification.to_dict(),
        }

        if self.value is not None:
            payload["value"] = self.value

        if self.error is not None:
            payload["error"] = self.error

        if self.duration_ms:
            payload["duration_ms"] = round(self.duration_ms, 2)

        return payload
