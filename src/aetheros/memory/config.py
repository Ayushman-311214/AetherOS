"""
Resolved memory configuration (spec Phase 23).

A single immutable snapshot of every memory knob, built once from the global
:class:`~aetheros.config.settings.Settings`. Services depend on this object, not
on ``Settings`` or ``os.getenv``, so configuration is read in exactly one place
(CLAUDE.md §18) and tests can construct a config without a full environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config.settings import Settings


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    """Immutable, fully-resolved memory settings."""

    enabled: bool
    database_path: Path
    vector_provider: str
    embedding_model: str
    embedding_dim: int
    retrieval_limit: int
    similarity_threshold: float
    decay_enabled: bool
    decay_halflife_days: float
    consolidation_enabled: bool
    dedup_threshold: float
    max_working_context: int
    auto_remember: bool
    agent_recall_limit: int
    agent_recall_min_score: float
    agent_recall_max_chars: int

    @classmethod
    def from_settings(cls, settings: Settings) -> MemoryConfig:
        raw = Path(settings.MEMORY_DATABASE)
        database_path = raw if raw.is_absolute() else settings.DATA_DIR / raw
        return cls(
            enabled=bool(settings.ENABLE_MEMORY),
            database_path=database_path,
            vector_provider=settings.MEMORY_VECTOR_PROVIDER.strip().lower(),
            embedding_model=settings.MEMORY_EMBEDDING_MODEL,
            embedding_dim=int(settings.MEMORY_EMBEDDING_DIM),
            retrieval_limit=int(settings.MEMORY_RETRIEVAL_LIMIT),
            similarity_threshold=float(settings.MEMORY_SIMILARITY_THRESHOLD),
            decay_enabled=bool(settings.MEMORY_DECAY_ENABLED),
            decay_halflife_days=float(settings.MEMORY_DECAY_HALFLIFE_DAYS),
            consolidation_enabled=bool(settings.MEMORY_CONSOLIDATION_ENABLED),
            dedup_threshold=float(settings.MEMORY_DEDUP_THRESHOLD),
            max_working_context=int(settings.MEMORY_MAX_WORKING_CONTEXT),
            auto_remember=bool(settings.MEMORY_AUTO_REMEMBER),
            agent_recall_limit=int(settings.MEMORY_AGENT_RECALL_LIMIT),
            agent_recall_min_score=float(settings.MEMORY_AGENT_RECALL_MIN_SCORE),
            agent_recall_max_chars=int(settings.MEMORY_AGENT_RECALL_MAX_CHARS),
        )

    @classmethod
    def for_memory_db(cls, database_path: Path, *, embedding_dim: int = 256) -> MemoryConfig:
        """
        A minimal config for tests / embedded use.

        Everything enabled, pointed at ``database_path``, hashing embedder.
        """
        return cls(
            enabled=True,
            database_path=database_path,
            vector_provider="hashing",
            embedding_model="",
            embedding_dim=embedding_dim,
            retrieval_limit=5,
            similarity_threshold=0.0,
            decay_enabled=True,
            decay_halflife_days=30.0,
            consolidation_enabled=True,
            dedup_threshold=0.95,
            max_working_context=50,
            auto_remember=True,
            agent_recall_limit=5,
            agent_recall_min_score=0.0,
            agent_recall_max_chars=1500,
        )
