"""
The execution-policy package (spec Phase 26 -- "Policy + Execution Safety").

:class:`~aetheros.trading.policy.policy_service.ExecutionPolicyService` is the
first gate on the §9 execution path -- Decision → **Policy** → Risk Validation
→ Execution Validation → Broker. It decides whether a fully-formed
:class:`~aetheros.trading.domain.execution.ExecutionRequest` is *permitted* to
move toward a venue at all, before the execution engine's account-level risk
gate runs. It computes no geometry and sizes nothing; it only judges mode,
per-trade risk cap, venue/instrument/strategy allow-lists and live
confirmation, and returns a deterministic
:class:`~aetheros.trading.domain.policy.PolicyVerdict`.
"""

from __future__ import annotations

from .policy_service import ExecutionPolicyService

__all__ = ["ExecutionPolicyService"]
