"""
Safety — the gates every destructive desktop action passes through.

Two independent concerns, kept in separate modules because they answer different
questions: :mod:`paths` decides *where* a tool may act, :mod:`policy` decides
*whether* it may act at all.
"""

from .paths import (
    PathAccess,
    PathGuard,
    PathVerdict,
    path_guard,
)

from .policy import (
    Capability,
    Decision,
    PolicyDecision,
    RiskLevel,
    SafetyPolicy,
    safety_policy,
)

__all__ = [
    # Paths
    "PathAccess",
    "PathGuard",
    "PathVerdict",
    "path_guard",

    # Policy
    "Capability",
    "Decision",
    "PolicyDecision",
    "RiskLevel",
    "SafetyPolicy",
    "safety_policy",
]
