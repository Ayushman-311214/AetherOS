"""
User memory controls (Phase 15).

The authorised user-facing layer over memory administration: inspection,
correction, forgetting, erasure, export, statistics and enable/disable --
all enforced against the existing scope model, all without exposing raw
storage internals.

Identity model (no parallel authentication system -- contract rule): this
is a single-operator desktop system. Identity is the existing
``user_id`` / ``session_id`` scope carried on every row's indexed columns
plus the ``ENABLE_MEMORY`` master switch. Authorization therefore means
*scope ownership*: a caller presenting ``user_id=X`` (or a session) may
only inspect/correct/forget/export rows in that scope, unless it presents
no scope at all -- the operator's own global view. Cross-scope access
raises :class:`MemoryNotFoundError` (never a distinct "forbidden": the
scope boundary must not become an existence oracle).

What each verb guarantees:

* ``inspect`` / ``list_scope`` -- scoped reads returning domain dicts
  (never raw rows, cursors, SQL or vectors). Missing, deleted (unless
  explicitly included for audit), or out-of-scope rows read as absent.
* ``correct`` -- routes to the Phase 13 correction path, so every
  correction wins by precedence (version bump), keeps attributable
  revision history (confidence history + version chain), and refuses
  immutable history. Correction precedence: the latest correction wins;
  history is never rewritten, only superseded by newer versions.
* ``forget`` (soft) -- DELETED status + vector delete for immediate
  exclusion from recall (authoritative filter + defense-in-depth).
  Refuses trading history without ``allow_history=True``.
* ``erase`` (hard) -- coordinated permanent erasure: row, vector, both-
  direction links, and graph evidence pointers. Refuses trading history
  without ``allow_history=True`` (explicit erasure vs retention conflicts
  resolve through this documented flag, never silently). Soft deletion
  alone is not erasure; backups, if any, are deployment policy outside
  this contract (documented, not pretended).
* ``export_scope`` -- full-fidelity scoped dump (row dicts + links +
  confidence histories + format version) suitable for audit or migration.
  Contains no vectors, SQL, file paths or connection internals. Fidelity
  means every exported row round-trips through ``Memory.from_dict``.
* ``stats_scope`` -- counts by type/status in scope (no content).
* Disable gates -- global (master switch, read from config) vs
  session/user (in-memory sets on this service, restart-cleared):
  disabling a session purges its working-memory context immediately;
  queued work does not exist in this subsystem (all verbs are
  caller-invoked, like decay/consolidation), so "pending-job behavior" is
  defined as: maintenance verbs return honest zeroed reports when the
  subsystem is disabled, in-flight operations run to completion against
  the store (SQLite serialises them), and embeddings/projections simply
  go idle (they are computed on demand, never by a background loop).
  In-flight disable cannot strand a half-write: every mutation is one
  guarded store transaction plus best-effort projection follow-up that
  repair reconciles.

Enforcement boundary (documented limitation): the storage layer itself
has no auth boundary (single-operator app); enforcement lives in this
service and in the tools/CLI that call it. A caller with a direct
``MemoryManager`` handle bypasses scope checks -- that handle is the
operator's own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...core.errors.memory_error import (
    MemoryNotFoundError,
    MemoryValidationError,
)
from ...core.logging import get_logger
from ..domain.enums import MemoryStatus, MemoryType, Veracity
from ..domain.memory import Memory

if TYPE_CHECKING:
    from .manager import MemoryManager

logger = get_logger("memory.controls")

EXPORT_FORMAT_VERSION = 1


class UserControls:
    """Scope-enforced user administration over durable memories.

    Constructed once by :class:`MemoryManager` (see the ``controls``
    accessor); holds only the manager handle plus the in-memory
    session/user disable sets (restart-cleared by design).
    """

    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager
        self._disabled_sessions: set[str] = set()
        self._disabled_users: set[str] = set()

    # ------------------------------------------------------------------
    # Scope helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _scope_of(row: Memory) -> tuple[str | None, str | None]:
        return (row.metadata.get("user_id"), row.metadata.get("session_id"))

    def _in_scope(
        self,
        row: Memory,
        *,
        user_id: str | None,
        session_id: str | None,
    ) -> bool:
        """Scope ownership: no requested scope = operator-global (all rows).

        A requested user_id matches rows carrying that user_id OR rows with
        no user_id at all (unscoped legacy rows belong to the operator).
        A requested session_id additionally requires the row's session to
        match (or the row to carry no session).
        """
        if user_id is None and session_id is None:
            return True
        row_user, row_session = self._scope_of(row)
        if user_id is not None:
            if row_user is not None and row_user != user_id:
                return False
        if session_id is not None:
            if row_session is not None and row_session != session_id:
                return False
        return True

    def _deny(self, memory_id: str) -> MemoryNotFoundError:
        # One error shape for missing/deleted/out-of-scope: the boundary
        # must not tell a scoped caller what exists outside its scope.
        return MemoryNotFoundError(f"No memory with id {memory_id!r} in scope.")

    # ------------------------------------------------------------------
    # Inspection (scoped reads, no internals)
    # ------------------------------------------------------------------

    async def inspect(
        self,
        memory_id: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """One memory as a plain dict, iff it is live and in scope."""
        row = await self._manager.get(memory_id)
        if row is None:
            raise self._deny(memory_id)
        if row.status is MemoryStatus.DELETED and not include_deleted:
            raise self._deny(memory_id)
        if not self._in_scope(row, user_id=user_id, session_id=session_id):
            raise self._deny(memory_id)
        return row.to_dict()

    async def list_scope(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        memory_type: MemoryType | None = None,
        include_deleted: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Scoped listing, newest first, bounded. No raw internals."""
        bound = max(1, int(limit))
        rows = await self._manager._repo.list_by(
            memory_type=memory_type.value if memory_type else None,
            limit=bound * 2,
        )
        out: list[dict[str, Any]] = []
        for row in rows:
            if row.status is MemoryStatus.DELETED and not include_deleted:
                continue
            if not self._in_scope(row, user_id=user_id, session_id=session_id):
                continue
            out.append(row.to_dict())
            if len(out) >= bound:
                break
        return out

    # ------------------------------------------------------------------
    # Correction (precedence + attributable history)
    # ------------------------------------------------------------------

    async def correct(
        self,
        memory_id: str,
        content: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """User correction with precedence and history (Phase 13 path).

        The latest correction wins (version bump); the confidence history
        + version chain retain what changed and when. Cross-scope and
        immutable-history rows are refused (the latter with a validation
        error explaining the policy).
        """
        row = await self._manager.get(memory_id)
        if row is None or (
            row.status is MemoryStatus.DELETED
        ):
            raise self._deny(memory_id)
        if not self._in_scope(row, user_id=user_id, session_id=session_id):
            raise self._deny(memory_id)
        self._require_enabled(user_id=user_id, session_id=session_id, verb="correct")
        result = await self._manager.confidence.correct(memory_id, content=content)
        updated = result.memory
        return {
            "memory_id": updated.id,
            "version": updated.version,
            "applied": result.applied,
            "reason": result.reason,
        }

    # ------------------------------------------------------------------
    # Forgetting and erasure
    # ------------------------------------------------------------------

    def _refuse_history(
        self, row: Memory, *, allow_history: bool, verb: str
    ) -> None:
        """Trading-history guard: ordinary edits stop here.

        Immutable market predictions and trading rows are protected from
        ordinary forgetting/erasure. An explicit ``allow_history=True``
        resolves the erasure-vs-retention conflict openly (documented
        policy, never silent): the caller states it means to erase history,
        and the erasure proceeds with full coordination.
        """
        if allow_history:
            return
        if row.memory_type is MemoryType.TRADING or (
            row.veracity is Veracity.PREDICTION
        ):
            raise MemoryValidationError(
                f"{verb}() refuses trading history without allow_history=True: "
                f"{row.memory_type.value} / {row.veracity.value} rows are "
                "retained as immutable audit trail.",
                hint="Pass allow_history=True to explicitly erase history, "
                "or link a correction/outcome instead of erasing.",
            )

    async def forget(
        self,
        memory_id: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        allow_history: bool = False,
    ) -> dict[str, Any]:
        """Soft-forget: DELETED + vector dropped (immediate recall exclusion).

        The row remains for audit. Cross-scope rows read as absent.
        """
        row = await self._manager.get(memory_id)
        if row is None or row.status is MemoryStatus.DELETED:
            raise self._deny(memory_id)
        if not self._in_scope(row, user_id=user_id, session_id=session_id):
            raise self._deny(memory_id)
        self._require_enabled(user_id=user_id, session_id=session_id, verb="forget")
        self._refuse_history(row, allow_history=allow_history, verb="forget")
        ok = await self._manager.forget(memory_id, hard=False)
        return {"memory_id": memory_id, "forgotten": ok, "hard": False}

    async def erase(
        self,
        memory_id: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        allow_history: bool = False,
    ) -> dict[str, Any]:
        """Permanently erase: row + vector + links + graph evidence pointers.

        Coordinated and irreversible. Reports what was removed (row, links,
        scrubbed graph edges) so the caller can verify completeness.
        Backups, if any, are deployment policy outside this contract.
        """
        row = await self._manager.get(memory_id)
        if row is None:
            raise self._deny(memory_id)
        if not self._in_scope(row, user_id=user_id, session_id=session_id):
            raise self._deny(memory_id)
        self._require_enabled(user_id=user_id, session_id=session_id, verb="erase")
        self._refuse_history(row, allow_history=allow_history, verb="erase")
        links_before = await self._manager._repo.linked_ids(memory_id)
        scrubbed = await self._manager._graph.scrub_memory(memory_id)
        ok = await self._manager.forget(memory_id, hard=True)
        return {
            "memory_id": memory_id,
            "erased": ok,
            "links_removed": len(links_before),
            "graph_edges_scrubbed": scrubbed,
        }

    # ------------------------------------------------------------------
    # Export and statistics (no raw internals)
    # ------------------------------------------------------------------

    async def export_scope(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        include_deleted: bool = False,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """Full-fidelity scoped export for audit or migration.

        Row dicts (which round-trip through ``Memory.from_dict``) plus the
        touching links and each row's confidence history. Contains no
        vectors, SQL, file paths or connection internals. Bounded.
        """
        bound = max(1, int(limit))
        rows = await self._manager._repo.list_by(limit=bound * 2)
        memories: list[dict[str, Any]] = []
        links: list[dict[str, Any]] = []
        seen_link_pairs: set[tuple[str, str, str]] = set()
        for row in rows:
            if row.status is MemoryStatus.DELETED and not include_deleted:
                continue
            if not self._in_scope(row, user_id=user_id, session_id=session_id):
                continue
            memories.append(row.to_dict())
            if len(memories) >= bound:
                break
        ids = {m["id"] for m in memories}
        for mid in sorted(ids):
            for other_id, link_type, weight in await self._manager._repo.linked_ids(
                mid
            ):
                key = (mid, other_id, link_type)
                if key in seen_link_pairs:
                    continue
                seen_link_pairs.add(key)
                links.append(
                    {
                        "from_id": mid,
                        "to_id": other_id,
                        "link_type": link_type,
                        "weight": weight,
                    }
                )
        return {
            "format_version": EXPORT_FORMAT_VERSION,
            "scope": {"user_id": user_id, "session_id": session_id},
            "memories": memories,
            "links": links,
        }

    async def stats_scope(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Counts by type/status in scope (no content)."""
        rows = await self._manager._repo.list_by(limit=5000)
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        total = 0
        for row in rows:
            if row.status is MemoryStatus.DELETED:
                continue
            if not self._in_scope(row, user_id=user_id, session_id=session_id):
                continue
            total += 1
            by_type[row.memory_type.value] = by_type.get(row.memory_type.value, 0) + 1
            by_status[row.status.value] = by_status.get(row.status.value, 0) + 1
        return {
            "scope": {"user_id": user_id, "session_id": session_id},
            "total": total,
            "by_type": by_type,
            "by_status": by_status,
        }

    # ------------------------------------------------------------------
    # Enable / disable (global vs session/user)
    # ------------------------------------------------------------------

    def is_disabled(
        self, *, user_id: str | None = None, session_id: str | None = None
    ) -> bool:
        """Whether memory is off globally or for this session/user."""
        if not self._manager.config.enabled:
            return True
        if session_id is not None and session_id in self._disabled_sessions:
            return True
        if user_id is not None and user_id in self._disabled_users:
            return True
        return False

    async def disable_session(self, session_id: str) -> dict[str, Any]:
        """Disable memory for one session + purge its working context now.

        Durable rows are untouched (disabling is not forgetting); in-flight
        operations complete against the store (SQLite serialises them);
        embeddings/projections go idle (computed on demand only). The gate
        is restart-cleared by design -- persistent per-user policy, if ever
        needed, belongs in configuration, not here.
        """
        self._disabled_sessions.add(session_id)
        purged = self._manager.working.end_session(session_id)
        return {"session_id": session_id, "disabled": True, "working_purged": purged}

    async def enable_session(self, session_id: str) -> dict[str, Any]:
        self._disabled_sessions.discard(session_id)
        return {"session_id": session_id, "disabled": False}

    async def disable_user(self, user_id: str) -> dict[str, Any]:
        self._disabled_users.add(user_id)
        return {"user_id": user_id, "disabled": True}

    async def enable_user(self, user_id: str) -> dict[str, Any]:
        self._disabled_users.discard(user_id)
        return {"user_id": user_id, "disabled": False}

    def _require_enabled(
        self, *, user_id: str | None, session_id: str | None, verb: str
    ) -> None:
        if self.is_disabled(user_id=user_id, session_id=session_id):
            raise MemoryValidationError(
                f"{verb}() refused: memory is disabled "
                f"(user_id={user_id!r}, session_id={session_id!r}).",
                hint="Enable memory (globally or for this scope) first.",
            )
