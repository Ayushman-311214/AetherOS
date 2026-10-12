# PHASE 05 — REAL EMBEDDING PROVIDER (OLLAMA) + EMBEDDING-SPACE IDENTITY

Status: DONE

## Starting revision and working-tree summary

- Baseline commit: `b0a2537` ("Initialize memory system").
- The working tree already carried uncommitted Phase 1–4 Memory work and
  substantial **concurrent Trading-agent** changes (trading providers/services,
  `settings.py` trading knobs, graphify-out, logs). Nothing was committed; Phase 5
  began on top of this live tree.
- Pre-existing (not mine): all `src/aetheros/trading/**`, the trading `settings.py`
  fields (`TRADING_*`), graphify artifacts, run logs. Classified Trading-owned /
  shared and left untouched except the two additive memory fields in `settings.py`.

## Scope

Add the first real semantic embedding provider (Ollama) behind the existing
`EmbeddingProvider` ABC, with embedding-space identity enforcement so vectors
from different models are never mixed in one query. Honesty policy: a requested
real provider is never silently replaced by hashing.

## Existing implementation reused

- `EmbeddingProvider` ABC + `HashingEmbeddingProvider` (Phase 1).
- `build_embedding_provider` factory (Phase 1) — extended, not replaced.
- `memory_embeddings.model` column (Phase 2) — already persists per-vector
  identity; reused as the identity filter key. **No schema/migration change.**
- `VectorIndex` store/search (Phase 1), `MemoryWriter.reindex` + projection
  verify/repair (Phase 4).
- The trading Yahoo provider's HTTP conventions (injected `httpx.AsyncClient`,
  bounded timeout, transient/permanent split, injected sleeper) as the pattern
  for `OllamaEmbeddingProvider`.
- `MemoryConfig` / `settings.py` configuration + `AliasChoices` convention.
- `EmbeddingError` (`core/errors/memory_error.py`).

## Changes implemented

- `OllamaEmbeddingProvider`: `POST /api/embeddings`, `ensure_ready()` validates
  daemon + model presence + real embedding capability and probes the true
  dimension, `name = ollama:<model>:<dim>`, validated normalised float32 vectors,
  bounded retries w/ exponential backoff on transient failures only, errors carry
  no prompt text.
- ABC: `embed_batch` (order/cardinality contract) + `embed_many` alias +
  `validate_vector` static guard.
- Factory: wires `ollama`; strict-by-default, loud `MEMORY_EMBEDDING_FALLBACK`
  degrade; unknown provider => `EmbeddingError`.
- `VectorIndex`: search filters on active identity (`model` column); `identities()`.
- `MemoryManager`: `_ensure_embedder_ready()` (strict/degrade) + foreign-identity
  startup warning wired into `initialize()`; `embedding_identities()`;
  `reembed_all()`; dimension-safe `stats()`.
- Config: `MEMORY_EMBEDDING_BASE_URL`, `MEMORY_EMBEDDING_FALLBACK` (additive).

## Files added

- `src/aetheros/memory/embeddings/ollama.py`
- `tests/memory/test_embedding_provider.py`
- `docs/memory/phase-reports/phase-05.md` (this file)

## Files modified

- `src/aetheros/memory/embeddings/base.py`
- `src/aetheros/memory/embeddings/__init__.py`
- `src/aetheros/memory/vector/index.py`
- `src/aetheros/memory/services/manager.py`
- `src/aetheros/memory/config.py`
- `src/aetheros/config/settings.py` (shared — see below)
- `pyproject.toml` (shared, root — marker only)
- `docs/memory/architecture.md`, `docs/memory/implementation-state.md`

## Shared files touched and justification

- `src/aetheros/config/settings.py`: added only `MEMORY_EMBEDDING_BASE_URL` and
  `MEMORY_EMBEDDING_FALLBACK`, inserted inside the existing `MEMORY_*` block,
  following the file's `Field(... AliasChoices(...))` convention. Re-read the
  live (Trading-mid-edit) file before editing; the edit applied cleanly without
  touching any `TRADING_*` field.
- `pyproject.toml`: registered the `real_embeddings` pytest marker only; no other
  key changed.

## Concurrent changes observed

Active Trading-agent edits throughout `src/aetheros/trading/**`, additional
`TRADING_*` fields in `settings.py`, new `graphify-out/2026-10-06|07/` artifacts
and run logs. None overlap Memory-owned code. No reconciliation conflict.

## Migrations and compatibility impact

None. The `model` identity column already existed. Existing hashing-provider
behavior is unchanged (default path untouched). All additions are backward
compatible: new config fields default to the prior behavior, `embed_many` keeps
working as an alias, and identity filtering is a no-op for a single-identity
index (the only kind the hashing default produces).

## Commands executed and exit statuses

- `curl /api/tags`, `curl /api/embeddings` (manual daemon probe) — exit 0;
  confirmed daemon up, model `llama3:latest`, dim 4096, raw (un-normalised) vectors.
- `python -m pytest tests/memory/test_embedding_provider.py -q` — exit 0.
- `AETHEROS_MEMORY_TEST_OLLAMA=1 AETHEROS_MEMORY_TEST_OLLAMA_MODEL=llama3:latest
  python -m pytest tests/memory/test_embedding_provider.py -m real_embeddings -q -s`
  — exit 0.
- `python -m pytest tests/memory -o addopts=""` — exit 0.

## Tests passed / failed / skipped / not run

- `test_embedding_provider.py` default run: **20 passed, 2 skipped** (the opt-in
  real tests auto-skip without the env var).
- Real-provider run (`-m real_embeddings`, env set): **2 passed**.
- Full memory suite (`tests/memory`): **108 passed, 2 skipped** (the opt-in real
  tests, deselected/skipped by default), 0 failed.
- Not run this phase: `tests/agents`, trading suites, full repo suite (out of
  scope; see baseline-failures note).

## Baseline failures and evidence

None observed within `tests/memory`. The known ~22 environmental full-suite
failures recorded in prior phases are outside the memory package and were not
re-exercised here; this report does **not** claim the whole repo regression
suite passed.

## Required acceptance evidence

Real-provider integration (contract §5.4) — **captured** with user authorization,
using an already-running Ollama daemon and a pre-installed model (no download):

```
[real] model=llama3:latest dim=4096 identity=ollama:llama3:latest:4096
[real] identities={'ollama:llama3:latest:4096': 2}
```

- `test_real_ollama_embed_identity_and_dimension`: real embed, probed dim 4096,
  identity `ollama:llama3:latest:4096`, unit-norm vector. PASSED.
- `test_real_ollama_semantic_retrieval_end_to_end`: real embeddings + real SQLite
  (`:memory:`) + real cosine search; query "central bank interest rate hike"
  ranked the RBI/repo-rate memory first over an unrelated memory; index held a
  single uniform identity. PASSED.

## Security and operational concerns

- Errors never include the embedded text payload (asserted by
  `test_exhausted_retries_raise_without_leaking_prompt`).
- Identity filtering prevents cross-model blending in retrieval.
- `llama3:latest` is a chat model used here only to exercise the real embeddings
  endpoint and prove the path; a dedicated embedding model (e.g. nomic-embed-text,
  mxbai-embed-large) is recommended for production retrieval quality. The code is
  model-agnostic — set `MEMORY_EMBEDDING_MODEL` accordingly.
- Soft-deleted / historical no-leak across cache / graph expansion / export is
  still owed by the later authorization phase (Finding #1); this phase closed only
  the incompatible-embedding-mixing gap.

## Remaining work

- Automatic reembed-on-identity-change (only manual `reembed_all()` + a loud
  startup warning exist now).
- Finding #1 authorization/scope/deletion-visibility layer across retrieval,
  cache, embedding, graph expansion, export.
- Graph-side projection rebuild/repair (counterpart to Phase 4 vector repair).

## Exact next-phase handoff

Phase 5 is DONE. The memory subsystem now has a real, identity-safe embedding
provider with strict/loud-degrade policy and an explicit re-embed migration.
Next candidates (unchanged priority): Finding #1 full authorization layer, then
graph-side repair, then auto-migration on embedding-identity change. Re-read
`agent-contract.md`, `implementation-state.md`, this report, and the live source;
re-run the concurrent-agent audit before starting.

PHASE 05 — DONE
