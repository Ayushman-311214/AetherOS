# Signal Engine — Evidence Model

How the engine aggregates evidence and what each item explains.

## The ledger

`EvidenceLedger` holds every `Evidence` item the sources produced plus a
`MissingSource` for each expected source that supplied none. It answers in one
pass: *what was observed, what was against it, and what was missing.*

Each `Evidence` item already carries the spec's full explanation contract:

- **WHAT** was observed — `type` + `detail` ("buy-side replenishment near
  25,120").
- **WHEN** — `created_at` + the observation's own bar time in `data`.
- **SOURCE** — `provenance.source` + `tier` (+ `is_mock`).
- **STRENGTH** — `weight` (0..1).
- **DIRECTION** — `direction` (UP/DOWN/SIDEWAYS/UNKNOWN).
- **CONFIDENCE** — `confidence` (LOW/MEDIUM/HIGH, a band not a probability).
- **WHY it matters** — `assertion` (OBSERVED/CALCULATED/DETECTED/INFERRED) +
  `data` payload.
- **LIMITATIONS** — `is_reliable` gate + `quality`/`limitations` (a mock or
  stale or inferred item can't tip a direction).

## Aggregation rules

- **Only reliable evidence moves the score.** `is_reliable` = usable ∧
  non-mock ∧ OBSERVED/CALCULATED/DETECTED. Unreliable items are listed but
  weighted zero — a synthetic or thin claim can never tip a direction.
- **Supporting vs contradicting** — split by the fused direction. Both are
  carried; the engine never hides disagreement.
- **Missing is explicit.** A source that supplied nothing is a `MissingSource`
  counting toward `coverage` — never a neutral vote, never silently dropped.

## Feature vectors become evidence

`features_to_evidence` converts `MarketFeatures`, `LiquidityFeatures` and
heatmap cells into `Evidence` items with an `EvidenceType` and a direction —
so a quantitative feature is recorded *as* a traceable claim, not a number
silently folded into a direction it didn't vote for. A neutral/absent read
produces a SIDEWAYS/UNKNOWN item or nothing, never a fabricated lean.

## Coverage

`coverage = supplied / expected` — the share of expected sources that actually
arrived. It feeds confidence: a read resting on half its expected evidence is
honestly thinner than one resting on all of it.
