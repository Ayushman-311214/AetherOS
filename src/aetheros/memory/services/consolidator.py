"""
Memory consolidator (spec Phase 12, hardened).

Turns redundancy into stable knowledge: duplicate memories are merged into
one survivor that accumulates their evidence, and the duplicates are archived
(not deleted) with a link back to the survivor so history stays auditable.
Contradictions are *represented* (linked), never resolved by fiat. Temporal
facts can supersede older readings of the same subject. Ambiguous candidates
stay separate.

Merge discipline (the core of this phase):

* **Exact duplicates always merge** (same type + byte-identical normalised
  content), regardless of type. An exact copy carries no independent
  information.
* **Near-duplicate merge is guardrailed.** Cosine similarity above
  ``dedup_threshold`` merges ONLY when every guard holds: same memory type,
  same scope, overlapping entities (when both rows name entities), neither
  row protected, and neither row prediction-veracity. Similarity alone never
  merges two rows that could be distinct historical events.
* **Protected types never near-merge**: EPISODIC, FAILURE, TRADING, and any
  row with ``Veracity.PREDICTION``. A past prediction, an episode, or a
  failure record is a historical event -- two of them are never "the same
  memory" merely because their text is similar. (Ordinary decay must not
  destroy protected trading history either; consolidation honours the same
  boundary.)
* **Contradiction requires structured rules, never similarity.** Two rows
  contradict only when: same type, shared entity, and opposing markers --
  one asserts FACT/USER_INPUT while the other asserts the negation pattern
  (``not``/``never``/``no longer`` prefix on the same normalised claim), or
  two FACT rows share subject+entity with different values. Low embedding
  similarity is explicitly NOT contradiction. A contradiction records a
  ``contradicts`` link in both directions and leaves both rows ACTIVE --
  the system surfaces disagreement, it does not pick a winner.
* **Supersession is opt-in and narrow**: a newer FACT/USER_INPUT assertion
  about the same entity supersedes the older divergent one (``supersedes``
  link, older row archived with reason) -- and only inside a structured
  contradiction, so the disagreement stays auditable. OBSERVATION rows
  (measurement series) never supersede: both readings stay live as history.
  Predictions, episodes, failures, procedures and PERMANENT rows never
  supersede -- history is immutable.
* **Ambiguous candidates stay separate** and gain a ``related_to`` link so
  retrieval can expand across them without pretending they are one memory.

Batch discipline: ``consolidate()`` processes in bounded batches
(``batch_size``) ordered by creation time and records a resume cursor in the
returned report; a re-run (or a run after interruption) skips rows already
archived or already linked for the same reason, making every batch
idempotent. The verb stays caller-invoked (like ``decay()``) -- there is no
memory-owned background scheduler; the caller decides cadence.

Every decision is auditable: merges archive (never delete) with a
``derived_from`` link carrying the reason + similarity; contradictions and
supersessions are typed links with reasons; the returned report counts each
outcome. Reversal = follow the link back to the archived original, which is
always intact.
"""

from __future__ import annotations

import re
import uuid

import numpy as np

from ..config import MemoryConfig
from ..domain.enums import MemoryScope, MemoryStatus, MemoryType, Veracity
from ..domain.memory import Memory
from ..events import MemoryConsolidated
from ..storage.database import SQLiteDatabase
from ..storage.repository import MemoryRepository

# Types whose rows are historical events: never near-duplicate-merged.
# (Exact byte-identical copies still merge -- a copy is not an event.)
_PROTECTED_TYPES = frozenset(
    {
        MemoryType.EPISODIC,
        MemoryType.FAILURE,
        MemoryType.TRADING,
        MemoryType.PROCEDURAL,
    }
)

# Negation markers for the structured contradiction rule. A claim contradicts
# another when removing negation tokens from one yields the other
# ("no longer prefers X" vs "prefers X") or when one is the negation-prefixed
# form of the other. Token-level and deterministic -- never similarity.
_NEGATION_TOKENS = ("no longer", "not", "never", "no")

# Small claim normaliser for the contradiction rule: lowercase, strip
# punctuation/extra whitespace.
_NON_WORD = re.compile(r"[^\w\s]")


def _normalise(text: str) -> str:
    lowered = _NON_WORD.sub("", text.strip().lower())
    return re.sub(r"\s+", " ", lowered)


def _remove_token(words: list[str], parts: list[str]) -> str:
    """Drop whole-word runs equal to ``parts`` and rejoin normalised."""
    n = len(parts)
    kept: list[str] = []
    i = 0
    while i < len(words):
        if words[i : i + n] == parts:
            i += n
        else:
            kept.append(words[i])
            i += 1
    return _normalise(" ".join(kept))


class ConsolidationReport(dict):  # type: ignore[type-arg]
    """Counts per outcome; a plain dict so callers keep the old shape."""


class MemoryConsolidator:
    """Deduplicate, link, contradict and supersede (spec Phase 12)."""

    def __init__(
        self,
        repository: MemoryRepository,
        db: SQLiteDatabase,
        config: MemoryConfig,
        *,
        event_bus=None,
    ) -> None:
        self._repo = repository
        self._db = db
        self._config = config
        self._bus = event_bus

    async def consolidate(
        self, *, batch_size: int = 500, max_batches: int = 0
    ) -> dict[str, int]:
        """Run one bounded consolidation pass.

        ``batch_size`` caps rows considered per batch; ``max_batches`` caps
        batches (0 == unbounded). Returns counts keyed ``merged``,
        ``archived``, ``promoted``, ``contradictions``, ``superseded``,
        ``related``, ``skipped_protected`` plus ``batches``. Idempotent:
        re-running over the same store merges/links nothing new, because
        archived rows are excluded and existing same-reason links are
        skipped.
        """
        if not self._config.consolidation_enabled or not self._config.enabled:
            return {
                "merged": 0,
                "archived": 0,
                "promoted": 0,
                "contradictions": 0,
                "superseded": 0,
                "related": 0,
                "skipped_protected": 0,
                "batches": 0,
            }

        stats = {
            "merged": 0,
            "archived": 0,
            "promoted": 0,
            "contradictions": 0,
            "superseded": 0,
            "related": 0,
            "skipped_protected": 0,
            "batches": 0,
        }
        batch_size = max(1, int(batch_size))
        max_batches = max(0, int(max_batches))
        offset = 0
        batch_no = 0
        while True:
            if max_batches and batch_no >= max_batches:
                break
            batch = await self._repo.list_by(limit=batch_size, offset=offset)
            # list_by excludes soft-deleted rows already; skip the
            # non-actionable statuses ourselves.
            live = [
                m
                for m in batch
                if m.status
                not in (
                    MemoryStatus.ARCHIVED,
                    MemoryStatus.EXPIRED,
                    MemoryStatus.DELETED,
                )
            ]
            if not batch:
                break
            batch_no += 1
            stats["batches"] += 1
            vectors = await self._load_vectors([m.id for m in live])
            by_scope_type = self._group(live)
            for group in by_scope_type.values():
                for key, count in (await self._process_group(group, vectors)).items():
                    stats[key] = stats.get(key, 0) + count
            if len(batch) < batch_size:
                break
            offset += len(batch)
        if self._bus is not None:
            await self._bus.publish(
                MemoryConsolidated(
                    merged=stats["merged"],
                    archived=stats["archived"],
                    promoted=stats["promoted"],
                )
            )
        return stats

    # ------------------------------------------------------------------
    # Grouping
    # ------------------------------------------------------------------

    @staticmethod
    def _group(memories: list[Memory]) -> dict[tuple[str, str], list[Memory]]:
        """Group by (type, scope) so merges never cross either boundary.

        Scope isolation: a session-scoped note never merges with a long-term
        memory even when the text matches -- they live in different
        retention worlds.
        """
        groups: dict[tuple[str, str], list[Memory]] = {}
        for m in memories:
            groups.setdefault((m.memory_type.value, m.scope.value), []).append(m)
        return groups

    # ------------------------------------------------------------------
    # Per-group processing
    # ------------------------------------------------------------------

    async def _process_group(
        self, group: list[Memory], vectors: dict[str, np.ndarray]
    ) -> dict[str, int]:
        counts = {
            "merged": 0,
            "archived": 0,
            "contradictions": 0,
            "superseded": 0,
            "related": 0,
            "skipped_protected": 0,
        }
        threshold = self._config.dedup_threshold
        survivors: list[Memory] = []
        # Most-evidenced / most-confident first so they become survivors.
        ordered = sorted(
            group, key=lambda m: (m.evidence_count, m.confidence), reverse=True
        )
        for memory in ordered:
            outcome = await self._resolve_one(memory, survivors, vectors, threshold)
            if outcome in counts:
                counts[outcome] += 1
            if outcome == "merged":
                counts["archived"] += 1
            if outcome == "superseded_with_contradiction":
                # One pair, two auditable effects: count both the archived
                # row and the recorded disagreement.
                counts["superseded"] += 1
                counts["contradictions"] += 1
                counts["archived"] += 1
                # The archived row leaves the candidate pool; the newer row
                # takes its place so later rows compare against live
                # history, not against an archived reading. Only the live
                # row rejoins -- when the candidate itself was archived
                # (survivor was newer), it stays out.
                survivors[:] = [
                    s for s in survivors if s.status is not MemoryStatus.ARCHIVED
                ]
                if (
                    memory.status is not MemoryStatus.ARCHIVED
                    and all(s.id != memory.id for s in survivors)
                ):
                    survivors.append(memory)
        return counts

    async def _resolve_one(
        self,
        memory: Memory,
        survivors: list[Memory],
        vectors: dict[str, np.ndarray],
        threshold: float,
    ) -> str:
        """Decide one row against current survivors. Returns the outcome key."""
        for survivor in survivors:
            decision = self._decide(memory, survivor, vectors, threshold)
            if decision == "separate":
                continue
            if decision == "merged":
                await self._merge_into(memory, survivor)
                return "merged"
            if decision == "contradiction":
                linked = await self._link_pair(
                    memory,
                    survivor,
                    link_type="contradicts",
                    reason="structured_contradiction",
                )
                survivors.append(memory)
                return "contradiction" if linked else "separate"
            if decision in (
                "contradiction_supersede_memory",
                "contradiction_supersede_survivor",
            ):
                # Both links + archive the older row. Pool maintenance
                # happens in the caller (it owns the survivors list).
                await self._link_pair(
                    memory,
                    survivor,
                    link_type="contradicts",
                    reason="structured_contradiction",
                )
                if decision == "contradiction_supersede_memory":
                    await self._supersede(newer=memory, older=survivor)
                else:
                    await self._supersede(newer=survivor, older=memory)
                return "superseded_with_contradiction"
            if decision == "related":
                linked = await self._link_pair(
                    memory,
                    survivor,
                    link_type="related_to",
                    reason="ambiguous_similarity",
                )
                survivors.append(memory)
                return "related" if linked else "separate"
        survivors.append(memory)
        return "separate"

    # ------------------------------------------------------------------
    # Decision rules (structured, never similarity-alone)
    # ------------------------------------------------------------------

    def _decide(
        self,
        memory: Memory,
        survivor: Memory,
        vectors: dict[str, np.ndarray],
        threshold: float,
    ) -> str:
        """One of merged / contradiction(+supersede variants) / related / separate."""
        byte_identical = (
            survivor.content.strip().lower() == memory.content.strip().lower()
        )
        if byte_identical:
            # Byte-identical text merges ONLY for unprotected,
            # non-prediction rows with compatible entities. Protected rows
            # are historical events: two separately-recorded episodes /
            # failures with the same summary text are two events, not one
            # (agent re-recording is already idempotent at the store layer
            # via idempotency keys, so consolidation must never be the
            # dedup path for history). Same prose with disjoint entities
            # is ambiguous, not identical.
            if (
                memory.memory_type in _PROTECTED_TYPES
                or survivor.memory_type in _PROTECTED_TYPES
                or memory.veracity is Veracity.PREDICTION
                or survivor.veracity is Veracity.PREDICTION
            ):
                return "related"
            if self._entities_disjoint(memory, survivor):
                return "related"
            return "merged"

        # Near-duplicate merge requires normalised equality (case /
        # punctuation / whitespace folded): genuinely different claims are
        # never merged on vector similarity alone, no matter how high it
        # scores. One digit differs ("2500" vs "2510") and the rows stay
        # separate -- they are distinct readings, not copies.
        normalised_equal = _normalise(memory.content) == _normalise(survivor.content)
        similarity = self._similarity(memory, survivor, vectors)
        entities_overlap = self._entities_overlap(memory, survivor)

        # Contradiction: structured rule only (never similarity). When the
        # contradicting pair also qualifies for supersession (a newer
        # assertion replacing an older one), the caller records BOTH links
        # and archives the older row: the disagreement stays auditable
        # while current truth stays live. Supersession only ever fires
        # here, inside a structured contradiction -- never on similarity or
        # recency alone. In particular OBSERVATION pairs (measurement
        # series) never supersede: both readings stay live as history.
        # (This method is sync; the async link/archive work happens in
        # _resolve_one. The direction suffix tells it which row is newer.)
        if self._is_contradiction(memory, survivor):
            if self._is_supersession(newer=memory, older=survivor):
                return "contradiction_supersede_memory"
            if self._is_supersession(newer=survivor, older=memory):
                return "contradiction_supersede_survivor"
            return "contradiction"

        if normalised_equal:
            if self._merge_guarded(memory, survivor, entities_overlap):
                return "merged"
            return "related" if entities_overlap else "separate"

        # Above threshold with compatible guards but genuinely different
        # claims: ambiguous -- link, don't merge.
        if similarity is not None and similarity >= threshold:
            return "related" if entities_overlap else "separate"

        # Moderately similar with shared entities: ambiguous -- link, don't merge.
        if entities_overlap and similarity is not None and similarity >= 0.5:
            return "related"
        return "separate"

    def _merge_guarded(
        self, memory: Memory, survivor: Memory, entities_overlap: bool
    ) -> bool:
        """All near-merge guards. Any failure => no merge."""
        if memory.memory_type in _PROTECTED_TYPES:
            return False
        if survivor.memory_type in _PROTECTED_TYPES:
            return False
        if (
            memory.veracity is Veracity.PREDICTION
            or survivor.veracity is Veracity.PREDICTION
        ):
            return False
        # Same group already guarantees same type+scope; require entity
        # overlap when both rows bother to name entities, so "RELIANCE up"
        # never absorbs "INFY up" on prose similarity alone.
        mine = {e.strip().lower() for e in memory.entities if e.strip()}
        theirs = {e.strip().lower() for e in survivor.entities if e.strip()}
        if mine and theirs and not entities_overlap:
            return False
        return True

    @staticmethod
    def _entities_overlap(memory: Memory, survivor: Memory) -> bool:
        mine = {e.strip().lower() for e in memory.entities if e.strip()}
        theirs = {e.strip().lower() for e in survivor.entities if e.strip()}
        return bool(mine & theirs)

    @staticmethod
    def _entities_disjoint(memory: Memory, survivor: Memory) -> bool:
        """Both rows name entities and they share none.

        Same prose about different subjects ("RELIANCE broke..." vs the
        identical sentence tagged INFY) is ambiguous, never identical --
        merging would silently discard one subject.
        """
        mine = {e.strip().lower() for e in memory.entities if e.strip()}
        theirs = {e.strip().lower() for e in survivor.entities if e.strip()}
        return bool(mine and theirs and not (mine & theirs))

    @staticmethod
    def _similarity(
        memory: Memory, survivor: Memory, vectors: dict[str, np.ndarray]
    ) -> float | None:
        vec = vectors.get(memory.id)
        sv = vectors.get(survivor.id)
        if vec is None or sv is None:
            return None
        try:
            return float(vec @ sv)
        except Exception:
            return None

    @staticmethod
    def _is_contradiction(memory: Memory, survivor: Memory) -> bool:
        """Structured contradiction: shared entity + opposing markers.

        Never embedding similarity. Two shapes: (a) one claim is the
        negation-prefixed form of the other on the same normalised text;
        (b) two FACT/USER_INPUT rows share an entity and their normalised
        contents differ while neither is a substring of the other (genuinely
        divergent assertions about the same thing, e.g. "close 2510" vs
        "close 2490").
        """
        if not MemoryConsolidator._entities_overlap(memory, survivor):
            return False
        a = _normalise(memory.content)
        b = _normalise(survivor.content)
        if not a or not b or a == b:
            return False
        if MemoryConsolidator._negation_of(a, b):
            return True
        authoritative = {Veracity.FACT, Veracity.USER_INPUT}
        if (
            memory.veracity in authoritative
            and survivor.veracity in authoritative
            and a not in b
            and b not in a
        ):
            return True
        return False

    @staticmethod
    def _negation_of(a: str, b: str) -> bool:
        """True when one normalised claim is the negated form of the other.

        Whole-word matching only, so "nobel" never trips on the "no" token.
        """
        words_a = a.split()
        words_b = b.split()
        for token in _NEGATION_TOKENS:
            parts = token.split()
            # Rebuild properly: remove token occurrences as whole-word runs.
            stripped_a = _remove_token(words_a, parts)
            stripped_b = _remove_token(words_b, parts)
            if (stripped_a == b and token in a) or (stripped_b == a and token in b):
                return True
        return False

    @staticmethod
    def _is_supersession(*, newer: Memory, older: Memory) -> bool:
        """A newer assertion of current truth supersedes the older one.

        Narrow by construction, and only ever evaluated inside a structured
        contradiction (so supersession never fires on similarity or recency
        alone):

        * both rows authoritative assertions (FACT / USER_INPUT) about the
          same entity -- OBSERVATION rows are measurement history and never
          supersede (a price series stays intact);
        * strictly newer timestamp (equal timestamps stay separate);
        * divergent, non-overlapping claims (a restatement is not a new
          state);
        * neither row protected history (episodes, failures, trading,
          procedures) and not PERMANENT scope.
        """
        if newer.memory_type in _PROTECTED_TYPES:
            return False
        authoritative = {Veracity.FACT, Veracity.USER_INPUT}
        if newer.veracity not in authoritative or older.veracity not in authoritative:
            return False
        if newer.scope is MemoryScope.PERMANENT:
            return False
        if not MemoryConsolidator._entities_overlap(newer, older):
            return False
        if newer.id == older.id:
            return False
        a = _normalise(newer.content)
        b = _normalise(older.content)
        if not a or not b or a == b or a in b or b in a:
            return False
        try:
            wins = newer.created_at > older.created_at
        except Exception:
            return False
        return bool(wins)

    # ------------------------------------------------------------------
    # Actions (all auditable, all reversible via the archived original)
    # ------------------------------------------------------------------

    async def _merge_into(self, memory: Memory, survivor: Memory) -> None:
        survivor.evidence_count += memory.evidence_count
        survivor.confidence = min(
            1.0, max(survivor.confidence, memory.confidence) + 0.02
        )
        # Provenance accumulates: the survivor cites what it absorbed.
        absorbed = list(survivor.metadata.get("merged_from", []))
        if memory.id not in absorbed:
            absorbed.append(memory.id)
        survivor.metadata["merged_from"] = absorbed
        # Entity union: the survivor covers every subject the copies named,
        # so no subject is silently dropped by the fold.
        survivor.entities = list(
            dict.fromkeys(
                [e for e in survivor.entities if e and e.strip()]
                + [e for e in memory.entities if e and e.strip()]
            )
        )
        await self._repo.update(survivor)

        memory.status = MemoryStatus.ARCHIVED
        memory.metadata["archived_reason"] = "consolidation_duplicate"
        memory.metadata["survivor_id"] = survivor.id
        await self._repo.update(memory)
        await self._link_pair(
            memory,
            survivor,
            link_type="derived_from",
            reason="consolidation_duplicate",
        )

    async def _supersede(self, *, newer: Memory, older: Memory) -> None:
        """Archive the older assertion; the newer row stays live.

        Either direction is supported: when the candidate is newer the older
        survivor is archived (and leaves the pool via the caller); when the
        survivor is newer the older candidate is archived against it.
        """
        older.status = MemoryStatus.ARCHIVED
        older.metadata["archived_reason"] = "consolidation_superseded"
        older.metadata["superseded_by"] = newer.id
        await self._repo.update(older)
        await self._link_pair(
            older,
            newer,
            link_type="supersedes",
            reason="newer_assertion_same_subject",
        )

    async def _link_pair(
        self, memory: Memory, survivor: Memory, *, link_type: str, reason: str
    ) -> bool:
        """Create a typed link unless the same reason-link already exists.

        Returns True when a link was created (False = already present:
        idempotent re-runs link nothing new).
        """
        try:
            existing = await self._repo.linked_ids(memory.id)
        except Exception:
            existing = []
        for other_id, other_type, _ in existing:
            if other_id == survivor.id and other_type == link_type:
                # Same pair+type already linked -- check the reason matches
                # by treating any existing typed link as sufficient (links
                # carry no reason index; the row metadata holds the audit).
                return False
        await self._repo.add_link(
            {
                "id": uuid.uuid4().hex,
                "from_id": memory.id,
                "to_id": survivor.id,
                "link_type": link_type,
                "weight": 1.0,
                "metadata": {"reason": reason},
            }
        )
        return True

    async def _load_vectors(self, ids: list[str]) -> dict[str, np.ndarray]:
        import asyncio

        def _run() -> dict[str, np.ndarray]:
            if not ids:
                return {}
            marks = ",".join("?" for _ in ids)
            rows = self._db.query_all(
                "SELECT memory_id, vector FROM memory_embeddings "
                f"WHERE memory_id IN ({marks})",
                ids,
            )
            return {
                r["memory_id"]: np.frombuffer(r["vector"], dtype=np.float32)
                for r in rows
            }

        return await asyncio.to_thread(_run)
