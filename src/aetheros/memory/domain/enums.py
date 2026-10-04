"""
Memory domain enumerations.

Every stable, closed set of values the memory layer reasons over lives here as a
``str``-backed ``Enum`` so it serialises to a plain string in SQLite, JSON and
events without a custom encoder, while staying a typed value in the code.

Two distinctions the project spec calls out explicitly are modelled as separate
enums rather than folded together:

* :class:`MemoryType` -- the *cognitive kind* (working / episodic / semantic /
  procedural / preference / failure / trading).
* :class:`Veracity` -- the *epistemic status* (fact vs prediction vs assumption
  vs observation vs model output vs user input). CLAUDE.md section 15 requires
  the system to keep these apart and to "never store a model prediction as a
  fact"; keeping veracity orthogonal to type is what makes that enforceable.
"""

from __future__ import annotations

from enum import Enum


class MemoryType(str, Enum):
    """The cognitive kind of a memory (spec Phase 1)."""

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PREFERENCE = "preference"
    FAILURE = "failure"
    TRADING = "trading"


class Veracity(str, Enum):
    """
    Epistemic status of a memory's content (CLAUDE.md section 15).

    Orthogonal to :class:`MemoryType`: a TRADING memory may hold a PREDICTION,
    while a SEMANTIC memory may hold a FACT. The consolidator and the trading
    integration both rely on this never silently promoting a PREDICTION or a
    MODEL_OUTPUT to FACT.
    """

    FACT = "fact"
    PREDICTION = "prediction"
    ASSUMPTION = "assumption"
    OBSERVATION = "observation"
    MODEL_OUTPUT = "model_output"
    USER_INPUT = "user_input"
    UNVERIFIED = "unverified"


class SourceType(str, Enum):
    """Where a memory originated -- its provenance channel (spec Rule 8)."""

    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
    TOOL = "tool"
    OBSERVATION = "observation"
    MODEL = "model"
    PREDICTION = "prediction"
    INFERENCE = "inference"
    CONSOLIDATION = "consolidation"
    DOCUMENT = "document"
    VISION = "vision"
    EXTERNAL = "external"


class MemoryStatus(str, Enum):
    """Lifecycle state of a memory (spec Phase 14)."""

    ACTIVE = "active"
    LOW_CONFIDENCE = "low_confidence"
    STALE = "stale"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    DELETED = "deleted"


class MemoryImportance(int, Enum):
    """
    How much a memory matters, as an ordered scale (spec Phase 13/21).

    ``int``-backed so it sorts and weights numerically; the scorer multiplies a
    normalised form of this into a memory's rank.
    """

    TRIVIAL = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

    @property
    def normalized(self) -> float:
        """Importance mapped onto [0, 1] for scoring."""
        return self.value / MemoryImportance.CRITICAL.value


class MemoryScope(str, Enum):
    """
    Retention class decided by the policy engine (spec Phase 21).

    Distinct from status: scope is the *intended* lifetime (set once), status is
    the *current* state (changes as a memory decays). A PERMANENT scope is what
    exempts a memory from automatic expiry (spec Phase 14).
    """

    EPHEMERAL = "ephemeral"
    SESSION = "session"
    TASK = "task"
    LONG_TERM = "long_term"
    PERMANENT = "permanent"


class PreferenceKind(str, Enum):
    """How a preference was established (spec Phase 1, type 5)."""

    EXPLICIT = "explicit"
    INFERRED = "inferred"
    TEMPORARY = "temporary"


class OutcomeStatus(str, Enum):
    """Result of an episode / action / recovery attempt (spec Phase 9/11)."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"
    UNKNOWN = "unknown"


class RelationType(str, Enum):
    """
    Common knowledge-graph edge labels (spec Phase 6).

    The graph store accepts any string label, but the recurring ones are named
    here so producers share spelling and the traversal helpers can special-case
    them. The spec's own examples (prefers / used_for / contains / uses) are all
    present.
    """

    PREFERS = "prefers"
    USED_FOR = "used_for"
    CONTAINS = "contains"
    USES = "uses"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    CAUSED_BY = "caused_by"
    PRODUCED = "produced"
    PRECEDED = "preceded"
    LOCATED_IN = "located_in"
    HAS_OUTCOME = "has_outcome"
    DERIVED_FROM = "derived_from"


def confidence_band(confidence: float) -> str:
    """
    Classify a [0, 1] confidence into a human band (spec Phase 13).

    A convenience for reporting and for the critic-style gating other layers
    do; the stored value is always the raw float.
    """

    if confidence >= 0.75:
        return "high"
    if confidence >= 0.45:
        return "medium"
    if confidence >= 0.2:
        return "low"
    return "very_low"
