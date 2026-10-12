"""
AetherOS Memory domain model (spec Phase 3).

Clean, storage-free value objects. Nothing here imports SQLite, the event bus or
any service -- domain logic only, with lossless ``to_dict`` / ``from_dict``
serialisation so a memory round-trips through persistence, events and tools
unchanged (Rule 8 -- preserve provenance).
"""

from __future__ import annotations

from .content_policy import (
    MAX_CONTENT_CHARS,
    MAX_PAYLOAD_BYTES,
    ContentPolicy,
    SecretAction,
    redact_text,
    scan_secrets,
)
from .document import DocumentChunk, DocumentSource, checksum_text
from .enums import (
    RECALLABLE_STATUSES,
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
from .episode import ActionRecord, Episode, EpisodeObservation, Outcome
from .memory import Memory, MemoryLink, MemorySource, new_id, utcnow
from .preference import FailureRecord, Preference, RecoveryAttempt
from .procedure import Procedure, ProcedureStep
from .query import MemoryQuery, MemoryResult, RetrievalExplanation, RetrievalReport
from .semantic import Entity, Relationship
from .trading import (
    AnalysisSnapshotMemory,
    CalibrationRecordMemory,
    MarketRegimeMemory,
    PredictionMemory,
    PredictionOutcomeMemory,
    ReasoningSummaryMemory,
    StrategyObservationMemory,
)

__all__ = [
    # enums
    "MemoryType",
    "Veracity",
    "SourceType",
    "MemoryStatus",
    "RECALLABLE_STATUSES",
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
    # content safety
    "ContentPolicy",
    "SecretAction",
    "scan_secrets",
    "redact_text",
    "MAX_CONTENT_CHARS",
    "MAX_PAYLOAD_BYTES",
    # query
    "MemoryQuery",
    "MemoryResult",
    "RetrievalExplanation",
    "RetrievalReport",
    # episodic
    "Episode",
    "ActionRecord",
    "EpisodeObservation",
    "Outcome",
    # document ingestion
    "DocumentSource",
    "DocumentChunk",
    "checksum_text",
    # semantic graph
    "Entity",
    "Relationship",
    # procedural
    "Procedure",
    "ProcedureStep",
    # preference / failure
    "Preference",
    "FailureRecord",
    "RecoveryAttempt",
    # trading
    "PredictionMemory",
    "PredictionOutcomeMemory",
    "MarketRegimeMemory",
    "AnalysisSnapshotMemory",
    "StrategyObservationMemory",
    "CalibrationRecordMemory",
    "ReasoningSummaryMemory",
]
