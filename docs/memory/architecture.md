# Memory Subsystem — Finalized Architecture & Contracts (Phase 1)

> This document is the finalized, audited design for the Memory subsystem. It
> describes **what exists and is authoritative today**, the **stable contracts**
> other subsystems may depend on, and the **invariants** every write/retrieval
> path must uphold. It is a design contract, not a tutorial — developer usage
> lives in `docs/memory.md`. Phase ledger and resumable state live in
> `docs/memory/implementation-state.md`.
>
> Everything here was verified against the source at commit `b0a2537`
> (`src/aetheros/memory/**`) and `src/aetheros/config/settings.py`. Where a
> capability is not yet built, it is labelled **DEFERRED** and the failure mode
> is specified — nothing is described as working that is not.

## 1. Design principle (smallest compatible design)

The subsystem already exists, is tested (46 passing), and is wired into DI. The
Phase 1 decision is therefore **extend, do not replace**: preserve the public
interface names (`MemoryManager`, `MemoryProvider`, `EmbeddingProvider`,
`VectorIndex`, `KnowledgeGraph`, `AgentMemory`), the DI registration keys, and
the shared EventBus. No parallel abstraction is introduced.

Layering (dependency direction points downward; nothing below imports upward):

```
Consumers         tools.py · integration/agent_memory.py · provider.py(ABC port)
                        │
Facade            services/manager.MemoryManager   (the one object callers use)
                        │
Services          writer · retriever · scorer · validator · policy ·
                  consolidator · lifecycle · working_memory
                        │
Projections       vector/index.VectorIndex   graph/store.KnowledgeGraph
                        │
Authoritative     storage/repository.MemoryRepository → storage/database.SQLiteDatabase
store                   (memory_items + append-only migrations)
                        │
Primitives        domain/** (value objects)   embeddings/** (EmbeddingProvider ABC)
```

Authoritative-store rule: `memory_items` (and its satellite tables) in SQLite is
the single source of truth. The **vector index** and the **knowledge graph** are
*derived projections* that can be rebuilt from the authoritative store. They are
never the source of truth and never hold a record the authoritative store lacks.

## 2. Stable contracts

These are the interfaces other subsystems (Trading, Agents, CLI, tools) may
depend on. Signatures below are the current, verified shapes — they are frozen
for compatibility unless a change is explicitly justified and its impact
documented.

### 2.1 `MemoryManager` (facade — `services/manager.py`)

The high-level verb surface. Composes storage/vector/graph/services internally.

- `async initialize() -> None` — idempotent; connects the DB and brings schema
  current. Safe to call twice.
- `async shutdown() -> None` — idempotent; closes the connection.
- `async health_check() -> bool` — `True` iff the schema version is readable and
  the connection is live; swallows exceptions and returns `False` (never raises).
- `async remember(content, *, memory_type, veracity, source_type, origin,
  confidence, importance, tags, entities, data, metadata) -> Memory`
- `async remember_memory(memory: Memory) -> Memory` — honours retention policy;
  may **decline** (returns the unsaved `Memory` unchanged) when policy judges it
  trivial. Callers must not assume a returned object was persisted — see §3.3.
- `async get(memory_id) -> Memory | None`
- `async retrieve(text="", *, query=None, limit=None, memory_types, tags,
  entities, context, min_confidence, record_access=True) -> list[MemoryResult]`
- `async search(text, *, limit=5) -> list[MemoryResult]`
- `async update(memory_id, **changes) -> Memory` — bumps version, re-indexes.
- `async forget(memory_id, *, hard=False) -> bool` — soft by default (status →
  `DELETED`); `hard=True` removes the row and its vector irreversibly.
- `async link(from_id, to_id, *, link_type, weight, metadata) -> None`
- Typed helpers: episodes, preferences, failures, procedures, trading history.
- Accessors: `.working`, `.graph`, `.config`.

### 2.2 `MemoryProvider` (key/value + semantic ABC — `core/interfaces/memory_provider.py`)

The pre-existing Core port. `services/provider.SQLiteMemoryProvider` implements
it **over the same `MemoryManager` instance** registered in DI (not a second
connection). Interface-typed consumers resolve a working provider; everything
richer uses the manager directly. This is the Phase 1 decision on "two
interfaces, one implementation" — do not fork a parallel KV store.

### 2.3 `EmbeddingProvider` (embedding ABC — `embeddings/base.py`)

- `name: str` — **stable embedding identity**, recorded next to every stored
  vector (`memory_embeddings.model`). See §4.4.
- `dimension: int` — vector length this provider emits.
- `async embed(text) -> np.ndarray` — float32, length `dimension`, L2-normalised.
- `async embed_many(texts) -> list[np.ndarray]` — batching hook.
- `staticmethod normalize(vector) -> np.ndarray` — L2 so cosine == dot product.

Factory: `embeddings.build_embedding_provider(config) -> EmbeddingProvider`.
**Today it only ever returns `HashingEmbeddingProvider`** (deterministic,
offline, dependency-free). Unknown provider names fall back to hashing *loudly by
default*. Real providers are **DEFERRED** (§5).

### 2.4 `VectorIndex` (projection — `vector/index.py`)

Exact brute-force cosine over a float32 BLOB table, scoped to a candidate pool.
- `async index(memory_id, text)` / `index_many(items)`
- `async delete(memory_id)` / `async count() -> int`
- `async search(query_text, *, limit, candidate_ids=None) -> list[(id, score)]`

Not an ANN index by design (Rule 5: vectors are one signal over an already
SQL-filtered pool). The `memory_id`-scoped interface keeps an ANN swap open.

### 2.5 `KnowledgeGraph` (projection — `graph/store.py`)

Entity/relationship upsert with dedup and superseding edges, networkx traversal.
Derived from entity references on memories (`writer._reflect_entities`). Rebuild
behaviour and leak controls: §4.5, §4.6.

### 2.6 Retrieval result contract (`domain/query.py`)

- `MemoryQuery` — `text` + hard/soft filters (`memory_types`, `veracities`,
  `tags`, `entities`, `context`, `min_confidence`, `min_similarity`,
  `include_archived`, `expand_hops`, `candidate_limit`, `limit`).
- `MemoryResult` — `memory` + `explanation`; `.score` proxies the blend.
- `RetrievalExplanation` — ten named per-signal components on [0,1] plus
  `reasons: list[str]`. Satisfies the "explain why retrieved" requirement
  (CLAUDE.md §6/Rule 6). This structure is **stable** — tools and the CLI render
  its fields directly.

### 2.7 Bounded `MemoryContext` (agent adapter — `agents/memory_port.py`)

`integration/agent_memory.ManagerAgentMemory` implements the agent-package port:
- `async recall(goal, *, session_id, context) -> MemoryContext` — recall is
  **optional** and degrades safely: any failure returns
  `MemoryContext(query=..., error=...)` with no items rather than raising
  (contract: "optional recall may degrade safely").
- Recording translates an `AgentState` run into episodes/failures, bounded by
  `_MAX_FAILURE_RECORDS = 10` and `_RESULT_SUMMARY_CHARS = 200`.
- Context is **bounded** before it reaches the LLM: `agent_recall_limit`,
  `agent_recall_min_score`, `agent_recall_max_chars`.

Dependency direction is memory → agents (memory imports the agent port, never the
reverse) so there is no import cycle. `NullAgentMemory` is substituted when memory
is disabled, so the agent loop runs identically with memory off.

### 2.8 Trading adapter contract

Trading Intelligence does **not** import the memory package and keeps its own
`prediction_store` / `outcome_store` / `track_record` services. Memory stores the
*history* of trading output via `domain/trading.PredictionMemory` /
`PredictionOutcomeMemory` and the manager's typed helpers. The payloads are plain
dicts, keeping memory decoupled from trading's internal shapes. **Memory exposes
record/recall; it never computes a trading algorithm.**

## 3. Health / degraded / write-result states

### 3.1 Startup modes

- **Disabled** (`ENABLE_MEMORY=false`): `_bootstrap_memory` returns early;
  neither `MemoryManager` nor `MemoryProvider` is registered; `_build_agent_memory`
  returns `NullAgentMemory`; every memory tool returns
  `{"ok": False, "error": "MEMORY_DISABLED", "detail": ...}`. No crash, no fake data.
  **Phase 4** also hardened the manager verbs themselves against a config whose
  `enabled` is false (independent of bootstrap): `store()` returns
  `WriteResult.unavailable(...)`, `remember_memory()` is a no-op returning the
  unsaved object, and `retrieve()` degrades to `[]` (optional recall degrades
  safely). None of these pretend to persist.
- **Enabled, strict**: `initialize()` connects SQLite and runs migrations. A
  failure here is a hard startup failure (durable store is required). This is the
  intended behaviour today.
- **Enabled, degradable component**: the *embedding provider* degrades — an
  unknown/unavailable provider name falls back to the hashing embedder rather
  than failing startup. **Phase 1 decision:** this silent fallback is acceptable
  only while hashing is the single shipped backend. Once a real provider exists,
  the fallback for an *explicitly requested* real provider must become a
  **loud, policy-controlled** decision (strict vs degrade), because silently
  swapping a real semantic provider for hashing would violate the contract
  ("never silently replace an unavailable production provider with fake semantic
  retrieval"). See §5 and the Phase 2 plan.

### 3.2 Health

`health_check()` is a boolean liveness probe (schema readable + connection up).
**DEFERRED:** a richer degraded-state report (embedding identity in use, vector
count vs memory count drift, projection staleness) is not yet exposed; today
callers get only `bool`. Specified for a later phase.

### 3.3 Write results

Two write surfaces exist:
- **Legacy verb** `remember` / `remember_memory` returns the `Memory` object and
  raises on storage failure. A returned object is **not** proof of persistence —
  a policy decline returns the unsaved object unchanged; a disabled subsystem
  returns the object as a no-op. Unchanged for backward compatibility.
- **Phase 4** `MemoryManager.store(memory, *, idempotency_key=None)` returns a
  first-class `WriteResult{status, memory, memory_id, reason}` with five honest
  statuses (`services/results.py::WriteStatus`): `STORED` (durably persisted),
  `SKIPPED` (policy decline **or** idempotent hit — `.ok` is true, `.persisted`
  is false), `FAILED` (attempted, nothing persisted — the embedder/storage error
  is reported, not hidden), `UNAVAILABLE` (subsystem disabled or not
  initialized), `PENDING` (reserved for a future async-durable path). This closes
  the former "skipped vs stored" conflation. Idempotency is enforced by memory id
  and by an optional caller `idempotency_key` stamped into metadata, so a retried
  write is a safe `SKIPPED` no-op rather than a duplicate row.
- A validation failure (e.g. prediction-as-FACT) still raises on both surfaces;
  it never silently succeeds.

## 4. Invariants (enforced on every path)

### 4.1 Scope / authorization / context boundary

`MemoryQuery.context` matches indexed metadata columns (`session_id`, `task_id`,
`instrument_id`, …) in `repository.candidates()`, giving a task/context scope
filter at the SQL candidate stage — before vectors or graph see anything. This is
the structural basis for authorization. **PARTIAL / DEFERRED:** there is no
caller-identity principal, no redaction, and no sensitive-data exclusion policy
yet. The contract requires security foundations from the first write path; the
*scoping mechanism* exists, the *enforcement/redaction layer* does not. This is
the single most important gap and is called out as a finding (§6).

### 4.2 Provenance

Every memory carries a `MemorySource(source_type, origin, reference)`. Trading
records additionally preserve `model`, `model_version`, `data_version`,
`source_tier`. Provenance is mandatory and never dropped on write.

### 4.3 Prediction immutability & veracity

- `MemoryValidator` rejects storing a prediction/model/inference-sourced memory
  as `Veracity.FACT` (CLAUDE.md §15) — verified by test.
- `PredictionMemory` is write-once; its realised result is a **separate**
  `PredictionOutcomeMemory` that references it. The original call is never
  rewritten (CLAUDE.md §16, Rule 4).

### 4.4 Embedding identity

Each stored vector row records `dim` and `model` (= `provider.name`) alongside
the bytes (`memory_embeddings` table). **Phase 1 decision:** embedding identity =
`(provider.name, dimension)` today; it must expand to include model
identity/version, preprocessing, and distance/normalization policy when a real
provider lands. Equal dimension does **not** imply compatible embeddings. The
retriever must never blend vectors written under different identities. **DEFERRED:**
there is currently no guard that *rejects* a query embedded under identity B
against vectors stored under identity A — safe today because only one identity
("hashing-N") can exist, but it must be added with the first real provider (§5).

### 4.5 Current-observation precedence

Retrieved memory is historical context, never an override of currently verified
screen state, live market/API data, or environment observations. This is a
consumer-side contract: callers (agents, trading) must treat `MemoryResult`
content as untrusted historical context — not executable instructions, not a
fresh fact. The memory layer tags everything with `veracity` and `source` so the
consumer can apply precedence; it does not itself fetch live data.

### 4.6 Projection consistency & no-leak

- Soft-deleted (`status='deleted'`) rows are **excluded from the candidate pool**
  in `repository.candidates()`; since vector search is scoped to that pool, a
  soft-deleted memory cannot leak through semantic recall. Verified end-to-end
  (soft-forget → 0 results). Archived/stale are included only when
  `include_archived` is set.
- `hard` forget deletes the vector (`VectorIndex.delete`) and the row; the schema
  also cascades `memory_embeddings`/`memory_tags`/`memory_entities` on row delete
  (`ON DELETE CASCADE`).
- **DEFERRED / finding:** graph-expansion (`expand_hops`) and the knowledge graph
  do **not** yet re-check `status` on expanded neighbours, so a soft-deleted
  memory could in principle re-enter context via a graph edge from a live memory.
  Must be closed before graph expansion is trusted for sensitive data (§6).
- No distributed transaction spans SQLite + vector + graph. Writes are ordered
  (row → vector → graph → event). Cross-connection contention is bounded by
  `PRAGMA busy_timeout` (default 5000ms, `SQLiteDatabase(busy_timeout_ms=...)`);
  a consistent online backup is available via `SQLiteDatabase.backup()` (Phase 2).
- **Phase 4:** an explicit verify/repair path now exists.
  `MemoryManager.verify_projection()` compares the authoritative live set against
  the vector index and reports `missing` (live memory, no vector) and `orphan`
  (vector, no live backing memory) without mutating anything;
  `MemoryManager.repair_projection()` re-embeds missing vectors from the
  authoritative row (`MemoryWriter.reindex`) and deletes orphan vectors. Repair is
  idempotent (a second run reports zeros) and never fabricates a projection — it
  always reconstructs from the authoritative store. Verified end-to-end.
  **STILL DEFERRED:** a graph-side rebuild/repair (the knowledge graph has no
  equivalent reconciliation yet) and automatic repair-on-startup.

### 4.6a Concurrent edits (optimistic version guard)

`update(id, ...)` defaults to **last-writer-wins** (the historical behaviour).
Pass `expected_version=` for an **optimistic-concurrency guard**: the repository
issues a conditional `UPDATE ... WHERE id=? AND version=?` (`update_guarded`,
built on `SQLiteDatabase.execute_write` which returns the affected row count). If
0 rows match, the row changed since it was read and `MemoryConflictError`
(`MEMORY_CONFLICT`) is raised — the losing write never persists and the vector is
not touched. Callers re-read and reapply. This protects append-only trading
records and any read-modify-write caller from silently clobbering a concurrent
edit. Verified: matching version succeeds and bumps `version`; a stale version
raises and the winner's content survives.

### 4.7 Decay vs protected history

`MemoryLifecycle` only *demotes* status (never deletes); `PERMANENT`-scope
memories are always `ACTIVE` regardless of age/confidence. Ordinary decay cannot
destroy protected trading history. Authorized erasure (`hard` forget) is the only
destructive path and is user-initiated. **DEFERRED:** a documented retention /
authorized-erasure policy that accounts for derived stores and retention
obligations is not yet written — flagged for the security phase.

## 5. Embedding providers — hashing (default) + Ollama (real, Phase 5)

Two providers ship behind the one `EmbeddingProvider` ABC:

- `HashingEmbeddingProvider` (default): dependency-free, deterministic,
  offline-safe, lexical-grade semantics.
- `OllamaEmbeddingProvider` (`MEMORY_VECTOR_PROVIDER=ollama`): the first *real*
  semantic embedder, backed by a running Ollama daemon.

The ABC also carries `embed_batch` (order/cardinality contract), `validate_vector`
(dimension/non-empty/finite guard) and `normalize`.

Guarantees now enforced in code (previously specified-only):
1. A requested real provider that is **unavailable** fails startup under the
   strict default; it degrades to hashing only under the opt-in
   `MEMORY_EMBEDDING_FALLBACK=true`, and that degrade is logged **loudly**. A
   real provider is never silently swapped for hashing.
2. `name` encodes identity = `ollama:<model>:<dimension>`. The dimension is
   **probed from the live model** at `ensure_ready()` (no static table), then
   pinned; a later different-length response is a hard error.
3. Mixing identities in one index/query is refused: `VectorIndex` search filters
   stored vectors to the active `name` via the `memory_embeddings.model` column,
   so equal-dimension-but-different-model vectors are never blended. `MemoryManager`
   warns loudly at startup if the index holds foreign-identity vectors and
   exposes `reembed_all()` as the explicit, authorized migration.
4. A real-provider integration test (`-m real_embeddings`, opt-in via
   `AETHEROS_MEMORY_TEST_OLLAMA=1`) exercises real embeddings, real SQLite
   persistence, and the real cosine path. Fixtures do not substitute for it.

Any claim of "semantic retrieval" under the hashing provider still means
hashing-grade lexical/feature semantics; the Ollama provider delivers true model
embeddings.

## 6. Known gaps requiring later implementation (not Phase 1 work)

Each is a real gap in the audited code, with its contractual failure mode:

1. **Authorization / redaction / sensitive-data exclusion layer** (§4.1) — scope
   *mechanism* exists; *enforcement* does not. Highest priority; the contract
   wants it from the first write path.
2. **Projection rebuild/repair & drift reconciliation** (§4.6) — no path to
   rebuild vector/graph from the authoritative store or detect drift.
3. **Status re-check on graph expansion** (§4.6) — potential soft-delete leak via
   graph edges.
4. **Embedding-identity guard** (§4.4) — needed with the first real provider.
5. **Real embedding/vector provider + its integration test** (§5).
6. **First-class `WriteResult` / richer health report** (§3.2, §3.3) — so
   skipped/failed/stored are never conflated.
7. **Documented retention / authorized-erasure policy across derived stores** (§4.7).

These are recorded as findings only. None are implemented in Phase 1.

## 7. Validation performed (Phase 1)

- Imports of all memory modules + the Core ABC: **OK** (via `PYTHONPATH=src`).
- Config rejection: `MEMORY_EMBEDDING_DIM=8`, `MEMORY_SIMILARITY_THRESHOLD=2.0`,
  `MEMORY_RETRIEVAL_LIMIT=0`, `MEMORY_DECAY_HALFLIFE_DAYS=0` all **rejected** by
  pydantic validators.
- Alias precedence (§ config): `AETHEROS_MEMORY_*` wins over the bare name.
- DI assembly + end-to-end: build `MemoryManager` on a temp DB, `health_check()`
  True, write → vector count 1, retrieve → 1 hit with a populated explanation,
  soft-forget → 0 hits (no leak).
- Disabled-mode tool contract confirmed in `tools.py`.
- Acceptance suite: `tests/memory`, `tests/cli/test_memory_command.py`,
  `tests/agents/test_agent_memory_integration.py` → **46 passed, 0 failed**.
