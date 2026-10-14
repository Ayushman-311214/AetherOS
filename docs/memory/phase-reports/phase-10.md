# PHASE 10 — EPISODIC MEMORY FOUNDATION

Status: DONE

## Starting revision and working-tree summary

- HEAD: `b0a2537` ("Initialize memory system"), branch `development`.
- Working tree carries uncommitted work from Memory phases 1–9 plus separate
  Trading-owned changes. No worktrees in use.
- Concurrent-agent classification of files I touched:
  - **Memory-owned**: `src/aetheros/memory/services/episodes.py` (new WIP
    completed), `.../services/manager.py`, `.../services/__init__.py`,
    `.../domain/episode.py`, `.../domain/__init__.py`, `.../config.py`,
    `tests/memory/test_episodic_memory.py` (new),
    `tests/memory/test_embedding_provider.py`, `docs/memory.md`,
    `docs/memory/*`.
  - **Shared (Core)**: `src/aetheros/config/settings.py` — one additive field.
- No Trading/Agent/Planner/Desktop/Vision file modified.

## Scope

Establish the explicit episode lifecycle foundation: start, action/observation
append, failure/recovery links, finalization and retrieval — capturing goal,
task/session IDs, timestamps, tool calls, observations, outcome, duration,
relevant memories and provenance, with sensitive inputs/results redacted before
persistence. Reuse actual event contracts (`MemoryStored` via the existing
writer path); no second bus; no invented delivery guarantees. Handle
duplicates, late/out-of-order events, partial tasks, interruption, restart and
repeated finalization without duplicate episodes. Keep summaries attributable
(rebuilt from stored steps, never invented). Phase 22 later validates
automatic coverage across the full integrated lifecycle — this phase is the
functionality, not the coverage proof.

## Existing implementation reused

- `Episode` / `ActionRecord` / `Outcome` value objects + `to_memory()`
  projection + `MemoryManager.store` (idempotency keys) / `update`
  (optimistic version guard) / `get` / `link` verbs — extended, not replaced.
- `ManagerAgentMemory` single-shot recording (`remember_episode`) — unchanged;
  its rows read back through the recorder (compat test).
- `redact_text` (secret-span scrubbing) + `redact_keys` / `safe_preview`
  (forbidden-key redaction, length bounding) — reused as-is.
- `WriteResult` five-state outcomes, `MemoryConfig.from_settings` /
  `for_memory_db`, settings `Field` + `AliasChoices` convention — all reused.
- The pre-existing WIP `services/episodes.py` skeleton was completed (not
  discarded): its lifecycle shape, docstring contract and test-facing API
  were kept; three bugs fixed (see below).
- No new EventBus, event class, storage table, or persistence path introduced.

## Changes implemented

- `domain/episode.py`: new `EpisodeObservation` value object (key/content/
  observed_at, lossless round-trip); `Episode` gains `observations`,
  `relevant_memories`, `provenance` (all in `to_dict`/`from_dict`);
  `to_memory()` stamps `episode_id` metadata + merges provenance into source
  detail (so rows are findable by episode id and carry their channel).
- `services/episodes.py` (`EpisodeRecorder`, constructed once by the manager):
  - Start via `store(..., idempotency_key=episode_id)`; idempotent replays
    return the stored episode; FAILED raises `MemoryStorageError` (never
    masquerades as success); disabled/uninitialized/policy-declined returns
    unsaved (honest no-op, recognisable by absent row).
  - Appends deduplicated (`(name, started_at)` / `(key, observed_at)`),
    re-sorted chronologically on write+read, version-guarded with 3 bounded
    retries; post-finalize appends keep outcome/`ended_at`.
  - `attach_failure` short-circuits repeats *before* creating the graph link
    (no duplicate link rows); same `derived_from`/`failure_in_episode`
    contract as the agent integration.
  - `finalize_episode` idempotent (same status writes nothing — version
    unchanged); different status updates the single row in place; lessons
    deduplicated; `ended_at` from the clock.
  - Retrieval: `get_episode` (never raises — missing/non-episode/deleted/
    corrupt reads as absent); `list_episodes` scoped by task/session + status
    + incomplete toggle + limit; `list_incomplete` pages in bounded batches.
  - `_mutate` returns `(episode, did_write)` so callers know whether a write
    happened; `_cap_actions` enforces the bound, oldest-first, counted in
    `truncated_actions` row metadata.
- `services/manager.py`: constructs `EpisodeRecorder(self, self._repo,
  max_actions=config.episode_max_actions)`; new `episodes` accessor.
  `remember_episode` unchanged.
- `services/__init__.py`: export `EpisodeRecorder`.
- `domain/__init__.py`: export `EpisodeObservation`.
- `memory/config.py`: additive `episode_max_actions` in both factories
  (default 200).
- `config/settings.py` (shared, additive): `MEMORY_EPISODE_MAX_ACTIONS`
  (default 200, 1–10000).
- `tests/memory/test_embedding_provider.py`: helper updated for the new
  config field (same as Phase 9's `working_ttl_seconds` fix).

## Files added

- `tests/memory/test_episodic_memory.py` (21 tests).
- `docs/memory/phase-reports/phase-10.md` (this report).

## Files modified

- `src/aetheros/memory/services/episodes.py`
- `src/aetheros/memory/services/manager.py`
- `src/aetheros/memory/services/__init__.py`
- `src/aetheros/memory/domain/episode.py`
- `src/aetheros/memory/domain/__init__.py`
- `src/aetheros/memory/config.py`
- `src/aetheros/config/settings.py` (shared, additive)
- `tests/memory/test_embedding_provider.py` (helper updated for new config field)
- `docs/memory.md`, `docs/memory/implementation-state.md`

## Shared files touched and justification

- `src/aetheros/config/settings.py`: one additive `MEMORY_EPISODE_MAX_ACTIONS`
  field following the existing memory-settings pattern (default preserves
  prior behaviour — nothing expires or is capped that wasn't before). Smallest
  compatible change; no existing field altered.

## Concurrent changes observed

Pre-existing uncommitted Memory (phases 1–9) and Trading changes present at
phase start; none within the regions I edited beyond my own prior-phase work.
The WIP `services/episodes.py` skeleton predates this phase (untracked file);
I completed it rather than replacing it.

## Migrations and compatibility impact

No schema migration (episodes ride the existing `memory_items` /
`memory_links` tables). All new `Episode` fields default to empty; old rows
(without `observations` / `relevant_memories` / `provenance`) parse via
`from_dict` defaults — covered by the single-shot compat test (an
agent-integration-style row reads back fine). `MemoryConfig` gains a required
field: the one direct-construction test helper needed it (updated); all other
construction goes through the two factories. No public API removed:
`remember_episode`, `Episode.summary()`, `to_dict()`/`from_dict()` shapes are
superset-compatible (new keys only).

## Commands executed and exit statuses

- `python --version` → exit 0 (`Python 3.13.15`).
- `python -m pytest tests/memory/test_episodic_memory.py -o addopts="" -q` →
  exit 0 (**21 passed**). NOTE: this phase's count is 21, not 22 — the "22"
  in earlier drafts was an off-by-one in documentation, not a missing test
  (collect-only confirms exactly the 21 tests listed below).
- `python -m pytest tests/memory -o addopts="" -q` → exit 0 (**202 passed,
  4 skipped**: prior 181 + 21 new, 0 failed).
- `ruff check` on all touched files → only pre-existing repo-wide `UP017`
  (`timezone.utc` vs `datetime.UTC`) in `domain/episode.py`, matching the
  convention `_clock.py` carries at HEAD (verified pre-existing via stash;
  left as-is). Four new-code findings (unsorted imports, `Callable` from
  `typing`, unused import) auto-fixed with `ruff check --fix`; suite
  re-run green after the fix.
- Settings/config load check → `MEMORY_EPISODE_MAX_ACTIONS` resolves to
  `200` via `MemoryConfig.from_settings` (exit 0).
- `mypy`: unavailable in env (`No module named mypy`), same as prior phases.

## Tests passed / failed / skipped / not run

- New file: **21 passed**, 0 failed, 0 skipped.
- Full memory suite: **202 passed, 4 skipped**, 0 failed. (Before this phase:
  181 passed / 4 skipped; delta = +21 new tests.)
- Not run: suites outside `tests/memory` (out of scope; only an additive
  shared settings field was touched, exercised via the load check above).
- New tests written (21), mapping to the contract acceptance areas:
  - Persistence/chronology: `test_full_lifecycle_persists_everything`,
    `test_out_of_order_appends_reconstruct_chronologically`,
    `test_late_append_after_finalize_keeps_outcome`.
  - Idempotency: `test_duplicate_start_returns_existing_without_duplicating`,
    `test_duplicate_action_delivery_is_noop`,
    `test_duplicate_observation_delivery_is_noop`,
    `test_repeated_finalization_writes_nothing`,
    `test_refinalize_with_different_status_updates_single_row`,
    `test_finalize_lessons_deduplicated`.
  - Links: `test_attach_failure_links_and_lists`,
    `test_attach_failure_missing_episode_or_failure_raises`.
  - Scope/retrieval: `test_scope_isolation`,
    `test_status_filter_and_incomplete_toggle`,
    `test_get_episode_degrades_to_none`.
  - Restart: `test_restart_lists_incomplete_and_resumes` (real file DB,
    fresh manager handle).
  - Bounds: `test_action_cap_drops_oldest_and_counts`,
    `test_list_limit_is_bounded`.
  - Redaction: `test_sensitive_arguments_and_summaries_redacted`,
    `test_secret_in_goal_is_scrubbed_and_labelled`.
  - Disabled: `test_disabled_mode_persists_nothing`.
  - Compat: `test_single_shot_episode_readable_via_recorder`.

## Baseline failures and evidence

None. The suite is green (21 new + full 202 passed / 4 skipped). The only
ruff finding on touched files is the pre-existing repo-wide `UP017` style
(evidenced at HEAD via stash comparison, left untouched). The `__import__`
hack flagged in earlier drafts was simplified to a top-level `MemoryType`
import before the green run. Carried forward: Finding #1 (full
authz/redaction/export no-leak layer); `datetime.utcnow()` deprecation
cosmetic (visible in test warnings, pre-existing).

## Required acceptance evidence

SATISFIED — all four verification commands green (see "Commands executed"):

1. `test_episodic_memory.py`: 21 passed. ✅
2. Full `tests/memory`: 202 passed, 4 skipped, 0 failed. ✅
3. `ruff check`: clean apart from pre-existing UP017. ✅
4. Settings load: `MEMORY_EPISODE_MAX_ACTIONS` → 200. ✅

## Security and operational concerns

- Redaction happens *before* persistence on every recorder input (arguments,
  goal, summaries, errors, lessons, provenance, environment) — pinned by two
  dedicated tests asserting secrets never reach the stored blob.
- Summaries are derived, never authored: `content` is rebuilt from stored
  steps on every mutation, so retrieval can never surface an invented step.
- No second bus/event contract: episode writes announce via the existing
  `MemoryStored` path — no new subscriber surface, no unverified delivery
  claims.
- Bounded retries (3), bounded listings (limit + 10×100 page cap), bounded
  actions (config knob, counted truncation) — no unbounded growth path.
- FAILED writes raise; SKIPPED-policy writes return unsaved; disabled returns
  unsaved — no phantom success anywhere.

## Remaining work

1. Optional: wire a periodic `list_incomplete`-based resume nudge into the
   maintenance loop (Phase 22 territory — not this phase).
2. Carried forward: Finding #1 (authz/redaction/export no-leak layer);
   UP017 style; `datetime.utcnow()` cosmetic.

## Exact next-phase handoff

Phase 10 is **DONE** (suite green: 21 new tests, full memory suite 202
passed / 4 skipped). Re-read the contract, `implementation-state.md` (§Phase
10 handoff), this report, and the live `episodes.py` / `manager.py` source
before the next phase. Phase 22 (automatic lifecycle coverage) can build on
`manager.episodes` as the recording seam. Key identifiers: `EpisodeRecorder`,
`manager.episodes`, `MemoryConfig.episode_max_actions`, settings
`MEMORY_EPISODE_MAX_ACTIONS`, `EpisodeObservation`.

PHASE 10 — DONE
