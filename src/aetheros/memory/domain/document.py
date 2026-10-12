"""
Document-ingestion value objects (Phase 17).

A :class:`DocumentSource` is one ingested artifact (a note file, a research
dump, a JSON/CSV knowledge export): its identity (origin + version), its
content checksum, and where ingestion got to (cursor). A
:class:`DocumentChunk` is one bounded, citable slice of it.

Content-addressed versions: a source's version IS its sha256 checksum.
Identical bytes re-ingested are the same version (idempotent no-op);
changed bytes are a new version whose chunks supersede the old ones (old
chunks archived with ``superseded_by`` links, never deleted silently).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import (
    MemoryImportance,
    MemoryType,
    SourceType,
    Veracity,
)
from .memory import Memory, MemorySource


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def checksum_text(text: str) -> str:
    """sha256 hex of UTF-8 text (source identity + change detection)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Formats this phase actually supports (stdlib only -- no PDF/DOCX/HTML
# libraries exist in this repo, and none are invented here).
SUPPORTED_FORMATS = ("txt", "md", "json", "jsonl", "csv")


@dataclass(slots=True)
class DocumentSource:
    """One registered ingestion source."""

    source_id: str
    origin: str
    format: str
    version: str = ""  # content checksum of the ingested bytes
    chunk_ids: list[str] = field(default_factory=list)
    chunks_total: int = 0
    cursor: int = 0  # next chunk index to index (resume point)
    status: str = "partial"  # partial | complete | archived
    scope: str = "long_term"
    ingested_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "origin": self.origin,
            "format": self.format,
            "version": self.version,
            "chunk_ids": list(self.chunk_ids),
            "chunks_total": self.chunks_total,
            "cursor": self.cursor,
            "status": self.status,
            "scope": self.scope,
            "ingested_at": self.ingested_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentSource:
        ingested = data.get("ingested_at")
        return cls(
            source_id=data["source_id"],
            origin=data.get("origin", ""),
            format=data.get("format", "txt"),
            version=data.get("version", ""),
            chunk_ids=list(data.get("chunk_ids", [])),
            chunks_total=int(data.get("chunks_total", 0)),
            cursor=int(data.get("cursor", 0)),
            status=data.get("status", "partial"),
            scope=data.get("scope", "long_term"),
            ingested_at=datetime.fromisoformat(ingested) if ingested else _utcnow(),
        )

    def to_memory(self) -> Memory:
        """The registry row: how to find every chunk and resume status."""
        return Memory(
            id=f"docsrc:{self.source_id}:{self.version or 'unversioned'}",
            content=(
                f"Document source '{self.origin}' ({self.format}): "
                f"{len(self.chunk_ids)}/{self.chunks_total} chunks "
                f"({self.status})."
            ),
            memory_type=MemoryType.SEMANTIC,
            veracity=Veracity.OBSERVATION,
            data={"document_source": self.to_dict()},
            source=MemorySource(
                source_type=SourceType.DOCUMENT,
                origin="document_ingestion",
                detail={"source_id": self.source_id},
            ),
            confidence=0.9,
            importance=MemoryImportance.NORMAL,
            tags=["document", "source", self.format],
            entities=[],
            metadata={"source_id": self.source_id, "doc_version": self.version},
        )


@dataclass(slots=True)
class DocumentChunk:
    """One bounded, citable slice of a source."""

    source_id: str
    index: int
    text: str
    ref: str = ""  # section heading / record index / row number / line range
    version: str = ""

    @property
    def id(self) -> str:
        # Deterministic: re-ingesting the same source+version+index is the
        # same row (idempotent via store()), never a duplicate.
        return f"doc:{self.source_id}:{self.version}:{self.index}"

    def to_memory(self) -> Memory:
        """A chunk row: UNVERIFIED evidence, never auto-verified knowledge.

        Imported text is untrusted by construction (spec Phase 17): it may
        contain wrong facts, prompt-injection prose, or secrets (the
        write-path validator redacts the latter before persistence). The
        citation (source/version/ref) travels in metadata so every hit is
        attributable to its exact origin.
        """
        return Memory(
            id=self.id,
            content=self.text,
            memory_type=MemoryType.SEMANTIC,
            veracity=Veracity.UNVERIFIED,
            data={
                "document_chunk": {
                    "source_id": self.source_id,
                    "index": self.index,
                    "ref": self.ref,
                    "version": self.version,
                }
            },
            source=MemorySource(
                source_type=SourceType.DOCUMENT,
                origin="document_ingestion",
                detail={"source_id": self.source_id, "ref": self.ref},
            ),
            confidence=0.5,
            importance=MemoryImportance.NORMAL,
            tags=["document", "chunk"],
            entities=[],
            metadata={
                "source_id": self.source_id,
                "doc_version": self.version,
                "chunk_index": self.index,
                "chunk_ref": self.ref,
            },
        )
