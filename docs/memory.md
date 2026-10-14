# AetherOS Memory Subsystem

The memory subsystem gives AetherOS a structured, retrievable, confidence- and
time-aware memory: working, episodic, semantic, procedural, preference, failure
and trading memory over a SQLite store, a swappable embedding/vector index and a
knowledge graph, surfaced through a hybrid, explainable retrieval pipeline and
the ToolRegistry.

It is **off by default** (`ENABLE_MEMORY=false`). When enabled, the bootstrapper
constructs one `MemoryManager`, registers it (and a `MemoryProvider` adapter)
in the DI container, and imports the memory tools.

## Architecture

```
                         MemoryManager  (high-level API)
                               |
   +--------------+------------+-------------+---------------+
   |              |            |             |               |
 Writer       Retriever   Consolidator   Lifecycle     WorkingMemory
   |              |            |             |
 Validator     Scorer      (dedup/merge) (decay/status)
 Policy          |
   |             +--- VectorIndex ---- EmbeddingProvider (hashing default)
   |             +--- KnowledgeGraph (entities + relationships, bounded SQL BFS)
   +--------------------------- MemoryRepository
                                      |
                                 SQLiteDatabase (schema + migrations)
```

### Layers

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Domain | `memory/domain/` | Storage-free value objects: `Memory`, `Episode`, `Entity`/`Relationship`, `Procedure`, `Preference`, `FailureRecord`, `PredictionMemory`, `MemoryQuery`/`MemoryResult`. Lossless `to_dict`/`from_dict`. |
| Storage | `memory/storage/` | `SQLiteDatabase` (connection + migrations), `MemoryRepository` (typed CRUD, structured candidate generation). |
| Embeddings | `memory/embeddings/` | `EmbeddingProvider` ABC + `HashingEmbeddingProvider` (offline-safe default) + `OllamaEmbeddingProvider` (real semantic embeddings via a running Ollama daemon). Identity-aware: `name = ollama:<model>:<dim>`. |
| Vector | `memory/vector/` | `VectorIndex` — SQLite-backed float32 vectors, exact cosine via numpy. Search is scoped to the active embedding identity so different models are never mixed. Whole-index search excludes soft-deleted rows (`exclude_deleted=True`) and is bounded (`max_scan`, default 50k, with a logged warning on truncation); `search_many` does batched queries; stores are guarded against wrong-dimension/non-finite vectors. |
| Graph | `memory/graph/` | `KnowledgeGraph` — deduplicating entity/relationship store with directed, temporal (`valid_from`/`valid_to`), evidenced edges. `add_relationship` reinforces an existing active edge instead of duplicating, and rejects edges whose endpoints do not exist (invalid-reference guard). Traversal (`find_related_entities`, `find_path`) is a **bounded** breadth-first walk done one hop at a time in SQL over the active edge set — never materialising the whole graph — governed by `TraversalBounds` (max hops, fan-out, result count, wall-clock time) and cycle-safe. Per-hop neighbour queries are backed by the partial `ix_rel_active_source`/`ix_rel_active_target` indexes (schema v2). |
| Services | `memory/services/` | `MemoryManager`, `MemoryWriter`, `MemoryRetriever`, `MemoryScorer`, `MemoryValidator`, `MemoryConsolidator`, `MemoryLifecycle`, `MemoryPolicyEngine`, `WorkingMemory`, `SQLiteMemoryProvider`. |
| Tools | `memory/tools.py` | `remember`, `recall`, `get_memory`, `update_memory`, `forget_memory`, `list_memories`, `find_related_memory`, `memory_status`. |

## Storage schema

Every cognitive kind persists as one row in `memory_items`, discriminated by
`memory_type` and carrying its full typed structure in a `data` JSON column.
Dedicated tables exist only where a distinct query pattern needs one:
`memory_embeddings` (vectors), `entities`/`relationships` (graph),
`memory_links` (memory-to-memory edges), `memory_tags`/`memory_entities`
(indexed filtering side tables), `memory_access` (read audit). Migrations are an
ordered, append-only list applied by version — no destructive rebuilds.

## Retrieval pipeline (hybrid, explainable)

```
query -> structured candidate generation (SQL filters)
      -> graph expansion (entity neighbourhood + memory links)
      -> uniform constraint filtering (scope/status/validity/age/confidence)
      -> semantic vector search over the candidate pool
      -> multi-signal scoring -> threshold -> dedup -> rank
      -> budgeted context selection (limit / per-type / chars / tokens)
```

Ranking blends eight signals (semantic, lexical, recency, importance,
confidence, frequency, task-relevance, source-reliability) plus a graph
proximity boost, and **every** returned memory carries a `RetrievalExplanation`
that answers "why was this retrieved?" — its actual per-signal component scores,
the human `reasons`, and `sources` provenance naming which candidate source(s)
surfaced it (`structured`, `vector`, `graph_entity`, `graph_link`).

### Filter isolation (Phase 8)

Scope, deletion/status, veracity/type, context, tag, `max_age_days` and
`min_confidence` constraints are applied **uniformly** to every candidate by one
in-memory predicate (`MemoryRetriever._passes`), mirroring the repository's SQL
filter. Graph and memory-link expansion therefore can never smuggle in a
candidate the structured filters would reject — a linked or entity-neighbour
memory is subject to exactly the same constraints as a directly-matched one.

### Budgeted, honest context (Phase 8)

`MemoryManager.retrieve_report(...)` (and the budget keyword args on
`retrieve(...)`) return a `RetrievalReport`. Besides the ranked `results` it
discloses:

| Field | Meaning |
| --- | --- |
| `degraded_sources` | candidate sources that failed and were skipped (e.g. `vector:TimeoutError`) |
| `candidates_considered` | pool size after uniform filtering |
| `dropped_by_filter` / `dropped_by_threshold` / `dropped_by_budget` | why candidates were discarded |
| `token_count_exact` | always `False` — see below |

Budget bounds (all default to `0` == unbounded, so existing callers are
unaffected): `limit` (max memories), `max_per_type`, `max_chars`, `max_tokens`.
A memory that would overflow a bound is **skipped whole**, never truncated.
Token counting is **conservative** (`ceil(len/3)`, an over-estimate relative to
a ~4-chars/token BPE tokenizer), so a `max_tokens` budget is never silently
exceeded; `token_count_exact` is therefore `False`.

Optional recall **degrades safely**: if the vector index or graph store is
unreachable the retriever skips that source, records it in `degraded_sources`,
and still returns whatever structured/lexical/graph results remain rather than
raising. A disabled or not-yet-started subsystem returns an empty report flagged
`subsystem_unavailable`.


## Working (short-term) memory

`WorkingMemory` (`memory/services/working_memory.py`, exposed as
`manager.working`) is the live, **ephemeral** reasoning scratchpad: the current
task/goal/plan, the application/screen in focus, the instrument/timeframe under
analysis, recent tool calls and decisions, and — kept deliberately apart — the
*current observations* of the world (screen state, market state).

### Ephemeral vs persisted

| State | Lifetime |
| --- | --- |
| Working items & current observations | **Ephemeral** — in-process only, **lost on restart by design**. Never written to the database row-by-row. |
| Promoted memories | **Persisted** — only what `promote(...)` explicitly copies into long-term memory survives. |

Nothing in working memory is durable unless explicitly promoted. We never turn
all live context into long-term memory by default.

### Session / task scoping

Every item carries a `session_id` (and optionally a `task_id`). Sessions are
**isolated**: one session never reads or evicts another's items, and cleanup is
scoped — `end_session(session_id)` purges a whole session, `complete_task(task_id)`
purges just that task's items. Calls that omit `session_id` use a default
session, so the legacy single-session API (used by the Agent/Desktop layers via
`manager.working.add/update/remove/items`) is unchanged.

### Size limits, TTL and cleanup

- **Bounded**: each session is capped at `MEMORY_MAX_WORKING_CONTEXT` general
  items; on overflow the least-important, oldest item is evicted. The cap is
  **per session**.
- **TTL**: items may carry `ttl_seconds`; a session default comes from
  `MEMORY_WORKING_TTL_SECONDS` (`0` == no expiry). Expired items are invisible to
  reads and reclaimed by `sweep_expired()`. The clock is injectable
  (`WorkingMemory(clock=...)`) so TTL behaviour is deterministic in tests.
- **Cleanup**: `end_session`, `complete_task`, `sweep_expired`, and `clear`.

### Freshness / sequence (current observations)

Current observations are set via `observe(key, content, sequence=…, observed_at=…)`
and represent **now**, not a historical reference. An update supersedes the
current observation only if it is *not older*: a higher `sequence` wins; on a tie
(or when both are `None`) a later `observed_at` wins; a sequenced update is never
displaced by an unsequenced one. A strictly older (delayed/out-of-order) update
is **rejected** (`ObservationResult.accepted is False`) and the newer known state
remains in effect — a lagging observation can never overwrite newer truth.
Retrieved long-term memory never overrides a current observation.

### Explicit evidence selection

`mark_evidence(item_id)` flags the items worth keeping; `promote_working(...)`
(manager) / `to_memories(...)` then persist either everything above an importance
threshold (default) or, with `only_evidence=True`, exactly the marked items.
`promote_working` is a **no-op when the subsystem is disabled** — it persists
nothing rather than reporting a false success.

### Concurrency & restart

All mutation goes through a re-entrant lock, so updates arriving from different
threads (e.g. desktop automation run via `asyncio.to_thread`) cannot corrupt the
structure. On process restart working memory starts empty — this is intentional;
anything that must survive a restart must have been promoted to long-term memory.


## Episodic memory lifecycle (Phase 10)

`manager.episodes` (`EpisodeRecorder`) is the explicit lifecycle for durable
task-execution records: `start_episode` → `record_action` / `record_observation`
→ `finalize_episode`. The agent's single-shot `remember_episode` path is
unchanged; episodes it wrote read back through the recorder.

- **Start** persists an incomplete row (outcome `UNKNOWN`, no `ended_at`) via
  `store(..., idempotency_key=episode_id)` — a retried start is a safe no-op,
  never a duplicate episode. Capture goal, task/session ids, environment,
  relevant-memory ids (linked as `references` edges, missing ones skipped),
  and secret-scrubbed provenance.
- **Appends** are chronological and deduplicated: actions on `(name,
  started_at)`, observations on `(key, observed_at)`, so redelivered events
  cannot double-record a step and late arrivals slot into place. Appends use
  the optimistic version guard with bounded retries, so concurrent writers
  converge instead of losing steps. Appending to a finalized episode is
  allowed (late evidence) but never moves `ended_at` or the outcome.
- **Failures** attach via `attach_failure(episode_id, failure_id)` using the
  same `derived_from` / `failure_in_episode` link contract as the agent
  integration; repeats are no-ops, never duplicate links. `episode_failures`
  lists the attached failure records.
- **Finalize** closes with outcome + duration + lessons (idempotent: same
  status writes nothing; a different status updates the single row in place).
- **Retrieval**: `get_episode` (never raises for a read — missing,
  non-episode, soft-deleted or corrupt rows read as absent),
  `list_episodes(task_id= / session_id= / status= / include_incomplete= /
  limit=)` for scoped browsing, and `list_incomplete()` for restart recovery.
- **Redaction before persistence**: tool arguments pass through forbidden-key
  redaction; goal, summaries, errors, lessons, provenance and environment pass
  through secret-span scrubbing — no credential reaches the row.
- **Bounded**: at most `MEMORY_EPISODE_MAX_ACTIONS` (default 200) actions per
  episode; the oldest are dropped first and the count is kept in row metadata
  (`truncated_actions`), never silently. Listings take an explicit `limit`
  and page internally.
- **Summaries stay attributable**: the stored content is always rebuilt from
  the stored steps via `Episode.summary()` — the recorder never invents steps
  or caches a stale summary.
- **Disabled mode is honest**: starts return the episode unsaved (recognisable
  because no row exists for its id); nothing masquerades as persisted.

No second event bus: every mutation flows through the existing
store/update/get/link verbs, so the `MemoryStored` event contract announces
episode activity to existing subscribers.


## Writing memories

Two write surfaces, both honest about persistence:

- `MemoryManager.remember(...)` / `remember_memory(memory)` — the ergonomic verb.
  Returns the `Memory`; raises on storage failure. A returned object is **not**
  proof it was stored: a retention-policy decline returns the object unsaved, and
  a disabled subsystem returns it as a no-op.
- `MemoryManager.store(memory, *, idempotency_key=None)` — returns a `WriteResult`
  with an explicit status so you never confuse "skipped" with "stored":

  | status | meaning | `.ok` | `.persisted` |
  |---|---|---|---|
  | `STORED` | durably written | ✓ | ✓ |
  | `SKIPPED` | policy decline **or** idempotent duplicate | ✓ | ✗ |
  | `FAILED` | attempted, nothing persisted (reason carries the error) | ✗ | ✗ |
  | `UNAVAILABLE` | subsystem disabled / not initialized | ✗ | ✗ |
  | `PENDING` | reserved for a future async-durable path | ✗ | ✗ |

  ```python
  result = await manager.store(memory, idempotency_key="signal-123")
  if result.persisted:
      ...  # durably stored
  elif result.status is WriteStatus.SKIPPED:
      ...  # already stored (same id or same idempotency_key) / policy declined
  ```

  Re-submitting the same memory id, or the same `idempotency_key`, is a safe
  `SKIPPED` no-op — not a duplicate row. This makes retries and at-least-once
  event delivery safe.

**Concurrent edits.** `update(id, ...)` is last-writer-wins by default. Pass
`expected_version=` for optimistic concurrency: if the stored row has moved on
since you read it, the update is rejected with `MemoryConflictError` instead of
clobbering the other writer — re-read and reapply.

**Projection repair.** The vector index is a derived projection of the
authoritative SQLite store. `await manager.verify_projection()` reports any drift
(`missing` vectors / `orphan` vectors) read-only; `await
manager.repair_projection()` reconstructs it from the authoritative rows
(re-embedding what's missing, dropping orphans). Repair is idempotent and never
fabricates a projection.

## Confidence, lifecycle & consolidation

- **Confidence** is evidence-derived (e.g. a procedure's confidence shrinks
  toward 0.5 until it accumulates successes) and never overwritten blindly;
  contradictions are kept and resolved, not silently replaced.
- **Stored-fact confidence** (`manager.confidence`, Phase 13) moves only
  through documented, bounded, deterministic rules, each appended to an
  auditable evidence history (`metadata["confidence_history"]`, cap 20):
  independent `confirm` (+0.05, cap 0.95, deduped by source — the same
  source twice is not independent evidence), user `correct` (sets 0.9, but
  only for USER_INPUT/PREFERENCE rows — never predictions, trading history,
  episodes, failures or procedures), verified `record_reuse` (+0.03/−0.05),
  observed `record_outcome` (+0.05/−0.10, never for forecasts — their
  outcomes are separate linked records), and `apply_contradiction` (−0.05,
  floor 0.2, naming its evidence). Update bounds float between 0.1 and
  0.95; the domain clamp holds absolute [0, 1].
- **What never moves confidence**: retrieval (access counts only), mere
  ageing (freshness lives in the scorer's recency signal and lifecycle
  status — decaying both would double-penalise), embedding similarity.
- **Separate numbers stay separate**: stored-fact confidence ≠ forecast
  probability (prediction rows pin `confidence=0.5`; the claim's
  uncertainty lives in `prob_up` etc.) ≠ retrieval relevance (the scorer's
  per-query blend) ≠ procedure success rate (Wilson-shrunk counts).
  These scores are bounded heuristics, **not calibrated probabilities** —
  no calibration is measured here.
- **Lifecycle** (`manager.decay(now=, batch_size=, max_batches=)`,
  Phase 14) demotes along a documented chain — ACTIVE → STALE (3
  half-lives untouched) → DECAYED (6) → ARCHIVED (9) — plus the parallel
  LOW_CONFIDENCE flag (confidence < 0.25), TTL-driven EXPIRED, and
  user-only DELETED (decay never deletes). PERMANENT scope always stays
  ACTIVE; CRITICAL importance never auto-archives; TRADING type and
  PREDICTION veracity skip the neglect chain (explicit TTLs still expire
  them). Passes are bounded, version-guarded (concurrent edits win; the
  transition is skipped and counted, never clobbered), idempotent and
  restartable, with a controllable clock. Status changes propagate to the
  vector projection on the same pass (recallable rows re-indexed —
  otherwise the store's REPLACE cascade would silently drop their vectors;
  ARCHIVED/EXPIRED rows have vectors deleted so no bypassed filter can
  leak them). Recall serves ACTIVE/LOW_CONFIDENCE/STALE/DECAYED;
  ARCHIVED/EXPIRED need `include_archived`; DELETED is never served.
  STALE/DECAYED reactivate automatically on fresh access;
  ARCHIVED/EXPIRED use the explicit `manager.reactivate()` verb (which
  rebuilds the vector). Decay reads confidence but never writes it, and
  never confuses it with freshness — an old row keeps its number, only
  its visibility changes. **Archival ≠ soft deletion ≠ erasure**:
  archival hides-by-neglect (reversible via reactivate), soft deletion
  hides-by-choice (excluded everywhere, row kept for audit), and true
  erasure (`forget(hard=True)`) removes the row + vector irreversibly —
  backups, if any, are outside this contract and must be handled by
  deployment policy.
- **Consolidation** (`manager.consolidate(batch_size=, max_batches=)`,
  Phase 12) deduplicates in bounded, restartable, idempotent batches:
  byte-identical copies merge into a survivor that accumulates evidence
  count, confidence, provenance (`merged_from`) and entities; the originals
  are archived (never deleted) with a `derived_from` link back, so every
  decision is reversible and auditable. Near-merges require normalised
  equality — genuinely different claims are linked (`related_to`), never
  merged, no matter how high the similarity scores.
- **Protected history never near-merges**: episodes, failures, trading rows
  and procedures with identical text are distinct events, not copies (agent
  re-recording is already idempotent at the store layer); predictions stay
  immutable even when duplicated. Same prose with disjoint entities never
  merges (no subject is silently dropped).
- **Contradictions are represented, never resolved by fiat.** A structured
  rule — shared entity plus negation morphology or divergent FACT/USER_INPUT
  assertions — records a two-way `contradicts` link and leaves both rows
  live. Similarity is explicitly never contradiction.
- **Supersession is narrow**: only inside a structured contradiction, only
  for FACT/USER_INPUT assertions about the same entity with a strictly newer
  timestamp — the older row archives with a `supersedes` link (disagreement
  preserved, current truth live). OBSERVATION series (price ticks, regime
  reads) never supersede: both readings stay live as history. Equal
  timestamps stay separate.
- **Scope isolation**: merges never cross type or scope boundaries — a
  session note never folds into a long-term memory.

## Epistemic integrity

Memory keeps *type* (working/episodic/…) orthogonal to *veracity*
(fact/prediction/assumption/observation/model-output/user-input). The validator
**rejects storing a prediction/model/inference-sourced memory as a FACT**
(CLAUDE.md §15). Trading predictions are stored immutably; a realised outcome is
a separate linked record — the original call is never rewritten.

## Content safety (write-path foundation)

Every write passes through `MemoryValidator`, which — besides the epistemic rule
above — applies a `ContentPolicy` (`aetheros.memory.domain.content_policy`):

- **Size limits.** `content` is bounded to `MAX_CONTENT_CHARS` (20k) and the
  structured `data` payload to `MAX_PAYLOAD_BYTES` (256 KiB). Oversize writes are
  rejected with `MemoryValidationError` — large text belongs to document
  ingestion, not a single memory.
- **Secret handling.** A conservative, high-precision scanner detects common
  credential shapes (AWS/GCP keys, Slack/GitHub tokens, bearer tokens, PEM
  private-key blocks, and `api_key=`/`password=`-style assignments). The policy's
  `on_secret` chooses the action: `REDACT` (default — the secret span is replaced
  in place and the removed kinds are recorded in
  `metadata["redacted_secret_kinds"]`, so a credential never lands in SQLite, the
  vector pool or an event while the write still succeeds), `REJECT` (refuse the
  write), or `ALLOW` (only for already-sanitised, trusted input).

This is a *foundation* that runs from the first write path, not an exhaustive DLP
scanner; the broader authorization / scope-filtering / sensitive-exclusion layer
(retrieval, cache, embedding, graph expansion, export) is tracked as future work.
Construct a stricter gate with `MemoryValidator(ContentPolicy(on_secret=SecretAction.REJECT))`.

## Embedding providers

The default `HashingEmbeddingProvider` is deterministic, offline-safe and
dependency-free, but gives lexical/feature-grade semantics only. For real
semantic retrieval, set `MEMORY_VECTOR_PROVIDER=ollama` and
`MEMORY_EMBEDDING_MODEL=<installed model>` (e.g. `nomic-embed-text`) against a
running Ollama daemon (`MEMORY_EMBEDDING_BASE_URL`, default
`http://127.0.0.1:11434`).

Honesty and identity guarantees:

- A requested real provider that is unreachable **fails startup** — it is never
  silently swapped for hashing. Set `MEMORY_EMBEDDING_FALLBACK=true` to opt into
  a *loud* degrade (logged warning) instead.
- The embedding dimension is probed from the live model at startup, not assumed.
  Each vector is stored under an identity `ollama:<model>:<dim>`; retrieval only
  compares vectors of the **active** identity, so two models (even same-dimension)
  are never blended.
- Changing the model/dimension leaves the old vectors unsearchable under the new
  identity. `MemoryManager` warns about this at startup; call
  `await manager.reembed_all()` to migrate the index to the active embedder.
  Inspect current identities with `await manager.embedding_identities()`.

## Trading integration

`manager.trading_history` (`TradingHistoryAdapter`, Phase 16) is the
Memory-owned seam for durable trading history: idempotent ingestion of
predictions, outcomes, regimes, analyses, strategy observations,
calibration records and reasoning summaries, plus as-of retrieval.

- **Decoupled by construction.** The adapter accepts plain data (dicts /
  memory-domain records), never trading-package objects. `from_*`
  constructors translate trading shapes (`PredictionRecord`,
  `RegimeAnalysis`, `TradingAnalysis`, `StrategyEvaluation`, calibration
  audits) field-by-field, tolerating missing keys — a trading-side shape
  change thins rows, never breaks ingestion. Numbers pass through
  verbatim: this layer never computes probabilities, Brier scores,
  returns or calibration corrections.
- **Three times, three questions.** `event_time` (when the market event
  happened) / `ingested_at` (when the row was written) / `evaluation_time`
  (when the outcome resolved). `history_as_of(instrument, as_of)` serves
  only rows with `event_time <= as_of` — future outcomes can never leak
  into historical tests, and undated rows are excluded (never leaked).
- **Immutable history, linked appends.** Predictions store once (caller
  ids, e.g. content digests, make re-ingestion a no-op); outcomes append
  as separate rows linked `has_outcome`. Out-of-order arrival works both
  ways (outcome-first links backfill on prediction arrival). Reasoning
  summaries cite `source_refs` and link each existing source — summaries,
  never primary evidence.
- **Scope isolation** by `instrument_id` (+ timeframe/venue); one
  instrument's history never appears in another's.
- **Honest ledger.** `verify_consumer_contract()` reports which trading
  shapes were verified live vs which rest on representative mappings —
  unverified consumer integration is stated, not implied.

`MemoryManager.remember_prediction` / `remember_prediction_outcome` store trading
history and link outcomes to their predictions, so the system can later answer
"what happened last time a similar setup occurred?" and "where have we been
poorly calibrated?" without the trading subsystem depending on memory.

## Document & knowledge ingestion (Phase 17)

`manager.documents` (`DocumentIngestion`) ingests notes, research dumps and
structured exports using only the standard library — plain text, Markdown
(structure only), JSON/JSONL records and CSV rows. There are no PDF/DOCX/HTML
extractors in this repo and none are invented here; remote-URL fetching is
unsupported (no URL policy layer exists to enforce), so callers pass
already-read text or an explicit local file.

- **Content-addressed versions.** A source's version IS its sha256 checksum.
  Identical bytes re-ingested are the same version (idempotent no-op);
  changed bytes are a new version whose chunks archive the old ones (old
  chunks leave recall with `derived_from` links to the new version row —
  never deleted silently). Corrections are new versions, not edits: there
  is intentionally no in-place chunk edit path.
- **Bounded.** Default 2000 chars per chunk (hard cap 8000, under the 20k
  write-path limit), 1 MiB per file read, 500 chunks per source. Oversized
  units are rejected, never silently truncated.
- **Resumable.** Chunks index in order; the source registry row's `cursor`
  advances per stored chunk, so an interrupted run re-ingested resumes
  where it stopped (chunk ids are deterministic, so replay is safe).
  A partially processed source reports `status=partial`.
- **Citable.** Every chunk is UNVERIFIED evidence carrying
  source/version/ref (Markdown section, JSON key/index, CSV row, JSONL
  line) in its metadata — every retrieval hit is attributable to its
  exact origin.
- **Untrusted by construction.** Imported text may contain wrong facts,
  prompt-injection prose or secrets: it persists as inert UNVERIFIED data
  (retrieval treats stored content as context, never instructions), and
  the write-path validator redacts secrets before persistence and before
  embedding.
- **No orphans, no stale projections.** Archiving a version or removing a
  source drops vectors inline (version-guarded row writes; `repair_projection`
  reconciles anything missed). `remove_source` archives every version's
  chunks + registry rows: nothing stays recallable, everything stays
  auditable by direct id read.
- **Honest ledger.** `verify_ingestion_contract()` states supported
  formats, explicitly unsupported inputs (pdf/docx/html, remote URLs,
  binary/OCR) and budgets.
- **Disabled safety.** Ingest/remove refuse while the subsystem is off —
  the archive paths write through the repository directly, so without the
  gate a disabled-mode ingest could archive the old version while
  persisting nothing to replace it.

## Agent & planner integration (Phase 20)

Memory is an automatic part of the agent lifecycle, not just a set of manual
tools. The flow is now:

```
user goal → memory recall → inject advisory context → plan → execute →
observe → … → terminal → record episode (+ failure/recovery)
```

- **Port, not coupling.** The agent package owns a small `AgentMemory` port
  (`agents/memory_port.py`: `AgentMemory`, `NullAgentMemory`, `MemoryContext`,
  `MemoryItemView`). `AgentCore` depends only on that port and never imports the
  memory package. The concrete `ManagerAgentMemory`
  (`memory/integration/agent_memory.py`) implements it over `MemoryManager`, so
  the dependency direction is memory → agents (no cycle).
- **Single on/off decision.** The bootstrapper injects `ManagerAgentMemory` when
  `ENABLE_MEMORY` is set, else `NullAgentMemory`. There is no `if ENABLE_MEMORY`
  in the agent loop — memory-off is a no-op collaborator.
- **Recall before planning.** `AgentCore.run` recalls relevant memory for the
  goal and injects it as a single advisory observation (so it reaches the
  planner through the existing context pathway). It is **bounded** by
  `MEMORY_AGENT_RECALL_LIMIT`, `MEMORY_AGENT_RECALL_MIN_SCORE` and
  `MEMORY_AGENT_RECALL_MAX_CHARS`, and **explainable** (each item carries its
  reasons).
- **Current reality wins.** The injected block is framed as *historical guidance
  only — verify against the current screen/state; current observations and
  vision take precedence*, so the planner never blindly replays a stale value
  (e.g. a remembered coordinate).
- **Automatic recording.** After a terminal (non-cancelled) run that used a tool
  or failed, the run is recorded as an `Episode` (goal, actions with argument
  *names* only, outcome, duration, metrics), and each failed tool call becomes a
  `FailureRecord`; when a later tool call recovered, the recovery is captured and
  the failure is linked to the episode. Recording is gated by
  `MEMORY_AUTO_REMEMBER` (default on when memory is enabled).
- **Never a point of failure.** Recall and recording are each wrapped so any
  memory error (SQLite, embedding, vector, graph, timeout) logs a warning and
  the task continues (spec Phase 20L).
- **No duplication.** Episode id = run id and failure id = `run_id:call_id`, so
  re-recording the same run replaces rather than duplicates (spec Phase 20M).
  Trading history (Phase 16) is untouched — this never rewrites a prediction.


## Failure & recovery memory (Phase 11)

`manager.failures` (`FailureRecorder`) is the explicit lifecycle for durable
failure records: `record_failure` → `record_attempt` (× N) → `resolve` /
`confirm_cause`, plus `link_episode` / `link_procedure` / `link_alternative`
and `get_failure` / `list_failures` / `list_open`. The agent's single-shot
`remember_failure` path is unchanged; its rows read back through the recorder.

- **Observed facts vs inferred causes.** `observed_symptoms` are facts.
  `suspected_cause` is an unverified hypothesis and is **quarantined**: stored
  in the payload (never lost) but excluded from the searchable summary until
  `confirm_cause` is called explicitly. An unverified suspicion must never
  read as a confirmed fact in retrieval.
- **Attempts, not just outcomes.** Each recovery try is appended with action,
  status, detail and timestamp (bounded at 50 per failure, oldest dropped
  first and counted in `truncated_attempts` metadata). The successful
  recovery is also in the attempt log, so the fix is attributable to a
  recorded step. Duplicate deliveries append nothing.
- **Alternatives are evidence links, never procedure edits.**
  `link_alternative(failure_id, alternative_id, evidence=...)` records a
  `recovered_by` edge to the procedure (or episode step) that actually
  worked, with evidence naming the source (episode id, successful step).
  The alternative itself is never modified — **no automatic procedure
  revision in this phase**.
- **Bound and redact error payloads.** Error text, symptoms, attempt details
  and context pass through forbidden-key redaction + secret-span scrubbing
  and length bounding before persistence. A 5KB traceback becomes a bounded
  preview; credentials from exceptions, URLs, request bodies or tool output
  never reach the row (pinned by tests).
- **Links tolerate absence.** Episode/procedure targets that don't exist yet
  are skipped with a warning at record time; `link_episode` /
  `link_procedure` attach them when they arrive (idempotent, no duplicate
  link rows).
- **Restart-safe.** No in-memory state; `list_open()` pages failure rows in
  bounded batches so interrupted work resumes on a fresh handle.
- **Disabled mode is honest**: records return unsaved; storage failures raise
  rather than masquerading as success.

**Evidence contract for procedure evolution (later phase).** A failure row
carries `failure_type`, the observed `error` + `symptoms`, the failing
`action`, the ordered `attempts` log, `successful_recovery` when one worked,
and `recovered_by` links to the alternative that succeeded (with `evidence`
metadata). Mine "failures of type T with successful recovery R" into
procedure fallbacks from these rows and links alone — without re-deriving
anything, and without ever promoting a quarantined suspicion.


## Configuration

All knobs live on `Settings` and are resolved once into `MemoryConfig`:
`ENABLE_MEMORY`, `MEMORY_DATABASE`, `MEMORY_VECTOR_PROVIDER`,
`MEMORY_EMBEDDING_MODEL`, `MEMORY_EMBEDDING_DIM`, `MEMORY_EMBEDDING_BASE_URL`,
`MEMORY_EMBEDDING_FALLBACK`, `MEMORY_RETRIEVAL_LIMIT`,
`MEMORY_SIMILARITY_THRESHOLD`, `MEMORY_DECAY_ENABLED`,
`MEMORY_DECAY_HALFLIFE_DAYS`, `MEMORY_CONSOLIDATION_ENABLED`,
`MEMORY_DEDUP_THRESHOLD`, `MEMORY_MAX_WORKING_CONTEXT`,
`MEMORY_WORKING_TTL_SECONDS`, `MEMORY_EPISODE_MAX_ACTIONS`,
`MEMORY_AUTO_REMEMBER`,
`MEMORY_AGENT_RECALL_LIMIT`, `MEMORY_AGENT_RECALL_MIN_SCORE`,
`MEMORY_AGENT_RECALL_MAX_CHARS`.

## CLI

```
memory                      # statistics
memory search <query>       # hybrid, explainable recall
memory show <id>            # full detail for one memory
memory list [type]          # recent memories
memory forget <id> [hard]   # soft (default) or hard delete
memory correct <id> <text>  # correct a user fact (history kept)
memory erase <id> [allow_history]  # coordinated permanent erasure
memory export               # all memories as JSON
```

## User memory controls (Phase 15)

`manager.controls` (`UserControls`) is the authorised administration layer:
scoped inspection, correction, forgetting, erasure, export, statistics and
enable/disable — without exposing raw storage internals (no SQL, vectors,
cursors, file paths; tools/CLI return plain dicts and strings).

- **Identity = scopes, not accounts.** This is a single-operator system;
  there is no login/auth layer, and none is invented. A caller presents
  `user_id` and/or `session_id`; rows carrying those scope values (or no
  scope, for legacy operator rows) are theirs. Anything else raises a
  uniform not-found — the boundary never reveals what exists outside it.
  Enforcement lives in this service and the tools/CLI above it; a direct
  `MemoryManager` handle is the operator's own and bypasses scope checks.
- **Corrections keep history.** `controls.correct` routes through the
  Phase 13 path: latest wins (version bump), both edits retained in the
  confidence history. Governs user-authored rows (PREFERENCE,
  USER_INPUT, or USER-sourced); refuses predictions, trading history and
  lifecycle records.
- **Forgetting excludes immediately.** Soft forget marks DELETED *and*
  drops the vector on the same call (authoritative filter plus
  defense-in-depth); default listings/exports/recall skip deleted rows,
  audit reads opt in explicitly.
- **Erasure is coordinated.** `controls.erase` removes the row, its
  vector, every link touching it (both directions — `memory_links` has no
  FK cascade), and every graph evidence pointer to it (edges stay;
  topology is shared knowledge). The report counts each so completeness
  is verifiable. **Soft deletion alone is not erasure**; backups, if any,
  are deployment policy outside this contract.
- **Trading-history guard.** Forgetting or erasing TRADING/PREDICTION rows
  without `allow_history=True` is refused with a policy error (erasure
  vs retention resolves openly through the flag, never silently).
- **Disable semantics.** Global (`ENABLE_MEMORY` off): writes report
  UNAVAILABLE, recall degrades empty, maintenance verbs return zeroed
  reports, in-flight operations complete against the store (SQLite
  serialises them), embeddings/projections idle (on-demand only).
  Session/user (`disable_session`/`disable_user`): scoped writes refused,
  reads still served, disabling a session purges its working context
  immediately. Gates are restart-cleared by design. There are no
  background jobs or queues in this subsystem — every verb is
  caller-invoked, so nothing can strand mid-flight.

## Backup & recovery

The authoritative store is a single SQLite file (`MEMORY_DATABASE`, default
`memory.db` under `DATA_DIR`). It runs in WAL mode, so a raw file copy taken
while the process is running can capture a torn WAL state. Use the native online
backup instead:

```python
db.backup("/path/to/backups/memory-2026-10-07.db")
```

`SQLiteDatabase.backup()` uses SQLite's online backup API and produces a
transactionally-consistent snapshot even while writes are in flight. The
destination directory is created if needed; backing up to `:memory:` is rejected.

Recovery (manual, deliberate — there is no auto-restore):

1. Stop the AetherOS process (so the live connection is closed).
2. Replace the live database file with the chosen backup. Also remove any
   stale `-wal` / `-shm` sidecar files next to the live DB so SQLite does not
   replay an old WAL over the restored snapshot.
3. Restart. On open, the migration runner brings the restored schema up to
   `LATEST_VERSION` if the backup predates the current version.

**Irreversible operations.** `memory erase <id>` (and
`MemoryManager.forget(id, hard=True)` / `controls.erase`) permanently deletes
the row and cascades to its embeddings, tags and entities, removes every
link touching it, and scrubs every graph evidence pointer to it — it cannot
be undone except by restoring a backup taken beforehand. Trading history
additionally requires `allow_history`. Ordinary (soft) deletion only sets
`status='deleted'` (plus an immediate vector drop) and is recoverable.
Schema migrations are append-only and non-destructive; no
current migration drops or rewrites existing data.

## Testing

`tests/memory/` covers storage round-trips, filtering, the service layer
(remember/retrieve/update/forget, episodes, failures, trading, documents,
consolidation, decay, graph paths, explainability, working memory, the
provider adapter) and the tools; `tests/cli/test_memory_command.py` covers the CLI. Everything runs
against an in-memory SQLite database with the deterministic hashing embedder, so
the suite is fast, isolated and offline.

## Deferred / future work

Real embedding providers (Ollama/OpenAI) behind `EmbeddingProvider`; automatic
procedure learning from episode patterns (Phase 10) and a background
consolidation scheduler (Phase 12); a dedicated vision-grounding memory
(Phase 18); large-scale performance validation (Phase 25). The agent/planner integration (Phase 20) is implemented;
the separate `TaskManager`/`Agent` path is not wired, as the live agent path is
`AgentCore` (via the interaction gateway). The primitives the remaining phases
build on (links, consolidation, policy, scoring, episodes) are implemented and
tested.
```
