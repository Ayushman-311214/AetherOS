# PHASE 03 — MEMORY DOMAIN MODELS

Status: DONE

## Starting revision and working-tree summary

- Branch `development`, HEAD `b0a2537` ("Initialize memory system").
- Concurrent audit (git status at phase start): the Trading agent's uncommitted
  work spans `src/aetheros/trading/**`, `graphify-out/**`, and the two shared
  files `bootstrap/bootstrapper.py` and `config/settings.py`. **No overlap with
  Memory-owned paths.** Pre-existing Memory-area change: `storage/database.py`
  (Phase 2) and the `docs/memory/**` control dir.
- Memory domain files were all present and unmodified at phase start.

## Scope

Phase 3 only: the memory **domain models**. Audit the requested record set
against the existing domain layer, close genuine gaps with the smallest coherent
change, and prove the model behaviour (serialisation round-trips, boundaries,
immutability, content safety) with a dedicated test file. No service/storage
behaviour change beyond wiring the content-safety foundation into the validator.

## Existing implementation reused

**All requested domain types already existed** (built pre-Phase 0). Mapping to
the contract's literal names:

| Requested | Existing type(s) |
|---|---|
| MemoryRecord | `domain/memory.py::Memory` (universal row) |
| WorkingMemory | `services/working_memory.py` (service over `Memory`) |
| SemanticMemory | `domain/semantic.py::Entity`, `Relationship` |
| EpisodicMemory | `domain/episode.py::Episode`, `ActionRecord`, `Outcome` |
| ProceduralMemory | `domain/procedure.py::Procedure`, `ProcedureStep` |
| PreferenceMemory | `domain/preference.py::Preference` |
| FailureMemory / RecoveryMemory | `domain/preference.py::FailureRecord` (failure + recovery fields) |
| TradingMemory | `domain/trading.py::PredictionMemory` (immutable) + `PredictionOutcomeMemory` (append-only) |
| MemoryRelationship | `domain/memory.py::MemoryLink` (memory↔memory) + `Relationship` (entity↔entity) |
| MemoryMetadata / provenance | `domain/memory.py::MemorySource` + `Memory.metadata` |

All already have: tz-aware timestamps, `[0,1]` confidence clamping, lossless
`to_dict`/`from_dict` with legacy-tolerant `.get(...)` defaults, versioning,
lifecycle status/scope, and evidence-gated (not asserted) procedure confidence.

So Phase 3 is **complete/harden**, not build-new.

## Changes implemented

The one genuine unmet contract ask was the content-safety foundation ("security
foundations must exist from the first write path") and the absence of a dedicated
domain-model test file.

- Added `ContentPolicy` + secret scanner/redactor as pure domain functions.
- Wired them into `MemoryValidator` (the single write-path gate): size limits
  enforced; secrets redacted-in-place (recorded in
  `metadata["redacted_secret_kinds"]`) or rejected, per policy.
- Added the domain-model acceptance test file.

## Files added

- `src/aetheros/memory/domain/content_policy.py` (Memory-owned).
- `tests/memory/test_domain_models.py` (28 tests).

## Files modified

- `src/aetheros/memory/services/validator.py` — enforce `ContentPolicy`
  (optional ctor arg, default `ContentPolicy()`; back-compatible).
- `src/aetheros/memory/domain/__init__.py` — export content-policy symbols.
- `docs/memory.md` — new "Content safety (write-path foundation)" section.
- `docs/memory/implementation-state.md` — Phase 3 ledger + decisions + handoff.

## Shared files touched and justification

None. `bootstrapper.py` / `settings.py` not touched. Content/payload limits live
in the domain (`ContentPolicy`), deliberately **not** in `settings.py`, to avoid
editing the shared, Trading-mid-edit config file (same rationale as Phase 2).

## Concurrent changes observed

Unchanged from Phase 2: Trading agent's uncommitted work in `trading/**`,
`graphify-out/**`, and the two shared files. No overlap with Memory-owned paths
during this phase.

## Migrations and compatibility impact

None. No schema/migration change; `LATEST_VERSION` unchanged. `Memory.to_dict()`
keys are unchanged, so `MemoryRepository` round-trips and all persisted rows stay
compatible — asserted by `test_memory_to_dict_has_every_field_the_repository_reads`.
`MemoryValidator()` with no args behaves as before (default policy); the new
behaviour (redaction/limits) only triggers on oversize or secret-bearing content.

## Commands executed and exit statuses

1. `python -m pytest tests/memory/test_domain_models.py -q` — exit 0, **28 passed**.
2. `python -m pytest tests/memory tests/cli/test_memory_command.py tests/agents/test_agent_memory_integration.py` — exit 0, **89 passed, 9 warnings**.
3. Inline smoke test of redact/reject/limits — exit 0 (redaction + reject verified).

(All commands run with `PYTHONPATH=src`. Every test uses `:memory:`/`tmp_path`;
no real user DB touched.)

## Tests passed / failed / skipped / not run

- Passed: 89 (28 new domain-model tests + 61 prior memory/CLI/agent tests).
- Failed: 0. Skipped: 0. Deselected: 0. Timed out: 0.
- Not run this phase: the rest of the full repo suite (unchanged by this phase;
  Memory changes are additive and import-isolated).

## Baseline failures and evidence

None introduced. Per the recorded baseline the full repo suite has ~22
pre-existing environmental failures outside Memory; this phase did not re-run or
rely on that claim, and touched no files outside the Memory subsystem + its docs.

## Required acceptance evidence

- Lossless round-trip for every record type (Memory, Episode, Procedure,
  Preference, FailureRecord, Prediction/Outcome, Entity, Relationship, MemoryLink).
- Malformed input: missing `content` → `KeyError`; unknown future field ignored;
  legacy row without `version`/`evidence_count` defaults cleanly.
- Boundaries: confidence clamped at 0.0 and 1.0; blank content rejected.
- Immutability/separation: outcome is a distinct record referencing the
  prediction by id; creating it leaves the prediction untouched; both carry the
  correct veracity (PREDICTION vs OBSERVATION, never FACT).
- Content safety: oversize content/payload rejected; secret redacted by default
  (and recorded), rejected in REJECT mode, preserved in ALLOW mode.
- No real-provider/embedding evidence required for a pure-domain phase.

## Security and operational concerns

- The secret scanner is a conservative **foundation**, not exhaustive DLP; tuned
  against false-positives on trading prose. Default REDACT keeps durable writes
  succeeding while the credential never reaches SQLite/vector/events.
- Still unbuilt (next phase): full authorization / scope-filtering / deletion-
  visibility / sensitive-exclusion across retrieval, cache, embedding, graph
  expansion and export (finding #1). Phase 3 covered only the write-path content
  foundation of that larger layer.

## Remaining work

- Finding #1 full authorization/redaction layer across all read/derived paths.
- Projection rebuild/repair + embedding-identity expansion with a real provider.
- Cosmetic: `datetime.utcnow()` deprecation warning originating in `BaseError`.

## Exact next-phase handoff

Domain layer is complete and hardened. For the next authorized phase: re-read
`agent-contract.md`, `implementation-state.md`, this report, and the live source;
re-run the concurrent-agent audit; prefer Memory-owned, additive changes; the
content-safety foundation (`ContentPolicy`/`MemoryValidator`) is the extension
point for the broader authorization layer.

PHASE 03 — DONE
