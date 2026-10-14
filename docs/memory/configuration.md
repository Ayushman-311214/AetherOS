# Memory Subsystem — Configuration Contract (Phase 1)

> Canonical, validated production configuration for the Memory subsystem. All
> values are read **once** into `MemoryConfig` (`memory/config.py`) from
> `Settings` (`config/settings.py`) — never via scattered `os.getenv`
> (CLAUDE.md §18). Verified against the source at commit `b0a2537`.

## 1. Master switch

| Setting | Env (precedence: first wins) | Default | Effect |
|---|---|---|---|
| `ENABLE_MEMORY` | `ENABLE_MEMORY` | `true` | Master switch the bootstrapper gates on. `false` → no manager/provider registered, agent gets `NullAgentMemory`, every tool returns `MEMORY_DISABLED`. |

`ENABLE_MEMORY` is the only gate on whether the subsystem exists. Everything
below is read only when it is on.

## 2. Canonical memory settings

Each field below accepts two environment names via pydantic `AliasChoices`. **The
`AETHEROS_`-prefixed name has precedence** (it is listed first in every
`AliasChoices`), the bare name is the supported alias. Verified empirically:
with both `AETHEROS_MEMORY_EMBEDDING_DIM=512` and `MEMORY_EMBEDDING_DIM=128` set,
the resolved value is **512**.

| Field | Canonical env (wins) | Alias env | Default | Validation |
|---|---|---|---|---|
| `MEMORY_DATABASE` | `AETHEROS_MEMORY_DATABASE` | `MEMORY_DATABASE` | `memory.db` | non-empty; relative → under `DATA_DIR` |
| `MEMORY_VECTOR_PROVIDER` | `AETHEROS_MEMORY_VECTOR_PROVIDER` | `MEMORY_VECTOR_PROVIDER` | `hashing` | — (unknown → loud hashing fallback) |
| `MEMORY_EMBEDDING_MODEL` | `AETHEROS_MEMORY_EMBEDDING_MODEL` | `MEMORY_EMBEDDING_MODEL` | `""` | passed to a real provider; ignored by hashing |
| `MEMORY_EMBEDDING_DIM` | `AETHEROS_MEMORY_EMBEDDING_DIM` | `MEMORY_EMBEDDING_DIM` | `256` | `16 ≤ n ≤ 4096` |
| `MEMORY_RETRIEVAL_LIMIT` | `AETHEROS_MEMORY_RETRIEVAL_LIMIT` | `MEMORY_RETRIEVAL_LIMIT` | `5` | `1 ≤ n ≤ 100` |
| `MEMORY_SIMILARITY_THRESHOLD` | `AETHEROS_MEMORY_SIMILARITY_THRESHOLD` | `MEMORY_SIMILARITY_THRESHOLD` | `0.0` | `0.0 ≤ x ≤ 1.0` |
| `MEMORY_DECAY_ENABLED` | `AETHEROS_MEMORY_DECAY_ENABLED` | `MEMORY_DECAY_ENABLED` | `true` | bool |
| `MEMORY_DECAY_HALFLIFE_DAYS` | `AETHEROS_MEMORY_DECAY_HALFLIFE_DAYS` | `MEMORY_DECAY_HALFLIFE_DAYS` | `30.0` | `> 0` |
| `MEMORY_CONSOLIDATION_ENABLED` | `AETHEROS_MEMORY_CONSOLIDATION_ENABLED` | `MEMORY_CONSOLIDATION_ENABLED` | `true` | bool |
| `MEMORY_DEDUP_THRESHOLD` | `AETHEROS_MEMORY_DEDUP_THRESHOLD` | `MEMORY_DEDUP_THRESHOLD` | (see settings) | `0.0 ≤ x ≤ 1.0` |
| `MEMORY_MAX_WORKING_CONTEXT` | `AETHEROS_MEMORY_MAX_WORKING_CONTEXT` | `MEMORY_MAX_WORKING_CONTEXT` | (see settings) | int |
| `MEMORY_AUTO_REMEMBER` | `AETHEROS_MEMORY_AUTO_REMEMBER` | `MEMORY_AUTO_REMEMBER` | (see settings) | bool; off = recall+manual only, no auto writes |
| `MEMORY_AGENT_RECALL_LIMIT` | `AETHEROS_MEMORY_AGENT_RECALL_LIMIT` | `MEMORY_AGENT_RECALL_LIMIT` | (see settings) | int |
| `MEMORY_AGENT_RECALL_MIN_SCORE` | `AETHEROS_MEMORY_AGENT_RECALL_MIN_SCORE` | `MEMORY_AGENT_RECALL_MIN_SCORE` | (see settings) | float |
| `MEMORY_AGENT_RECALL_MAX_CHARS` | `AETHEROS_MEMORY_AGENT_RECALL_MAX_CHARS` | `MEMORY_AGENT_RECALL_MAX_CHARS` | (see settings) | int |

Config rejection verified: out-of-range `MEMORY_EMBEDDING_DIM=8`,
`MEMORY_SIMILARITY_THRESHOLD=2.0`, `MEMORY_RETRIEVAL_LIMIT=0`, and
`MEMORY_DECAY_HALFLIFE_DAYS=0` are all rejected by pydantic at construction.

## 3. `EMBEDDING_*` vs `MEMORY_EMBEDDING_*` reconciliation

**Finding (verified by search of `src/aetheros/**`):** there is **no bare
`EMBEDDING_*` convention anywhere in the codebase.** The only embedding settings
are the memory-scoped `MEMORY_EMBEDDING_MODEL` and `MEMORY_EMBEDDING_DIM` (with
`AETHEROS_MEMORY_EMBEDDING_*` aliases).

**Decision:**
- **Canonical names:** `MEMORY_EMBEDDING_MODEL`, `MEMORY_EMBEDDING_DIM` (and their
  `AETHEROS_`-prefixed forms, which take precedence).
- A top-level `EMBEDDING_MODEL` / `EMBEDDING_DIM` convention is **not introduced**.
  Creating one would produce exactly the ambiguity the contract warns against
  (which wins? what is the precedence?). The memory-scoped names are already
  namespaced and unambiguous.
- If a future, non-memory embedding consumer (e.g. a RAG/document subsystem)
  needs embeddings, it should define its **own** namespaced settings rather than
  a bare `EMBEDDING_*`, so there is never a shared, ambiguous global.
- **No deprecations are declared** because there is no legacy bare name in use to
  deprecate. This is recorded explicitly so a later phase does not "reconcile" a
  convention that never existed.

## 4. Precedence summary

For any memory field, the resolution order is:
1. `AETHEROS_MEMORY_<NAME>` environment variable (highest).
2. `MEMORY_<NAME>` environment variable (alias).
3. Field default in `Settings`.

Then `MemoryConfig.from_settings(settings)` copies the resolved values into the
immutable `MemoryConfig` the subsystem actually uses.

## 5. Enabled / disabled behaviour (startup)

- `ENABLE_MEMORY=false`: subsystem absent (see §1). Deterministic, no fake data.
- `ENABLE_MEMORY=true`: `MemoryManager.initialize()` connects SQLite and migrates
  the schema. DB/schema failure is a **hard** failure (durable store required).
- Embedding backend selection degrades (unknown name → hashing). This silent
  fallback is acceptable **only** while hashing is the sole shipped backend; the
  architecture doc (§3.1/§5) specifies the loud strict-vs-degrade policy required
  once a real provider exists.
