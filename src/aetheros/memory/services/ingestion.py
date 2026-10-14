"""
Document and knowledge ingestion (Phase 17).

Memory-facing ingestion for the formats this repo can actually parse with
the standard library -- plain text, Markdown (structure only), JSON/JSONL
records and CSV rows -- using existing write-path machinery (validation,
redaction, idempotent store, version-guarded updates). No new parsers are
invented: PDF/DOCX/HTML have no extraction libraries in this repo and are
explicitly unsupported (see ``SUPPORTED_FORMATS`` and
``verify_ingestion_contract``); remote-URL fetching is unsupported (no URL
policy layer exists to enforce).

Lifecycle of a source:

.. code-block:: text

    ingest (new bytes) -> chunk (bounded) -> store each (idempotent)
         |                      |
         v                      v
    same checksum:          new checksum: new version row, old chunks
    no-op (same id)         archived + superseded_by links (vectors
                            dropped inline: no orphans, no stale hits)

Resumability: chunks index in order and the source row's ``cursor``
advances after each stored chunk. An interrupted run re-ingested resumes
after the cursor (idempotency keys make replays safe); a partially
processed source reports ``status=partial`` until the last chunk lands.

Removal (``remove_source``): every chunk of every version archives
(``archived_reason=document_source_removed``) with vectors deleted inline,
and the source row archives too. Nothing stays recallable; everything
stays auditable via direct reads. No orphaned chunks, no stale vectors
(``verify_projection`` agrees: archived rows need no vectors, Phase 14).

Corrections flow through versions, not edits: corrected bytes are simply
a new checksum, hence a new version; the old version archives with links.
There is intentionally no in-place chunk edit path.

Untrusted by construction: chunk rows are UNVERIFIED veracity with the
exact citation (source/version/ref) in metadata. Malicious instruction
prose inside a source persists as inert data (retrieval already treats
stored content as untrusted context, never instructions). Secrets pass
through the write-path validator (redact-by-default) before persistence
and before embedding -- redaction happens on the validated content, so
the embedded text is the redacted text.

Bounded: chunk chars (default 2000, hard-capped below the 20k validator
limit), source bytes (default 1 MiB cap -- a document, not a corpus dump;
larger inputs are rejected, not truncated silently), file reads resolve
through one explicit local path (no URLs, no globs, no directory walks).
No second bus: everything flows through store/update/get/link.
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...core.errors.memory_error import (
    MemoryNotFoundError,
    MemoryStorageError,
    MemoryValidationError,
)
from ...core.logging import get_logger
from ..domain.document import (
    SUPPORTED_FORMATS,
    DocumentChunk,
    DocumentSource,
    checksum_text,
)
from ..domain.enums import MemoryScope, MemoryStatus
from ..domain.memory import Memory
from .results import WriteStatus

if TYPE_CHECKING:
    from .manager import MemoryManager

logger = get_logger("memory.ingestion")

# Bounded budgets. Chunks must fit the 20k write-path content cap with room
# for validator/redaction overhead; sources are capped so one ingest call
# can never wedge memory, embeddings or the LLM context behind it.
DEFAULT_CHUNK_CHARS = 2000
MAX_CHUNK_CHARS = 8000
MAX_SOURCE_BYTES = 1_000_000
MAX_CHUNKS_PER_SOURCE = 500

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def _split_text(text: str, *, chunk_chars: int) -> list[tuple[str, str]]:
    """Split prose into (ref, text) chunks, keeping Markdown section refs.

    A ``# Heading`` line opens a section: following chunks cite it until
    the next heading. Long sections split on paragraph boundaries first,
    then hard-cut as a last resort (no chunk exceeds the budget).
    """
    section = "top"
    paras: list[tuple[str, str]] = []
    buf: list[str] = []
    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            if buf:
                paras.append((section, "\n".join(buf).strip()))
                buf = []
            section = match.group(2).strip()
            continue
        if line.strip():
            buf.append(line)
        elif buf:
            paras.append((section, "\n".join(buf).strip()))
            buf = []
    if buf:
        paras.append((section, "\n".join(buf).strip()))

    chunks: list[tuple[str, str]] = []
    for ref, para in paras:
        if not para:
            continue
        while len(para) > chunk_chars:
            chunks.append((ref, para[:chunk_chars]))
            para = para[chunk_chars:]
        if para:
            chunks.append((ref, para))
    if not chunks and text.strip():
        clipped = text.strip()
        while len(clipped) > chunk_chars:
            chunks.append((section, clipped[:chunk_chars]))
            clipped = clipped[chunk_chars:]
        if clipped:
            chunks.append((section, clipped))
    return chunks


def _split_json(text: str) -> list[tuple[str, str]]:
    """One chunk per record (object key / array index / bare value)."""
    payload = json.loads(text)
    chunks: list[tuple[str, str]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            chunks.append((f"key:{key}", json.dumps(value, ensure_ascii=False)))
    elif isinstance(payload, list):
        for i, value in enumerate(payload):
            chunks.append((f"index:{i}", json.dumps(value, ensure_ascii=False)))
    else:
        chunks.append(("value:0", json.dumps(payload, ensure_ascii=False)))
    return chunks


def _split_csv(text: str) -> list[tuple[str, str]]:
    """One chunk per data row (header + row number as the ref)."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise MemoryValidationError(
            "CSV source has no header row.",
            hint="Provide a header line followed by data rows.",
        )
    chunks: list[tuple[str, str]] = []
    for i, row in enumerate(reader, start=1):
        chunks.append((f"row:{i}", json.dumps(row, ensure_ascii=False)))
    if not chunks:
        raise MemoryValidationError(
            "CSV source has a header but no data rows.",
            hint="Provide at least one data row.",
        )
    return chunks


class DocumentIngestion:
    """Bounded, resumable, idempotent document ingestion.

    Constructed once by :class:`MemoryManager` (see the ``documents``
    accessor); holds no source state itself (the source registry row is
    the state, so restart resumes naturally).
    """

    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    async def ingest_text(
        self,
        text: str,
        *,
        origin: str,
        format: str = "txt",
        source_id: str | None = None,
        scope: str = "long_term",
        chunk_chars: int = DEFAULT_CHUNK_CHARS,
    ) -> DocumentSource:
        """Ingest in-memory text (caller-read bytes, never fetched here).

        ``format`` is one of txt/md/json/jsonl/csv (jsonl splits per line
        as JSON records). Idempotent: identical bytes for the same
        ``source_id`` return the stored source without writing. Changed
        bytes supersede the previous version (old chunks archived +
        linked, vectors dropped inline).
        """
        fmt = (format or "txt").strip().lower()
        if fmt not in SUPPORTED_FORMATS:
            raise MemoryValidationError(
                f"Unsupported document format {format!r}.",
                hint=f"Supported: {', '.join(SUPPORTED_FORMATS)}. PDF/DOCX/HTML "
                "have no extraction libraries in this repo and remote URLs "
                "have no fetch policy -- both are explicitly unsupported.",
            )
        if fmt == "jsonl":
            chunks = self._split_jsonl(text)
        elif fmt == "json":
            try:
                chunks = _split_json(text)
            except (ValueError, TypeError) as exc:
                raise MemoryValidationError(
                    f"JSON source does not parse: {exc}",
                    hint="Provide valid JSON (object, array or value).",
                ) from exc
        elif fmt == "csv":
            chunks = _split_csv(text)
        else:
            chunks = _split_text(text, chunk_chars=self._chunk_budget(chunk_chars))
        for ref, body in chunks:
            if len(body) > MAX_CHUNK_CHARS:
                raise MemoryValidationError(
                    f"A {fmt} unit exceeds the {MAX_CHUNK_CHARS}-char chunk cap "
                    f"(ref {ref!r}).",
                    hint="Split the record; oversized units are rejected, "
                    "never silently truncated.",
                )
        if len(chunks) > MAX_CHUNKS_PER_SOURCE:
            raise MemoryValidationError(
                f"Source yields {len(chunks)} chunks (cap {MAX_CHUNKS_PER_SOURCE}).",
                hint="Ingest a smaller slice; sources are documents, not dumps.",
            )
        if not chunks:
            raise MemoryValidationError(
                "Source produced no ingestible content.",
                hint="Provide non-empty text, records or rows.",
            )
        self._ensure_enabled("ingest")
        sid = (source_id or "").strip() or f"src:{checksum_text(origin)[:12]}"
        version = checksum_text(text)
        return await self._index(sid, origin, fmt, version, chunks, scope=scope)

    async def ingest_file(
        self,
        path: str | Path,
        *,
        origin: str | None = None,
        format: str | None = None,
        source_id: str | None = None,
        scope: str = "long_term",
        chunk_chars: int = DEFAULT_CHUNK_CHARS,
        max_bytes: int = MAX_SOURCE_BYTES,
    ) -> DocumentSource:
        """Ingest one explicit local file (no URLs, globs or directories).

        The path must name a regular file within the byte budget; parents
        are never walked. ``format`` defaults from the suffix.
        """
        raw = str(path).strip()
        if raw.lower().startswith(("http://", "https://", "ftp://")):
            raise MemoryValidationError(
                f"Remote ingestion is unsupported: {raw[:80]}",
                hint="Ingest local files or pass caller-read text to ingest_text.",
            )
        p = Path(raw)
        if not p.is_file():
            raise MemoryNotFoundError(f"No regular file at {raw[:200]!r}.")
        size = p.stat().st_size
        if size > max_bytes:
            raise MemoryValidationError(
                f"File is {size} bytes (cap {max_bytes}).",
                hint="Ingest a smaller slice; oversize inputs are rejected, "
                "never silently truncated.",
            )
        fmt = (format or p.suffix.lstrip(".") or "txt").strip().lower()
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise MemoryValidationError(
                f"Cannot read {p.name} as UTF-8 text: {exc}",
                hint="Only UTF-8 text formats are supported "
                f"({', '.join(SUPPORTED_FORMATS)}).",
            ) from exc
        return await self.ingest_text(
            text,
            origin=origin or p.name,
            format=fmt,
            source_id=source_id,
            scope=scope,
            chunk_chars=chunk_chars,
        )

    # ------------------------------------------------------------------
    # Source administration
    # ------------------------------------------------------------------

    async def get_source(
        self, source_id: str, *, version: str | None = None
    ) -> DocumentSource | None:
        """The registry row for a source (latest version unless pinned)."""
        if version is not None:
            row = await self._manager.get(f"docsrc:{source_id}:{version}")
            if row is None:
                return None
            payload = row.data.get("document_source")
            return (
                DocumentSource.from_dict(payload) if isinstance(payload, dict) else None
            )
        rows = await self._manager._repo.find_by_metadata("source_id", source_id)
        best: DocumentSource | None = None
        for row in rows:
            payload = row.data.get("document_source")
            if not isinstance(payload, dict):
                continue
            candidate = DocumentSource.from_dict(payload)
            if best is None or candidate.ingested_at > best.ingested_at:
                best = candidate
        return best

    async def source_chunks(
        self, source_id: str, *, version: str | None = None, limit: int = 500
    ) -> list[Memory]:
        """Chunk rows for a source version (newest version unless pinned)."""
        source = await self.get_source(source_id, version=version)
        if source is None:
            raise MemoryNotFoundError(f"No source with id {source_id!r}.")
        out: list[Memory] = []
        for cid in source.chunk_ids[: max(1, int(limit))]:
            row = await self._manager.get(cid)
            if row is not None:
                out.append(row)
        return out

    async def remove_source(self, source_id: str) -> dict[str, Any]:
        """Archive every version of a source (chunks + registry rows).

        Nothing stays recallable; everything stays auditable via direct
        reads. Vectors drop inline per chunk (bounded loop, best-effort
        with repair as backstop): no orphaned chunks, no stale vectors.
        Returns counts for verification.
        """
        self._ensure_enabled("remove_source")
        rows = await self._manager._repo.find_by_metadata("source_id", source_id)
        archived_chunks = 0
        archived_sources = 0
        vectors_dropped = 0
        for row in rows:
            payload_chunk = row.data.get("document_chunk")
            payload_source = row.data.get("document_source")
            if payload_chunk is None and payload_source is None:
                continue
            if row.status is MemoryStatus.ARCHIVED:
                continue
            archive_ok = await self._archive_row(row, reason="document_source_removed")
            if not archive_ok:
                continue
            try:
                await self._manager._vectors.delete(row.id)
                vectors_dropped += 1
            except Exception as exc:  # noqa: BLE001 - repair backstops
                logger.bind(memory_id=row.id, error=str(exc)).debug(
                    "Vector drop on source removal skipped."
                )
            if payload_chunk is not None:
                archived_chunks += 1
            else:
                archived_sources += 1
        return {
            "source_id": source_id,
            "archived_chunks": archived_chunks,
            "archived_sources": archived_sources,
            "vectors_dropped": vectors_dropped,
        }

    async def verify_ingestion_contract(self) -> dict[str, Any]:
        """Honest capability ledger (no invented formats or fetching)."""
        return {
            "adapter": "DocumentIngestion",
            "supported_formats": list(SUPPORTED_FORMATS),
            "unsupported": {
                "pdf/docx/html": "no extraction libraries in this repo; "
                "adding any is a dependency decision, not taken here",
                "remote URLs": "no URL fetch policy layer exists to enforce; "
                "callers pass already-read text",
                "binary/OCR/scanned": "no vision/OCR path in this phase",
            },
            "budgets": {
                "chunk_chars_default": DEFAULT_CHUNK_CHARS,
                "chunk_chars_max": MAX_CHUNK_CHARS,
                "source_bytes_max": MAX_SOURCE_BYTES,
                "chunks_per_source_max": MAX_CHUNKS_PER_SOURCE,
            },
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_enabled(self, verb: str) -> None:
        """Refuse admin writes while the subsystem is off (controls precedent).

        The chunk loop already treats a store-level UNAVAILABLE honestly by
        stopping without claiming progress, but the archive paths below
        write through the repository directly -- without this gate a
        disabled-mode ingest would archive the old version while persisting
        nothing to replace it.
        """
        if not self._manager.config.enabled:
            raise MemoryValidationError(
                f"{verb}() refused: memory is disabled.",
                hint="Enable memory first (ENABLE_MEMORY=true).",
            )

    @staticmethod
    def _chunk_budget(chunk_chars: int) -> int:
        return max(256, min(int(chunk_chars), MAX_CHUNK_CHARS))

    @staticmethod
    def _split_jsonl(text: str) -> list[tuple[str, str]]:
        chunks: list[tuple[str, str]] = []
        for i, line in enumerate(text.splitlines()):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise MemoryValidationError(
                    f"JSONL line {i + 1} does not parse: {exc}",
                    hint="Provide one JSON value per non-empty line.",
                ) from exc
            chunks.append((f"line:{i + 1}", json.dumps(payload, ensure_ascii=False)))
        return chunks

    async def _index(
        self,
        source_id: str,
        origin: str,
        fmt: str,
        version: str,
        chunks: list[tuple[str, str]],
        *,
        scope: str,
    ) -> DocumentSource:
        # Same bytes already ingested? Return the stored source (no-op).
        existing = await self._manager.get(f"docsrc:{source_id}:{version}")
        if existing is not None:
            payload = existing.data.get("document_source")
            if isinstance(payload, dict):
                stored_source = DocumentSource.from_dict(payload)
                if stored_source.status == "complete" and len(
                    stored_source.chunk_ids
                ) >= len(chunks):
                    return stored_source

        # New version: supersede any previous version's chunks first, so no
        # stale projection of the old text stays visible.
        await self._supersede_previous(source_id, version)

        source = DocumentSource(
            source_id=source_id,
            origin=origin,
            format=fmt,
            version=version,
            chunks_total=len(chunks),
            scope=scope,
        )
        # Resume point: a partial source row from an interrupted run tells
        # us where to continue (chunk ids are deterministic, so replay is
        # safe regardless).
        partial = await self._partial_source(source_id, version)
        start = partial.cursor if partial is not None else 0
        if partial is not None:
            source.chunk_ids = list(partial.chunk_ids)

        try:
            wanted_scope = MemoryScope(scope)
        except ValueError:
            wanted_scope = MemoryScope.LONG_TERM

        for index in range(start, len(chunks)):
            ref, body = chunks[index]
            chunk = DocumentChunk(
                source_id=source_id,
                index=index,
                text=body,
                ref=ref,
                version=version,
            )
            memory = chunk.to_memory()
            # An explicit caller scope wins (the policy never downgrades a
            # deliberate choice); ingestion always asks for a durable one.
            memory.scope = wanted_scope
            result = await self._manager.store(memory, idempotency_key=chunk.id)
            if result.status is WriteStatus.STORED and result.memory is not None:
                stored = result.memory
            elif result.status is WriteStatus.SKIPPED and "already stored" in (
                result.reason or ""
            ):
                stored = result.memory if result.memory is not None else memory
            elif result.status is WriteStatus.FAILED:
                raise MemoryStorageError(
                    f"Chunk {chunk.id!r} was attempted but not persisted: "
                    f"{result.reason or 'unknown storage failure'}.",
                    hint="Check the database and the embedding provider, "
                    "then re-ingest to resume from the cursor.",
                )
            else:
                # UNAVAILABLE (disabled / not started) or policy-declined
                # SKIPPED: never claim progress for an unpersisted chunk.
                # The partial source row records how far we got; re-ingest
                # resumes from the cursor.
                logger.debug("Chunk not persisted: %s", result.reason)
                break
            if stored.id not in source.chunk_ids:
                source.chunk_ids.append(stored.id)
            source.cursor = index + 1
            source.status = "complete" if source.cursor >= len(chunks) else "partial"
            await self._write_source_row(source)

        if source.cursor >= len(chunks):
            source.status = "complete"
            await self._write_source_row(source)
        return source

    async def _partial_source(
        self, source_id: str, version: str
    ) -> DocumentSource | None:
        row = await self._manager.get(f"docsrc:{source_id}:{version}")
        if row is None:
            return None
        payload = row.data.get("document_source")
        if not isinstance(payload, dict):
            return None
        source = DocumentSource.from_dict(payload)
        if source.status == "complete":
            return None
        return source

    async def _write_source_row(self, source: DocumentSource) -> None:
        memory = source.to_memory()
        existing = await self._manager.get(memory.id)
        if existing is None:
            result = await self._manager.store(memory, idempotency_key=memory.id)
            if result.status is WriteStatus.FAILED:
                raise MemoryStorageError(
                    f"Source row {memory.id!r} was attempted but not persisted: "
                    f"{result.reason or 'unknown storage failure'}.",
                    hint="Check the database and the embedding provider, "
                    "then re-ingest to resume from the cursor.",
                )
            # UNAVAILABLE / policy-declined: the next successful chunk write
            # retries the row; progress itself is never overstated.
            if result.status not in (WriteStatus.STORED, WriteStatus.SKIPPED):
                logger.debug("Source row not persisted: %s", result.reason)
            return
        await self._manager.update(
            memory.id,
            expected_version=existing.version,
            content=memory.content,
            data=memory.data,
            metadata=memory.metadata,
        )

    async def _archive_row(
        self, row: Memory, *, reason: str, extra: dict[str, Any] | None = None
    ) -> bool:
        """Flip one row to ARCHIVED under a version guard.

        Returns False on a lost race (a concurrent edit won; its write
        stands and the next pass re-evaluates) -- the lifecycle's
        ``_transition_one`` pattern, minus the clock. The version is
        bumped before the guarded write (the guard matches on the old
        version; the row carries the new one).
        """
        expected_version = row.version
        row.status = MemoryStatus.ARCHIVED
        row.metadata["archived_reason"] = reason
        if extra:
            row.metadata.update(extra)
        row.version += 1
        won = await self._manager._repo.update_guarded(row, expected_version)
        if not won:
            logger.bind(memory_id=row.id).debug(
                "Archive skipped: concurrent edit won the race."
            )
            return False
        return True

    async def _supersede_previous(self, source_id: str, version: str) -> int:
        """Archive other versions' chunks (vectors dropped inline).

        Returns how many chunks were archived. The registry rows of old
        versions stay (audit trail of what changed when); their chunks
        leave recall. Supersede links chain versions for provenance.
        """
        archived = 0
        rows = await self._manager._repo.find_by_metadata("source_id", source_id)
        for row in rows:
            chunk_payload = row.data.get("document_chunk")
            if chunk_payload is None:
                continue
            if not isinstance(chunk_payload, dict):
                continue
            if chunk_payload.get("version") == version:
                continue
            if row.status is MemoryStatus.ARCHIVED:
                continue
            old_version = str(chunk_payload.get("version", ""))
            archive_ok = await self._archive_row(
                row,
                reason="document_version_superseded",
                extra={"superseded_by": version},
            )
            if not archive_ok:
                continue
            try:
                await self._manager._vectors.delete(row.id)
            except Exception as exc:  # noqa: BLE001 - repair backstops
                logger.bind(memory_id=row.id, error=str(exc)).debug(
                    "Vector drop on supersede skipped."
                )
            # Link only when the new source row exists (it is written as
            # chunks land; the first chunk's write precedes it, so link
            # best-effort and skip when absent).
            try:
                await self._manager.link(
                    row.id,
                    f"docsrc:{source_id}:{version}",
                    link_type="derived_from",
                    metadata={
                        "reason": "document_version_superseded",
                        "old_version": old_version,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - link is audit, not load-bearing
                logger.bind(memory_id=row.id, error=str(exc)).debug(
                    "Supersede link skipped (source row not yet written)."
                )
            archived += 1
        return archived
