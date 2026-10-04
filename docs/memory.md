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
   |             +--- KnowledgeGraph (entities + relationships, networkx)
   +--------------------------- MemoryRepository
                                      |
                                 SQLiteDatabase (schema + migrations)
```

### Layers

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Domain | `memory/domain/` | Storage-free value objects: `Memory`, `Episode`, `Entity`/`Relationship`, `Procedure`, `Preference`, `FailureRecord`, `PredictionMemory`, `MemoryQuery`/`MemoryResult`. Lossless `to_dict`/`from_dict`. |
| Storage | `memory/storage/` | `SQLiteDatabase` (connection + migrations), `MemoryRepository` (typed CRUD, structured candidate generation). |
| Embeddings | `memory/embeddings/` | `EmbeddingProvider` ABC + deterministic `HashingEmbeddingProvider` (offline-safe default). |
| Vector | `memory/vector/` | `VectorIndex` — SQLite-backed float32 vectors, exact cosine via numpy. |
| Graph | `memory/graph/` | `KnowledgeGraph` — deduplicating entity/relationship store, networkx traversal. |
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
      -> semantic vector search over the candidate pool
      -> multi-signal scoring -> threshold -> dedup -> rank -> assemble
```

Ranking blends eight signals (semantic, lexical, recency, importance,
confidence, frequency, task-relevance, source-reliability) plus a graph
proximity boost, and **every** returned memory carries a `RetrievalExplanation`
that answers "why was this retrieved?".

## Confidence, lifecycle & consolidation

- **Confidence** is evidence-derived (e.g. a procedure's confidence shrinks
  toward 0.5 until it accumulates successes) and never overwritten blindly;
  contradictions are kept and resolved, not silently replaced.
- **Lifecycle** demotes memories by age/confidence/TTL (ACTIVE → STALE /
  LOW_CONFIDENCE → ARCHIVED / EXPIRED). PERMANENT scope never expires.
- **Consolidation** merges near-duplicates of the same type into a survivor that
  accumulates evidence; duplicates are archived (not deleted) with a link back.

## Epistemic integrity

Memory keeps *type* (working/episodic/…) orthogonal to *veracity*
(fact/prediction/assumption/observation/model-output/user-input). The validator
**rejects storing a prediction/model/inference-sourced memory as a FACT**
(CLAUDE.md §15). Trading predictions are stored immutably; a realised outcome is
a separate linked record — the original call is never rewritten.

## Trading integration

`MemoryManager.remember_prediction` / `remember_prediction_outcome` store trading
history and link outcomes to their predictions, so the system can later answer
"what happened last time a similar setup occurred?" and "where have we been
poorly calibrated?" without the trading subsystem depending on memory.

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


## Configuration

All knobs live on `Settings` and are resolved once into `MemoryConfig`:
`ENABLE_MEMORY`, `MEMORY_DATABASE`, `MEMORY_VECTOR_PROVIDER`,
`MEMORY_EMBEDDING_MODEL`, `MEMORY_EMBEDDING_DIM`, `MEMORY_RETRIEVAL_LIMIT`,
`MEMORY_SIMILARITY_THRESHOLD`, `MEMORY_DECAY_ENABLED`,
`MEMORY_DECAY_HALFLIFE_DAYS`, `MEMORY_CONSOLIDATION_ENABLED`,
`MEMORY_DEDUP_THRESHOLD`, `MEMORY_MAX_WORKING_CONTEXT`, `MEMORY_AUTO_REMEMBER`,
`MEMORY_AGENT_RECALL_LIMIT`, `MEMORY_AGENT_RECALL_MIN_SCORE`,
`MEMORY_AGENT_RECALL_MAX_CHARS`.

## CLI

```
memory                      # statistics
memory search <query>       # hybrid, explainable recall
memory show <id>            # full detail for one memory
memory list [type]          # recent memories
memory forget <id> [hard]   # soft (default) or hard delete
```

## Testing

`tests/memory/` covers storage round-trips, filtering, the service layer
(remember/retrieve/update/forget, episodes, failures, trading, consolidation,
decay, graph paths, explainability, working memory, the provider adapter) and
the tools; `tests/cli/test_memory_command.py` covers the CLI. Everything runs
against an in-memory SQLite database with the deterministic hashing embedder, so
the suite is fast, isolated and offline.

## Deferred / future work

Real embedding providers (Ollama/OpenAI) behind `EmbeddingProvider`; automatic
procedure learning from episode patterns (Phase 10) and a background
consolidation scheduler (Phase 12); document/knowledge ingestion (Phase 17);
a dedicated vision-grounding memory (Phase 18); large-scale performance
validation (Phase 25). The agent/planner integration (Phase 20) is implemented;
the separate `TaskManager`/`Agent` path is not wired, as the live agent path is
`AgentCore` (via the interaction gateway). The primitives the remaining phases
build on (links, consolidation, policy, scoring, episodes) are implemented and
tested.
```
