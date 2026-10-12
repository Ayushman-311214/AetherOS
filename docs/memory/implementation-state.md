# Memory Subsystem — Implementation State

> Resumable state for the Memory subsystem engineering effort. Each phase MUST
> update this file to match the actual code. This is the single source of truth
> for "where are we and what is verified". Read `agent-contract.md` and the
> latest `phase-reports/phase-XX.md` alongside this file at the start of every
> phase.

Last updated: 2026-10-10 (Phase 17)
Current branch: `development`
Baseline revision at Phase 0: `b0a2537` ("Initialize memory system")

## Phase ledger

| Phase | Name | Status | Report |
|-------|------|--------|--------|
| 00 | Orientation, contract persistence, concurrent-agent audit | DONE | `phase-reports/phase-00.md` |
| 01 | Architecture, contracts, and configuration | DONE | `phase-reports/phase-01.md` |
| 02 | Persistent storage and migrations | DONE | `phase-reports/phase-02.md` |
| 03 | Memory domain models | DONE | `phase-reports/phase-03.md` |
| 04 | Write-path hardening (honest results, idempotency, projection repair) | DONE | `phase-reports/phase-04.md` |
| 05 | Real embedding provider (Ollama) + embedding-space identity | DONE | `phase-reports/phase-05.md` |
| 06 | Real vector index hardening (deletion-safety, batch search, bad-vector guard, bounded scan) | DONE | `phase-reports/phase-06.md` |
| 07 | Knowledge-graph hardening (bounded traversal, referential integrity, partial active-edge index) | DONE | `phase-reports/phase-07.md` |
| 08 | Explainable hybrid retrieval (filter isolation, budget bounds, provenance, safe degradation) | DONE | `phase-reports/phase-08.md` |
| 09 | Working (short-term) memory (session/task scope, TTL, freshness, evidence selection) | DONE | `phase-reports/phase-09.md` |
| 10 | Episodic memory foundation (explicit lifecycle, redaction, idempotency, restart) | DONE | `phase-reports/phase-10.md` |
| 11 | Failure and recovery memory (attempts, quarantine, alternatives, evidence contract) | DONE | `phase-reports/phase-11.md` |
| 12 | Consolidation and contradictions (guardrailed merge, links, supersession, batches) | DONE | `phase-reports/phase-12.md` |
| 13 | Confidence and evidence updates (bounded rules, history, refusals) | DONE | `phase-reports/phase-13.md` |
| 14 | Decay, retention and lifecycle (neglect chain, protection, batches, reactivation) | DONE | `phase-reports/phase-14.md` |
| 15 | User memory controls (scoped admin, erasure, export, disable gates) | DONE | `phase-reports/phase-15.md` |
| 16 | Trading memory integration (history adapter, as-of retrieval, honest ledger) | DONE | `phase-reports/phase-16.md` |
| 17 | Knowledge and document ingestion (bounded chunking, versions, citations, removal) | DONE | `phase-reports/phase-17.md` |

### Phase 7 deliverables

- `src/aetheros/memory/graph/store.py` (Memory-owned) — hardened the audited
  real knowledge graph (persisted entities/relationships; **not** replaced, no
  graph DB added, per the contract):
  - `TraversalBounds` dataclass: explicit `max_hops` / `max_fanout` /
    `max_results` / `time_limit_s`, validated.
  - Removed `_active_graph` (whole-graph networkx materialisation per call) and
    the `networkx` import. `find_related_entities` / `find_path` now run a
    cycle-safe, per-hop SQL BFS (`_bounded_bfs_sync` / `_active_neighbor_ids_sync`)
    that filters active edges at every hop and never loads the whole graph. Both
    keep their old signatures; new `relation` / `bounds` params are optional.
  - `add_relationship` invalid-reference guard: endpoints must exist, else
    `MemoryValidationError`.
- `src/aetheros/memory/graph/__init__.py` — exports `TraversalBounds`.
- `src/aetheros/memory/storage/schema.py` — migration **version 2**: partial
  indexes `ix_rel_active_source` / `ix_rel_active_target` on
  `relationships(source_id|target_id) WHERE valid_to IS NULL`. Additive,
  idempotent, no data rewrite. EXPLAIN QUERY PLAN confirms both are selected for
  the per-hop neighbour queries.
- `tests/memory/test_knowledge_graph.py` — 18 tests (dedup, direction,
  supersede/no-leak, invalid-ref guard, hop/fanout/result/time bounds, cycles,
  relation filter, persistence, DB isolation, bounds validation).
- `tests/memory/test_storage_migrations.py` — fidelity fix: the simulated "v1"
  DB now also creates the `relationships` table (which a real v1 DB has and
  migration 2 indexes).
- `docs/memory.md` — Graph layer + diagram updated (networkx → bounded SQL BFS).
- Verification: `pytest tests/memory` → 143 passed, 3 skipped (exit 0).
  Pre-existing `ruff` findings in `store.py` (`I001`, `F401 utcnow`) evidenced at
  HEAD, left untouched. `mypy` not installed in this environment.

### Phase 6 deliverables

- `src/aetheros/memory/vector/index.py` (Memory-owned) — hardened the audited
  real vector store (SQLite float32 BLOBs + exact numpy cosine; **not** replaced,
  per the contract's replace-only-when-necessary rule — no new ANN dependency):
  - `search(..., exclude_deleted=True)`: the whole-index (`candidate_ids=None`)
    path now JOINs `memory_items` and excludes `status='deleted'`, closing the
    direct-caller deletion-leak. The `candidate_ids` path (the retriever's normal
    route) is unchanged — it was already status-filtered upstream.
  - `search_many(...)`: real batch search (`M @ Qᵀ`, matrix loaded once).
  - `_store`: `EmbeddingProvider.validate_vector` guard before persistence
    (rejects wrong-dim / empty / NaN/inf; adopts the vector's length when a lazy
    provider's `dimension` is un-probed).
  - Whole-index scan bounded by `DEFAULT_MAX_SCAN = 50_000` (constructor
    `max_scan=`), `created_at DESC`, logged warning on truncation.
- `tests/memory/test_vector_index.py` (new) — 17 backend tests (real SQLite +
  deterministic hashing backend: CRUD, upsert, on-disk persistence across reopen,
  candidate filtering, bounded top-k, soft-delete no-leak, embedding-identity
  isolation, bad-vector rejection, batch==single, projection repair) + 1 opt-in
  real-Ollama relative-retrieval test (skipped without a daemon).
- No schema/migration change. No shared/Trading-owned file touched.

Key audit finding (existing behaviour, documented not changed): `repo.update`'s
`INSERT OR REPLACE` + the embedding FK `ON DELETE CASCADE` means a normal
`forget(hard=False)` already drops the vector; the new JOIN guard is
defense-in-depth for any path that flips `status` without replacing the row.

Evidence: `python -m pytest tests/memory -o addopts=""` → 125 passed, 3 skipped
(opt-in real tests). `ruff` clean on the new test; the 2 `index.py` ruff findings
are pre-existing (verified against `HEAD`). See `phase-reports/phase-06.md`.
PENDING: the opt-in real-vector integration test still needs a run against a live
Ollama daemon to satisfy Phase 6's real-provider acceptance.

### Phase 5 deliverables

- `src/aetheros/memory/embeddings/ollama.py` (new, Memory-owned) —
  `OllamaEmbeddingProvider`: the first *real* semantic embedder, behind the
  existing `EmbeddingProvider` ABC. Injected `httpx.AsyncClient`, bounded
  timeouts, opt-in bounded retries with exponential backoff on transient
  failures only (mirrors the trading Yahoo provider's HTTP shape). `ensure_ready()`
  proves daemon reachability + model presence + real embedding capability and
  **probes** the true dimension from the live model (no static dimension table).
  `name` encodes identity = `ollama:<model>:<dim>`. Errors never leak the prompt.
- `src/aetheros/memory/embeddings/base.py` — added `embed_batch` (order/cardinality
  contract), kept `embed_many` as a back-compat alias, and a static
  `validate_vector` guard (dimension / non-empty / finite). Additive.
- `src/aetheros/memory/embeddings/__init__.py` — factory now wires `ollama` and
  enforces the honesty policy: an explicitly-requested real provider is **never**
  silently swapped for hashing; unknown provider is a config error unless
  `MEMORY_EMBEDDING_FALLBACK=true` opts into a **loud** degrade.
- `src/aetheros/memory/vector/index.py` — search now filters stored vectors to
  the **active embedding identity** (`model` column), so two models that share a
  dimension can never be blended in one cosine query (contract §4.4). Added
  `identities()` inventory.
- `src/aetheros/memory/services/manager.py` — `initialize()` calls
  `ensure_ready()` under the strict/degrade policy and warns loudly if the index
  holds foreign-identity vectors; added `embedding_identities()` and `reembed_all()`
  (the explicit, authorized migration for an incompatible embedding-space change).
  `stats()` made dimension-safe for a not-yet-probed real provider.
- `src/aetheros/memory/config.py` + `src/aetheros/config/settings.py` — two
  additive knobs: `MEMORY_EMBEDDING_BASE_URL`, `MEMORY_EMBEDDING_FALLBACK`.
- `tests/memory/test_embedding_provider.py` (new) — 20 boundary unit tests
  (httpx.MockTransport labelled external-boundary mock) + 2 opt-in real-provider
  integration tests (`-m real_embeddings`, auto-skip unless
  `AETHEROS_MEMORY_TEST_OLLAMA=1`).
- `pyproject.toml` (shared, root) — registered the `real_embeddings` marker only.

### Phase 5 key decisions

- **No schema/migration change.** The `memory_embeddings.model` column (Phase 2)
  already persists per-vector identity; identity enforcement is a WHERE-clause on
  it. Smallest coherent change.
- **Dimension is probed, not assumed.** There is no reliable static table of
  Ollama embedding dimensions, and equal dimensions do not imply compatible
  spaces. `ensure_ready()` learns the real dimension and pins it; a later
  different-length response is a hard error.
- **Strict-by-default, loud-degrade opt-in.** A requested real provider that is
  unavailable fails startup rather than silently serving lexical hashing. Only
  `MEMORY_EMBEDDING_FALLBACK=true` degrades, and it is logged as a warning.
- **Real-provider acceptance evidence captured.** With user authorization, an
  already-running Ollama daemon (model `llama3:latest`, dim 4096) was used — no
  model download. Both integration tests passed against real embeddings, real
  SQLite persistence, and the real cosine path (see phase report for output).

### Phase 4 deliverables

See `phase-reports/phase-04.md`: honest `WriteResult` statuses, idempotency key,
optional optimistic-concurrency guard, and vector-projection verify/repair.

### Phase 3 deliverables

- Audit result: **all requested domain types already existed** (built pre-Phase 0)
  under adapted names — `Memory` (= MemoryRecord), `Episode`/`ActionRecord`/
  `Outcome` (= EpisodicMemory), `Entity`/`Relationship` (= SemanticMemory),
  `Procedure`/`ProcedureStep` (= ProceduralMemory), `Preference` (= PreferenceMemory),
  `FailureRecord` (= Failure + Recovery), `PredictionMemory` + `PredictionOutcomeMemory`
  (= TradingMemory, immutable prediction + append-only outcome), `MemoryLink` +
  `Relationship` (= MemoryRelationship), `MemorySource` + `Memory.metadata`
  (= MemoryMetadata/provenance). Phase 3 = **complete/harden**, not build-new.
- `src/aetheros/memory/domain/content_policy.py` (new, Memory-owned) — safe
  content limits (`MAX_CONTENT_CHARS` 20k, `MAX_PAYLOAD_BYTES` 256 KiB) and a
  conservative secret scanner/redactor with `ContentPolicy`/`SecretAction`
  (REDACT default / REJECT / ALLOW). Pure, side-effect-free domain functions.
- `src/aetheros/memory/services/validator.py` — wired the content-safety
  foundation into the single write-path gate: size limits enforced; secrets
  redacted-in-place (recording `metadata["redacted_secret_kinds"]`) or rejected.
  Existing prediction-not-FACT rule preserved. `MemoryValidator(policy=...)`
  gains an optional ctor arg (default `ContentPolicy()`), back-compatible.
- `src/aetheros/memory/domain/__init__.py` — export the content-policy symbols.
- `tests/memory/test_domain_models.py` (new) — 28 tests: lossless round-trips,
  malformed/unknown-field/legacy-shape input, boundary confidence, tz-aware +
  naive-coercion timestamps, prediction/outcome separation + immutability,
  evidence-gated procedure confidence, preference veracity, failure/recovery,
  content limits + secret redact/reject/allow, and the repository-field contract.

### Phase 3 key decisions

- Did **not** rename existing types to the contract's literal names — that would
  break every caller, the repository serialisation, and persisted rows for no
  behavioural gain. Mapping recorded above instead (contract: "Adapt names to
  existing conventions; do not create duplicate domain types").
- Secret handling is a **foundation, not a DLP guarantee**: high-precision
  patterns tuned against false-positives on trading prose; the later security
  phase extends it. Default = REDACT so a durable write still succeeds while the
  credential never lands in SQLite/vector/events; REJECT available for strict
  callers. This satisfies "security foundations from the first write path".
- Content/payload limits live in the domain (`ContentPolicy`) and are enforced in
  the validator, not in `settings.py` — avoids editing the shared, Trading-mid-edit
  config file (same rationale as Phase 2's `busy_timeout`).
- No schema/migration change; `Memory.to_dict()` keys unchanged, so the
  repository round-trip and all persisted rows stay compatible (asserted by test).

Phases 0–1 were non-mutating. Phase 2 made the first source change:
additive hardening of the SQLite store (bounded busy_timeout + native backup)
plus the full persistence/migration acceptance test matrix.

### Phase 2 deliverables

- `src/aetheros/memory/storage/database.py` — `busy_timeout_ms` ctor arg +
  `PRAGMA busy_timeout`; `SQLiteDatabase.backup()` (native online backup).
- `tests/memory/test_storage_migrations.py` — 15 tests (fresh install, upgrade,
  rollback, constraints/cascade, idempotent re-migration, concurrent writers,
  close/reopen + restart persistence, records-survive-migration, backup/recovery).
- `docs/memory.md` — Backup & recovery + irreversible-operation documentation.

### Phase 2 key decisions

- No schema migration added; `LATEST_VERSION` unchanged (v1 already covers the
  domain). Any future field goes in a new append-only migration entry.
- `busy_timeout` default 5000ms via constructor arg, **not** a Settings field —
  avoided editing shared `settings.py` (concurrent Trading edits in flight).
- Backup = SQLite native online backup (WAL-safe); recovery is manual
  (stop → replace file + drop `-wal`/`-shm` → restart). Hard delete is the only
  irreversible data path.
- Acceptance: 61 memory tests pass (46 prior + 15 new); every test uses
  `tmp_path`/`:memory:`, never a real user DB.
- Still open: finding #1 (authorization/redaction) and projection
  rebuild/repair are the top candidates for the next phase.

### Phase 1 deliverables (all under `docs/memory/`)

- `architecture.md` — finalized contracts, invariants, health/write-result
  states, DEFERRED features + failure modes, findings #1–#7.
- `configuration.md` — canonical config, alias precedence (`AETHEROS_MEMORY_*`
  wins), `EMBEDDING_*`/`MEMORY_EMBEDDING_*` reconciliation.
- `phase-2-migration-plan.md` — Phase 2 scope/acceptance.

### Phase 1 key decisions

- Smallest compatible design = **extend, not replace**; all public interface
  names and DI keys preserved.
- **No bare `EMBEDDING_*` convention exists** in the codebase; canonical names
  are `MEMORY_EMBEDDING_MODEL`/`MEMORY_EMBEDDING_DIM` (+ `AETHEROS_` aliases,
  which win). No new ambiguous global introduced; nothing to deprecate.
- Authoritative store = SQLite `memory_items`; vector index + knowledge graph are
  rebuildable projections, never the source of truth.
- Embedding identity = `(provider.name, dim)` today; must expand with the first
  real provider. Silent hashing fallback acceptable only while hashing is the
  sole backend.
- Validated: imports, config rejection (4/4), alias precedence, DI assembly +
  end-to-end write/retrieve/soft-forget, disabled mode. Acceptance suite 46 green.
- Top finding: authorization/redaction/sensitive-exclusion layer not built
  (mechanism exists, enforcement does not) → proposed Phase 3. Phase 2 = projection
  consistency/rebuild + graph soft-delete-leak fix.

## Audited existing architecture (do not reinvent)

The Memory subsystem already exists and is tested. It was built prior to this
engineering effort (commit `a356bfc` and earlier; `b0a2537` initialized the
on-disk memory DB). Treat it as the system to EXTEND, not replace.

Developer documentation already exists and is current at `docs/memory.md` — DO
NOT overwrite it. The contract's control files live under `docs/memory/` (this
directory), which coexists with the `docs/memory.md` file.

### Module map (`src/aetheros/memory/`, verified present 2026-10-07)

- `config.py` — `MemoryConfig` (resolved from `config/settings.py`).
- `_clock.py` — clock abstraction.
- `events.py` — memory-domain events (`MemoryStored`, …) built on the SHARED
  `Event` base from `runtime/events/events.py`. Reuses the shared EventBus; no
  second bus. (verified: header + import of `..runtime.events.events.Event`.)
- `domain/` — storage-free value objects: `enums` (`MemoryType`, `Veracity`,
  `MemoryImportance`), `memory.Memory`, `episode.Episode`, `semantic`
  (`Entity`/`Relationship`), `procedure.Procedure`, `preference.Preference`,
  `trading` (`PredictionMemory`/outcome, `FailureRecord`), `query`
  (`MemoryQuery`/`MemoryResult`).
- `storage/` — `database.SQLiteDatabase` (migrations, WAL, thread-safe single
  conn), `repository.MemoryRepository` (typed CRUD + structured candidate gen),
  `schema.py` (DDL / ordered append-only migrations).
- `embeddings/` — `base.EmbeddingProvider` ABC + `hashing` deterministic
  offline provider. Real providers are DEFERRED (plug in behind the ABC).
- `vector/index.py` — `VectorIndex`, SQLite float32 vectors, exact cosine via
  numpy over a candidate pool.
- `graph/store.py` — `KnowledgeGraph` (dedup entities, superseding
  relationships, networkx traversal).
- `services/` — `manager.MemoryManager` (façade), `writer.MemoryWriter`,
  `retriever.MemoryRetriever` (hybrid, explainable; `RetrievalExplanation`),
  `scorer.MemoryScorer` (8 signals), `validator.MemoryValidator` (rejects
  prediction-as-FACT per CLAUDE.md §15), `consolidator.MemoryConsolidator`,
  `lifecycle.MemoryLifecycle` (decay), `policy.MemoryPolicyEngine` (scope/TTL),
  `working_memory.WorkingMemory`, `provider.SQLiteMemoryProvider` (implements
  the core `memory_provider` ABC).
- `integration/agent_memory.py` — agent-facing adapter.
- `tools.py` — ToolRegistry tools: `remember`, `recall`, `get_memory`,
  `update_memory`, `forget_memory`, `list_memories`, `find_related_memory`,
  `memory_status`. Return `{"ok": False, "error": "MEMORY_DISABLED"}` when off.

### Wiring

- Bootstrap: `bootstrap/bootstrapper.py` `_bootstrap_memory` builds + initializes
  the manager and registers it in DI; `_shutdown_memory` closes it;
  `_bootstrap_tools` imports memory tools when enabled. (NOTE: `bootstrapper.py`
  is currently modified in the working tree by the concurrent agent — see
  "Concurrent-agent audit".)
- Config toggle: memory is OFF by default (`ENABLE_MEMORY=false`), resolved into
  `MemoryConfig` from `config/settings.py`.
- Shared EventBus: `src/aetheros/runtime/events/event_bus.py` (DO NOT create a
  second bus).
- CLI: `memory [stats|search|show|list|forget]` in `cli/commands.py`.

### Tests (Memory-owned, verified green at Phase 0)

- `tests/memory/conftest.py`, `tests/memory/test_memory_services.py`,
  `tests/memory/test_memory_storage.py`, `tests/memory/test_memory_tools.py`
- `tests/cli/test_memory_command.py`
- `tests/agents/test_agent_memory_integration.py`

Baseline command and result (2026-10-07):

    python -m pytest tests/memory tests/cli/test_memory_command.py \
      tests/agents/test_agent_memory_integration.py
    => 46 passed, 1 warning (DeprecationWarning: datetime.utcnow in a test), exit 0

## Deferred / known-not-built (from prior status, re-verify before claiming)

- Real embedding providers (only `HashingEmbeddingProvider` exists today).
- Automatic procedure learning from episodes.
- Background consolidation/decay scheduler.
- Automatic agent/planner memory wiring beyond the current adapter (gated by a
  `MEMORY_AUTO_REMEMBER`-style flag per prior notes — re-verify the exact name).
- Document/knowledge ingestion.
- 100k-scale performance validation.

## Concurrent-agent audit (2026-10-07)

A second agent is actively developing Trading Intelligence. At Phase 0 the
working tree is dirty but NO memory source files are modified or added. All dirty
`src/` changes are under `src/aetheros/trading/**` (Trading-owned) plus two
shared/Core files touched by that agent:

- `src/aetheros/bootstrap/bootstrapper.py` — SHARED. Contains `_bootstrap_memory`.
  Currently modified by the Trading agent. Any Memory change here must re-read
  the live file and its diff first, and make the smallest compatible edit.
- `src/aetheros/config/settings.py` — SHARED. Holds memory config fields.
  Currently modified by the Trading agent. Same caution.
- `src/aetheros/data/memory.db` — a real on-disk DB file, modified in tree. DO
  NOT run mutating tests/migrations against it; tests use isolated temp DBs.

Everything else dirty is Trading-owned (`trading/domain`, `trading/services`,
`trading/providers`, `trading/indicators`, `trading/tools.py`, new `trading/*`
subpackages) or tooling/graph output (`graphify-out/**`, `logs/**`,
`pyproject.toml`, `run-claude.sh`). None are Memory-owned.

### Ownership classification for Memory work going forward

- Memory-owned (safe to extend): `src/aetheros/memory/**`, `tests/memory/**`,
  `tests/cli/test_memory_command.py`, `tests/agents/test_agent_memory_integration.py`,
  `docs/memory.md`, `docs/memory/**`.
- Shared (smallest-compatible edits only, re-read diff first):
  `bootstrap/bootstrapper.py`, `config/settings.py`,
  `runtime/events/event_bus.py`, `runtime/events/events.py`, DI container,
  `core/interfaces/memory_provider.py`.
- Trading-owned (do not touch without coordination): `src/aetheros/trading/**`.
- Other agents' territory: `agents/**` (coordinate), `planner/**`, `desktop/**`,
  `vision/**`, `core/**` (edit only additively, with care).

## Key decisions

- Phase 0 is non-mutating: contract + state + audit + baseline only.
- `docs/memory.md` is preserved as-is (current developer docs). Contract control
  files placed under `docs/memory/` to avoid any conflict. No path remapping was
  necessary — the `docs/memory/` directory did not previously exist.

## Test commands (discovered, actual)

- Memory suite: `python -m pytest tests/memory tests/cli/test_memory_command.py tests/agents/test_agent_memory_integration.py`
- (Full suite has 22 pre-existing environmental failures per prior baseline —
  re-establish evidence before relying on that claim in any phase.)

## Open risks

- Two shared files (`bootstrapper.py`, `settings.py`) are mid-edit by the
  Trading agent. A future Memory phase that must touch them risks a merge
  conflict; re-read before editing and prefer additive changes.
- `datetime.utcnow()` deprecation warning in `test_memory_services.py` — cosmetic
  today, worth fixing in a maintenance pass (not a Phase 0 action).

## Next-phase handoff

Phase 17 (knowledge and document ingestion) is DONE (suite green: 18 new
tests, memory + CLI suite 327 passed / 4 skipped). No Trading-owned file
touched. New `DocumentIngestion` (`memory/services/ingestion.py`), exposed
as `manager.documents`, plus `DocumentSource` / `DocumentChunk` /
`checksum_text` in `domain/document.py`:
- **Stdlib-only by evidence**: audited first — no parsers/ingestion code
  and no PDF/DOCX/HTML libraries exist in the repo, so supported formats
  are txt/md/json/jsonl/csv; pdf/docx/html/remote are explicitly rejected
  (never invented). `verify_ingestion_contract()` is the honest ledger.
- **Content-addressed versions**: version IS the sha256; same bytes =
  idempotent no-op, changed bytes = new version (old chunks guarded-archive
  + inline vector drop + `derived_from` link; registry rows kept as audit).
  Corrections are new versions — no in-place chunk edit path.
- **Honest progress**: `_index` advances the cursor only for STORED chunks
  (idempotent SKIPPED replays); FAILED raises `MemoryStorageError`;
  UNAVAILABLE/policy SKIPPED stops with the partial row recording the
  cursor (re-ingest resumes). `_ensure_enabled` gates ingest/remove so
  disabled mode can never half-archive.
- **Citable + untrusted**: every chunk UNVERIFIED with source/version/ref
  metadata (md section / json key / jsonl line / csv row); malicious prose
  persists as inert data; secrets redacted pre-persistence *and*
  pre-embedding by the write-path validator.
- **Removal**: `remove_source` archives every version (chunks + rows,
  counts receipt); nothing recallable, everything auditable by direct read.
Key identifiers: `DocumentIngestion`, `manager.documents`,
`DocumentSource` / `DocumentChunk`, `checksum_text`, `SUPPORTED_FORMATS`,
`doc:{source}:{version}:{index}` / `docsrc:{source}:{version}` ids.
Evidence: `tests/memory/test_ingestion.py` — **18 passed**; memory +
CLI suite **327 passed, 4 skipped** (exit 0). Ruff clean except
pre-existing UP017 (at HEAD, untouched) + pre-existing manager.py format
drift in regions not touched. `mypy` unavailable in env. See
`phase-reports/phase-17.md`.
Test-caught issues fixed in-phase: 3 test bugs (off-by-one cursor count,
valid-CSV negative case, sync vector probe via await); then 2 F841 + 2
B017 (now assert `MemoryStorageError`) by hand. Implementation defects
caught during drafting: dead `_absent_ok` link block, missing version bump
in `_archive_row`, double-write supersede stamp, missing disabled gate.
Known observation: `docsrc:*` registry rows are ACTIVE and surface in
retrieval (metadata, not a leak) — noted for Phase 22.

### Phase 16 handoff (previous)

Phase 16 (trading memory integration) is DONE (suite green: 12 new tests,
memory + CLI suite 309 passed / 4 skipped). No Trading-owned file touched
(34-file Trading working tree left alone). New `TradingHistoryAdapter`
(`memory/services/trading_history.py`), exposed as
`manager.trading_history`, plus 5 history records in `domain/trading.py`:
- **Decoupled seam**: plain dicts in via `from_*` constructors (tolerant,
  verbatim, never recompute); no trading imports anywhere in memory.
- **Time discipline**: event/ingestion/evaluation times separated;
  `history_as_of` filters on event_time (future + undated rows excluded —
  no leakage into historical tests).
- **Immutability**: predictions store once (caller content-digest ids make
  re-ingest a no-op); outcomes append + link `has_outcome` both arrival
  orders (backfill); reasoning summaries cite + link sources.
- **Scope isolation** by instrument_id (+ timeframe/venue).
- **Honest ledger**: `verify_consumer_contract()` states verified-live
  vs representative-mapping shapes explicitly.
Key identifiers: `TradingHistoryAdapter`, `manager.trading_history`,
`MarketRegimeMemory` / `AnalysisSnapshotMemory` /
`StrategyObservationMemory` / `CalibrationRecordMemory` /
`ReasoningSummaryMemory`, `history_as_of`.
Evidence: `tests/memory/test_trading_history.py` — **12 passed**; memory +
CLI suite **309 passed, 4 skipped** (exit 0). Ruff clean on changed files.
`mypy` unavailable in env. See `phase-reports/phase-16.md`.
Test-caught issues fixed in-phase: disabled-test setup (initialize before
DB reads), 2 unused locals.

### Phase 15 handoff (previous)

Phase 15 (user memory controls) is DONE (suite green: 17 new tests, memory
suite + CLI command tests 297 passed / 4 skipped). New `UserControls`
(`memory/services/controls.py`), exposed as `manager.controls`:
- **Scope-enforced admin**: `inspect` / `list_scope` / `correct` /
  `forget` (soft) / `erase` (hard) / `export_scope` / `stats_scope` /
  session-user disable gates. No parallel auth (identity = existing
  user_id/session_id scopes + master switch); cross-scope reads as absent
  (no existence oracle); enforcement in service + tools/CLI, documented.
- **Corrections** route through Phase 13 (precedence + history); user
  authorship (source USER) now governs alongside USER_INPUT/PREFERENCE.
- **Erasure coordinated**: row + vector + both-direction links (new
  `repo.delete_links` — `memory_links` has no FK cascade) + graph evidence
  scrub (new `graph.scrub_memory`; edges stay, pointers go). Soft forget
  also drops the vector immediately. Trading-history guard
  (`allow_history=False` default, open override).
- **Disable semantics**: global (honest UNAVAILABLE/empty/zeroed) vs
  session/user gates (writes refused, reads served, working purged on
  session disable, restart-cleared). No background jobs exist — documented
  with pending-job behavior pinned by tests.
- **Surface**: `correct_memory` + `export_memories` tools; scope params on
  get/update/list/forget tools (additive); `list_memories` no longer
  touches `mgr._repo` directly; CLI `correct`/`erase`/`export` verbs
  (forget-hard wording preserved for the existing test).
Key identifiers: `UserControls`, `manager.controls`, `repo.delete_links`,
`graph.scrub_memory`, `EXPORT_FORMAT_VERSION`.
Evidence: `tests/memory/test_user_controls.py` — **17 passed**; memory +
CLI suite **297 passed, 4 skipped** (exit 0). Ruff clean except
pre-existing F841 (CLI, at HEAD, untouched). `mypy` unavailable in env.
See `phase-reports/phase-15.md`.
Test-caught issues fixed in-phase: USER-authored rows uncorrectable
(gate widened to source authorship), CLI hard-delete wording regression,
tool container wiring in tests, single-entity graph edge assumption.

### Phase 14 handoff (previous)

Phase 14 (decay, retention and lifecycle) is DONE (suite green: 21 new
tests, full memory suite 276 passed / 4 skipped). Hardened the existing
`MemoryLifecycle` in place (no replacement, no new scheduler — the
caller-invoked `manager.decay()` verb is the scheduling infrastructure):
- **Neglect chain**: new `MemoryStatus.DECAYED`; ACTIVE→STALE→DECAYED→
  ARCHIVED at 3/6/9 half-lives (defaults ~90/180/270d); LOW_CONFIDENCE
  parallel flag; EXPIRED TTL-first; DELETED user-only. EPHEMERAL archives
  at the STALE point (existing behaviour kept).
- **Protection**: TRADING type + PREDICTION veracity skip the neglect
  chain (explicit TTLs still expire); CRITICAL never auto-archives (plus
  policy stamps it PERMANENT at write); PERMANENT always ACTIVE.
- **Batches**: `decay(now=, batch_size=, max_batches=)` pages `list_by`;
  version-guarded transitions (`skipped_conflict`, never clobber);
  idempotent fixed-point re-runs; controllable clock (lifecycle `clock=`
  + per-call `now=`).
- **Propagation**: recallable rows re-indexed on the same pass (fixes a
  real bug: bare `repo.update` dropped vectors via FK cascade with no
  rebuild); ARCHIVED/EXPIRED vectors deleted; `verify/repair_projection`
  narrowed to recallable rows; one shared `RECALLABLE_STATUSES`
  (domain.enums) across lifecycle/retriever/SQL/projections.
- **Retrieval**: DECAYED recallable (weak score ranks last); ARCHIVED/
  EXPIRED need `include_archived`; DELETED never served (SQL + predicate).
- **Reactivation**: `manager.reactivate()` (explicit, re-indexes; refuses
  DELETED/missing); STALE/DECAYED auto-restore on fresh access via pure
  re-evaluation.
Key identifiers: `MemoryStatus.DECAYED`, `RECALLABLE_STATUSES`,
`manager.decay(now, batch_size, max_batches)`, `manager.reactivate`.
Evidence: `tests/memory/test_lifecycle.py` — **21 passed**; full memory
suite **276 passed, 4 skipped** (exit 0). Ruff clean except pre-existing
UP042 (enum style) + B905 (writer zip, both at HEAD, untouched). `mypy`
unavailable in env. See `phase-reports/phase-14.md`.
Test-caught bugs fixed in-phase: dangling RECALLABLE reference hidden by
bare except (now logged), missing logger import, boundary relativity,
CRITICAL double-layer, manager kwarg passthrough, enabled gate.

### Phase 13 handoff (previous)

Phase 13 (confidence and evidence updates) is DONE (suite green: 20 new
tests, full memory suite 255 passed / 4 skipped). New `ConfidenceUpdater`
(`memory/services/confidence.py`), exposed as `manager.confidence`:
- **Rules** (deterministic, bounded, history-appended): `confirm` (+0.05,
  cap 0.95, source-deduped); `correct` (sets 0.9, user-governed rows only);
  `record_reuse` (+0.03/-0.05, cap 0.9/floor 0.1); `record_outcome`
  (+0.05/-0.10, never for forecasts); `apply_contradiction` (-0.05, floor
  0.2, per-contradictor idempotent). History in
  `metadata["confidence_history"]` (cap 20) + `history()` reader.
- **Refusals**: TRADING type / PREDICTION veracity / history rows refused
  with `MemoryValidationError`; user corrections govern USER_INPUT and
  PREFERENCE rows only. Forecast payloads (`prob_up`) never rewritten.
- **Pins**: retrieval never bumps (access counts only); age never decays
  confidence (recency lives in the scorer); version-guarded retries;
  existing `MemoryStored` announcements, no new bus.
Key identifiers: `ConfidenceUpdater`, `manager.confidence`,
`ConfidenceUpdateResult`.
Evidence: `tests/memory/test_confidence.py` — **20 passed**; full memory
suite **255 passed, 4 skipped** (exit 0). Ruff clean on changed files.
`mypy` unavailable in env. See `phase-reports/phase-13.md`.
Test-caught issue fixed in-phase: history-cap test hit rule bounds before
the cap (rewritten with net-zero alternating rules).

### Phase 12 handoff (previous)

Phase 12 (consolidation and contradictions) is DONE (suite green: 16 new
tests, full memory suite 235 passed / 4 skipped). Hardened the existing
`MemoryConsolidator` in place (no replacement, no new scheduler — the
caller-invoked `manager.consolidate()` verb is the scheduling
infrastructure, like `decay()`):
- **Merge discipline**: byte-identical copies merge (evidence/confidence/
  provenance/entities fold into survivor; originals archived with
  `derived_from` links); near-merge requires normalised equality +
  type/scope/entity guards. Protected types (EPISODIC/FAILURE/TRADING/
  PROCEDURAL) and PREDICTION veracity never merge; disjoint entities never
  merge; ambiguous pairs get `related_to` links and stay separate.
- **Contradiction**: structured rule only (shared entity + negation
  morphology or divergent FACT/USER_INPUT) → two-way `contradicts` link,
  both rows live. Similarity is never contradiction.
- **Supersession**: only inside a structured contradiction, only
  FACT/USER_INPUT same-entity strictly-newer divergent claims → older
  archived with `supersedes` link + `contradicts` link (both counted).
  OBSERVATION series never supersede; equal timestamps stay separate.
- **Batches**: `consolidate(batch_size=, max_batches=)` pages `list_by`;
  re-runs skip archived rows and existing same-type links (idempotent);
  disabled/flag-off returns zeroed report; `MemoryConsolidated` event kept.
- `manager.consolidate()` forwards batch kwargs (additive, defaults
  preserve old behaviour).
Key identifiers: `MemoryConsolidator.consolidate`, `contradicts` /
`supersedes` / `related_to` link types, `_PROTECTED_TYPES`.
Evidence: `tests/memory/test_consolidation.py` — **16 passed**; full memory
suite **235 passed, 4 skipped** (exit 0). Ruff clean on changed files.
`mypy` unavailable in env. See `phase-reports/phase-12.md`.
Test-caught bugs fixed in-phase: sync/async split (`_decide` sync decision
+ `_resolve_one` async actions), bidirectional supersession pool bug,
manager kwarg passthrough, disabled-subsystem gate.

### Phase 11 handoff (previous)

Phase 11 (failure and recovery memory) is DONE (suite green: 17 new tests,
full memory suite 219 passed / 4 skipped). All Memory-owned,
backward-compatible:
- New `FailureRecorder` (`memory/services/failures.py`), constructed once by
  `MemoryManager` and exposed as `manager.failures`: `record_failure` ->
  `record_attempt` (x N) -> `resolve` / `confirm_cause`, plus `link_episode`
  / `link_procedure` / `link_alternative` / `failure_alternatives`,
  `get_failure` / `list_failures` / `list_open`.
- **Fact/cause separation**: `observed_symptoms` are facts;
  `suspected_cause` quarantined out of the summary until `confirm_cause`;
  `from_dict` added (old agent-written rows without the new keys parse via
  defaults -- compat tested).
- **Attempts**: `RecoveryAttempt` value object (action/status/detail/
  timestamp); cap 50 per failure, oldest-first, counted in
  `truncated_attempts`; duplicate deliveries and repeated resolutions write
  nothing (version unchanged).
- **Resolution recomputes presentation**: `_mutate` rebuilds content/tags/
  confidence/importance from the updated record, so a resolved failure stops
  reading `open` (test-caught bug, fixed).
- **Links**: episode (`derived_from`/`failure_in_episode`) + procedure
  (`observed_in`/`failure_in_procedure`) attach at record or late-arrive via
  `link_episode`/`link_procedure` (idempotent, missing targets skipped);
  `link_alternative` records `recovered_by` edges with evidence -- the
  alternative is never modified (no auto procedure revision).
- **Redaction**: all free-text fields scrubbed + bounded; argument values
  never stored (names only); credentials pinned absent by tests.
- **Restart**: `list_open` pages in bounded batches; verified with a real
  file DB reopened by a fresh manager (attempt + resolve resume).
- `remember_failure` unchanged -- agent single-shot rows read back through
  the recorder (compat + search tests).
Key identifiers: `FailureRecorder`, `manager.failures`, `RecoveryAttempt`,
`FailureRecord.from_dict`, `recovered_by` link type.
Evidence: `tests/memory/test_failure_memory.py` — **17 passed**; full memory
suite **219 passed, 4 skipped** (exit 0). Ruff clean on changed files.
`mypy` unavailable in env. See `phase-reports/phase-11.md`.

### Phase 10 handoff (previous)

Phase 10 (episodic memory foundation) is DONE (suite green: 21 new tests,
full memory suite 202 passed / 4 skipped). All Memory-owned,
backward-compatible:
- New `EpisodeRecorder` (`memory/services/episodes.py`), constructed once by
  `MemoryManager` and exposed as `manager.episodes`. Explicit lifecycle:
  `start_episode` -> `record_action` / `record_observation` ->
  `finalize_episode`, plus `attach_failure` / `episode_failures`,
  `get_episode` / `list_episodes` / `list_incomplete`.
- **Durability**: incomplete rows (outcome UNKNOWN, no `ended_at`) persist via
  `store(..., idempotency_key=episode_id)`; mutations are version-guarded
  read-modify-writes with bounded retries; restart recovery via
  `list_incomplete` (verified with a real file DB reopened by a fresh manager).
- **Idempotency**: duplicate starts return the stored episode; duplicate
  action/observation deliveries and repeated finalizations write nothing
  (version unchanged); re-finalize with a different status updates the single
  row in place -- never a second episode.
- **Chronology**: appends re-sorted on every write and read, so late arrivals
  slot into place; appending after finalize keeps the recorded outcome/ended_at.
- **Redaction**: tool arguments via forbidden-key `redact_keys`; goal,
  summaries, errors, lessons, provenance, environment via secret-span
  `redact_text` (goal redactions labelled in provenance). No credential
  reaches the row (pinned by tests).
- **Scope isolation**: `task_id` / `session_id` listings never cross; failures
  attach with the same `derived_from` / `failure_in_episode` contract as the
  agent integration.
- **Bounds**: `MEMORY_EPISODE_MAX_ACTIONS` (default 200, new additive knob in
  `Settings` + `MemoryConfig` wired from config); oldest dropped first, counted
  in `truncated_actions` metadata, never silently. Listings take `limit` + page.
- **Summaries attributable**: stored content always rebuilt from stored steps
  via `Episode.summary()`; nothing invented, nothing stale.
- **Disabled honesty**: starts return unsaved (no row for the id); storage
  failures raise `MemoryStorageError` rather than masquerading as success.
- Domain: new `EpisodeObservation` value object; `Episode` gains
  `observations` / `relevant_memories` / `provenance` (lossless round-trip);
  `to_memory()` stamps `episode_id` metadata + provenance detail.
- `remember_episode` unchanged -- the agent integration's single-shot path
  records rows the recorder reads back (covered by a compat test).
Key identifiers: `EpisodeRecorder`, `manager.episodes`,
`MemoryConfig.episode_max_actions`, settings `MEMORY_EPISODE_MAX_ACTIONS`,
`EpisodeObservation`.
Evidence: `tests/memory/test_episodic_memory.py` — **21 passed**; full memory
suite **202 passed, 4 skipped** (exit 0). Ruff clean on changed files except
the repo-wide pre-existing `UP017` (`timezone.utc` vs `datetime.UTC`) style,
verified at HEAD via stash and left untouched. Settings load check resolves
`MEMORY_EPISODE_MAX_ACTIONS` → 200. `mypy` unavailable in env. See
`phase-reports/phase-10.md`.

### Phase 9 handoff (previous)
- `WorkingMemory` rewritten from a single process-wide deque into a
  **session/task-scoped, TTL-aware, concurrency-safe, ephemeral** store
  (`memory/services/working_memory.py`). New `ObservationResult` value object.
- **Scoping**: every `WorkingItem` carries `session_id` + optional `task_id`;
  sessions isolated; `end_session` / `complete_task` scoped cleanup. Omitting
  `session_id` uses a `"default"` session, so the legacy single-session API
  (`add/update/remove/items/clear`) used by Agent/Desktop is unchanged.
- **TTL**: per-item `ttl_seconds` + session default from new config
  `working_ttl_seconds` (settings `MEMORY_WORKING_TTL_SECONDS`, default 0 == no
  expiry). Injectable `clock` for deterministic tests; `sweep_expired()`.
- **Freshness/sequence**: current observations set via `observe(key, ...,
  sequence=, observed_at=)`; stale (older sequence, or older timestamp on tie,
  or unsequenced-vs-sequenced) updates rejected so delayed observations cannot
  overwrite newer known state. `current_observation` / `current_observations`.
- **Bounded**: per-session capacity (`MEMORY_MAX_WORKING_CONTEXT`), evict
  least-important oldest.
- **Evidence selection**: `mark_evidence(item_id)` + `promote_working(...,
  only_evidence=True)` / `to_memories(..., only_evidence=True)`. `promote_working`
  is a **no-op when the subsystem is disabled** (returns `[]`, persists nothing).
- **Concurrency**: `threading.RLock` guards all shared state. **Restart**:
  ephemeral by design — empty after restart; only promoted items persist.
Key identifiers: `WorkingMemory.observe/current_observation/end_session/
complete_task/sweep_expired/mark_evidence/to_memories`, `ObservationResult`,
`MemoryConfig.working_ttl_seconds`, settings `MEMORY_WORKING_TTL_SECONDS`.
Config field is additive; the direct-construction test helper in
`test_embedding_provider.py` was updated to pass it.
Evidence: `tests/memory/test_working_memory.py` — **22 passed**; full memory
suite **181 passed, 4 skipped** (exit 0). Ruff clean on changed files except the
repo-wide pre-existing `UP017` (`timezone.utc` vs `datetime.UTC`) style, which
`_clock.py` itself carries at HEAD — matched for consistency. `mypy` unavailable
in env. See `phase-reports/phase-09.md`.

### Phase 8 handoff (previous)

Phase 8 (explainable hybrid retrieval) is DONE. All Memory-owned, backward-compatible:
- **Filter isolation**: `MemoryRetriever._passes` applies status/scope, type,
  veracity, context, tag, `min_confidence` and `max_age_days` uniformly to
  candidates from *every* source after expansion, so graph/link expansion can no
  longer bypass structured constraints. The entity-expansion probe now inherits
  the query's hard filters (previously it reset to entities-only).
- **Budget bounds**: `MemoryQuery` gains `max_tokens`, `max_chars`,
  `max_per_type`, `max_age_days` (all default 0 == unbounded). Final selection
  (`_apply_budget`) takes top-ranked memories honouring each bound; overflowing
  memories are skipped whole, not truncated. Token count is conservative
  (`estimate_tokens` = `ceil(len/3)`); `token_count_exact` is always `False`.
- **Provenance + honest report**: `RetrievalExplanation.sources` lists the
  candidate source(s) (`structured`/`vector`/`graph_entity`/`graph_link`). New
  `RetrievalReport` (domain/query.py) carries `results`, `degraded_sources`,
  and `candidates_considered` / `dropped_by_filter` / `dropped_by_threshold` /
  `dropped_by_budget` / `token_count_exact`.
- **Safe degradation**: vector or graph source failure is caught, recorded in
  `degraded_sources`, and recall continues on the remaining sources instead of
  raising. Disabled/not-started subsystem → empty report, `subsystem_unavailable`.
- **Manager API**: `retrieve(...)` keeps its old return type (`list[MemoryResult]`)
  and gains the four budget kwargs; new `retrieve_report(...)` returns the full
  `RetrievalReport`. `MemoryRetriever.retrieve` delegates to new
  `retrieve_report`. The `recall` tool is unchanged (still uses `retrieve`).
Key identifiers: `RetrievalReport`, `MemoryRetriever.retrieve_report`,
`MemoryRetriever._passes`, `MemoryRetriever._apply_budget`,
`aetheros.memory.services.retriever.estimate_tokens`.
Evidence: `tests/memory/test_hybrid_retrieval.py` — 16 passed, 1 skipped
(opt-in `real_embeddings`); full memory suite **159 passed, 4 skipped** (exit 0).
Ruff clean on all five touched files. `mypy` unavailable in env (`No module named
mypy`), same as prior phases. See `phase-reports/phase-08.md`.

Real-provider evidence for the semantic ranking path is pending: the opt-in test
`test_real_semantic_retrieval_ranks_by_meaning` is written and skipped by
default — run with `AETHEROS_MEMORY_TEST_OLLAMA=1` +
`AETHEROS_MEMORY_TEST_OLLAMA_MODEL=<model>` against a reachable daemon to satisfy
the integration acceptance.

### Phase 7 handoff (previous)

Phase 7 (knowledge-graph hardening) is DONE. All Memory-owned, backward-compatible:
- Bounded, cycle-safe traversal in `graph/store.py`: `TraversalBounds` (max
  hops/fan-out/results/time) + per-hop SQL BFS replacing the whole-graph
  networkx materialisation. `find_related_entities` / `find_path` keep their old
  signatures; new `relation` / `bounds` params optional. networkx no longer used
  by the memory subsystem (dependency declaration intentionally left in place).
- Referential integrity: `add_relationship` rejects edges with a missing
  endpoint (`MemoryValidationError`).
- Schema **version 2**: partial active-edge indexes
  `ix_rel_active_source` / `ix_rel_active_target`; EXPLAIN QUERY PLAN confirms
  selection. Additive, idempotent.
- Superseded edges filtered at every hop → no historical-edge leak through graph
  expansion.
Evidence: `tests/memory/test_knowledge_graph.py` — 18 tests pass; full memory
suite 143 passed, 3 skipped (exit 0). Pre-existing `store.py` ruff findings
(`I001`, `F401 utcnow`) evidenced at HEAD, untouched. `mypy` unavailable in env.
See `phase-reports/phase-07.md`.

Phases 3–6 were DONE before this (see ledger).

Top candidates for the next phase (unchanged priority):
- Finding #1 — full authorization / scope-filtering / deletion-visibility /
  sensitive-exclusion layer across retrieval, cache, embedding, graph expansion
  and export. Phase 5's identity filter closes the "incompatible embeddings
  mixed in a query" gap, Phase 7 closes historical-edge leakage *within the
  graph*, and Phase 8 now applies query-supplied scope/context/validity
  constraints uniformly across all retrieval sources. Still owed: an *authorization*
  boundary (caller identity/permissions, not just query-supplied filters),
  sensitive-field redaction on the retrieval/export path, and soft-deleted/
  historical no-leak across cache and export.
- Graph-side projection rebuild/repair (counterpart to Phase 4's vector repair).
- An automatic reembed-on-identity-change path (Phase 5 added the manual
  `reembed_all()` + a loud startup warning; auto-migration is deferred).

When a phase is authorized: re-read `agent-contract.md`, this file, the latest
phase report, and the live source for the targeted modules; re-run the
concurrent-agent audit (git status/diff); then follow the Phase Execution
Protocol.
