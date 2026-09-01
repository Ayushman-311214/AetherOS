"""
Verification — reading state back after a desktop action.

The public surface is deliberately small: tools build a
:class:`VerificationRequest`, hand it to the shared :data:`verifier`, and return
the :class:`VerificationResult` inside a :class:`ToolResult`.
"""

from .result import (
    ToolResult,
    VerificationResult,
    VerificationStatus,
)

from .strategy import (
    STRATEGIES,
    MatchMode,
    VerificationRequest,
    VerificationStrategy,
)

from .verifier import (
    Verifier,
    verifier,
)

__all__ = [
    # Results
    "ToolResult",
    "VerificationResult",
    "VerificationStatus",

    # Requests and strategies
    "STRATEGIES",
    "MatchMode",
    "VerificationRequest",
    "VerificationStrategy",

    # Dispatch
    "Verifier",
    "verifier",
]
