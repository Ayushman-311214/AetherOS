"""
AetherOS Memory domain model (spec Phase 3).

Clean, storage-free value objects. Nothing here imports SQLite, the event bus or
any service -- domain logic only, with lossless ``to_dict`` / ``from_dict``
serialisation so a memory round-trips through persistence, events and tools
unchanged (Rule 8 -- preserve provenance).
"""

from __future__ import annotations

from .enums import (
    MemoryImportance,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    OutcomeStatus,
    PreferenceKind,
    RelationType,
    SourceType,
    Veracity,
    confidence_band,
)
from .episode import ActionRecord, Episode, Outcome
from .memory import Memory, MemoryLink, MemorySource, new_id, utcnow
from .preference import FailureRecord, Preference
from .procedure import Procedure, ProcedureStep
from .query import MemoryQuery, MemoryResult, RetrievalExplanation
from .semantic import Entity, Relationship
from .trading import PredictionMemory, PredictionOutcomeMemory

__all__ = [
    # enums
    "MemoryType",
    "Veracity",
    "SourceType",
    "MemoryStatus",
    "MemoryImportance",
    "MemoryScope",
    "PreferenceKind",
    "OutcomeStatus",
    "RelationType",
    "confidence_band",
    # core
    "Memory",
    "MemorySource",
    "MemoryLink",
    "new_id",
    "utcnow",
    # query
    "MemoryQuery",
    "MemoryResult",
    "RetrievalExplanation",
    # episodic
    "Episode",
    "ActionRecord",
    "Outcome",
    # semantic graph
    "Entity",
    "Relationship",
    # procedural
    "Procedure",
    "ProcedureStep",
    # preference / failure
    "Preference",
    "FailureRecord",
    # trading
    "PredictionMemory",
    "PredictionOutcomeMemory",
]
