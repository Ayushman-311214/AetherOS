# AetherOS — Production Memory System

## Master Implementation Prompt for Claude Code

You are the dedicated **Memory Systems Architect and Engineer** for AetherOS.

Your responsibility is to build, complete, test, integrate, and production-harden the **AetherOS Memory System**.

AetherOS is an autonomous Trading Intelligence and Decision Support System.

IMPORTANT:

> Trading Intelligence is being developed by ANOTHER Claude Code agent in the SAME repository at the same time.

You MUST assume that another agent is actively modifying Trading Intelligence code.

Your work must therefore be:

* additive
* modular
* backward compatible
* isolated
* conflict-aware
* production-oriented

DO NOT overwrite another agent's work.

DO NOT reset/revert unrelated changes.

DO NOT rebuild existing functionality from scratch.

DO NOT create fake/mock memory implementations merely to satisfy tests.

DO NOT claim completion without actually implementing and testing the functionality.

---

# 0. PRIMARY OBJECTIVE

Build a complete production-grade long-term Memory System for AetherOS.

The final Memory System must support:

1. Working Memory
2. Episodic Memory
3. Semantic Memory
4. Procedural Memory
5. Preference Memory
6. Failure / Recovery Memory
7. Trading Memory
8. Vector / Semantic Retrieval
9. Knowledge Graph
10. Hybrid Retrieval
11. Memory Consolidation
12. Confidence
13. Importance
14. Recency
15. Memory Decay
16. Lifecycle management
17. Provenance
18. Explainable retrieval
19. Automatic memory formation
20. Episode recording
21. Procedure learning
22. Agent integration
23. Planner integration
24. Trading Intelligence integration
25. Vision/Desktop contextual memory
26. Memory tools
27. CLI/debugging
28. Observability
29. Security/privacy controls
30. Testing
31. Performance
32. Production configuration

The system must use REAL persistence and REAL retrieval.

No fake memory.

No hardcoded retrieval responses.

No fake embeddings.

No "TODO" implementations pretending to work.

---

# 1. FIRST RULE — READ THE EXISTING MEMORY

Before writing ANY code:

Perform a complete repository audit.

You MUST inspect:

* existing Memory modules
* MemoryProvider
* MemoryManager
* memory services
* storage
* schemas
* migrations
* domain models
* vector code
* embeddings
* graph code
* retrieval
* episodic memory
* procedural memory
* trading memory
* memory tools
* configuration
* bootstrap
* CLI
* tests
* documentation
* agent integration
* planner integration
* event system
* Trading Intelligence interfaces

Also inspect Git status and recent changes.

Determine:

```text
What already exists?
What is complete?
What is partially implemented?
What is stubbed?
What is fake/mock?
What is production-ready?
What is missing?
What can be reused?
What must be replaced?
What must NOT be touched because another agent owns it?
```

Create an internal implementation map before making changes.

DO NOT start coding before understanding the current architecture.

---

# 2. EXISTING MEMORY MUST BE PRESERVED

If a Memory System already exists in the repository:

DO NOT rebuild it from scratch.

Extend and improve it.

For every existing memory component:

```text
KEEP
IMPROVE
REPLACE ONLY IF NECESSARY
DELETE ONLY WITH STRONG JUSTIFICATION
```

Before replacing anything, determine:

* who uses it
* which interfaces depend on it
* which tests depend on it
* whether persisted data depends on it
* whether migration is required

Existing persisted memory must never be silently destroyed.

---

# 3. PARALLEL CLAUDE AGENT SAFETY

Another Claude Code agent is simultaneously implementing Trading Intelligence.

Therefore:

## NEVER:

* git reset
* git clean
* checkout unrelated files
* revert unrelated changes
* rewrite Trading Intelligence
* rename unrelated modules
* mass-format the repository
* modify unrelated architecture
* overwrite files simply because they are unfamiliar

Before editing a file:

Determine whether it belongs to:

```text
Memory
Shared infrastructure
Trading Intelligence
Desktop
Vision
Agent
Planner
Core
```

If a file is actively used by Trading Intelligence:

prefer:

```text
new adapter
new interface
new integration layer
minimal compatible change
```

instead of rewriting the existing implementation.

If a conflict is detected:

STOP and analyze it.

Do not blindly overwrite.

---

# 4. ARCHITECTURAL PRINCIPLE

Memory must be a subsystem.

Trading Intelligence must consume Memory through interfaces.

Do NOT put memory internals directly inside Trading Intelligence.

Desired architecture:

```text
                    AetherOS
                       |
              +--------+--------+
              |                 |
       Trading Intelligence   Memory System
              |                 |
              |          +------+------+
              |          |             |
              |      Memory API    Memory Manager
              |          |             |
              |      Retrieval      Storage
              |          |             |
              |      +---+---+-------+
              |      |       |       |
              |    SQLite   Vector   Graph
              |              |
              |          Embeddings
              |
              +------ Memory Interface
```

Memory implementation details must remain hidden behind stable interfaces.

---

# 5. MEMORY TYPES

Implement/verify the following memory types.

## 5.1 Working Memory

Current:

* conversation
* task
* plan
* goal
* active application
* active screen
* current market state
* current symbols
* current timeframe
* active tools
* current observations

Working memory is short-lived.

---

## 5.2 Episodic Memory

Record:

```text
Goal
Task
Session
Start
End
Actions
Tool calls
Observations
Errors
Recovery
Outcome
Duration
Relevant memories
```

Example:

```text
User asked:
Open TradingView and inspect NIFTY 50.

Actions:
Open browser
Navigate TradingView
Select NIFTY
Select 15m timeframe
Capture chart

Outcome:
Successful
```

---

# 6. SEMANTIC MEMORY

Store durable facts and knowledge.

Examples:

```text
Entity
Fact
Concept
Relationship
Market concept
Trading concept
System knowledge
User-confirmed fact
```

Every semantic memory should have:

* source
* provenance
* confidence
* created_at
* updated_at
* importance
* validity
* version

---

# 7. PROCEDURAL MEMORY

Store reusable procedures.

Example:

```text
Procedure:
Open TradingView NIFTY analysis

Preconditions:
TradingView available

Steps:
1. Open browser
2. Navigate TradingView
3. Search NIFTY
4. Select timeframe
5. Capture chart
6. Analyze

Verification:
Chart visible

Success rate:
...
```

Procedures must be versioned.

Failures must be able to improve procedures.

---

# 8. FAILURE / RECOVERY MEMORY

Record:

```text
failure
cause
context
attempted recovery
result
successful alternative
related procedure
```

Example:

```text
Click coordinate failed
    ↓
Vision search attempted
    ↓
Vision succeeded
    ↓
Procedure updated:
prefer visual target detection
```

---

# 9. TRADING MEMORY

Trading memory must support:

```text
Prediction
Prediction timestamp
Instrument
Timeframe
Regime
Features
Evidence
Reasoning reference
Probability
Direction
Confidence
Risk/reward
Expected outcome
Actual outcome
Outcome timestamp
Calibration
```

IMPORTANT:

Historical predictions must remain immutable.

Never rewrite historical predictions because the market later changed.

Instead:

```text
Prediction
    ↓
Outcome
    ↓
Evaluation
    ↓
Calibration
```

---

# 10. REAL EMBEDDINGS

This is mandatory.

DO NOT implement a fake embedding system just to make retrieval work.

DO NOT use:

```text
random vectors
constant vectors
hashes pretending to be embeddings
hardcoded similarity
keyword score pretending to be vector similarity
```

A deterministic hashing embedder may ONLY exist as an explicitly documented development fallback if already present, but it MUST NOT be treated as production semantic retrieval.

Production configuration must use a REAL embedding model.

---

# 11. EMBEDDING PROVIDER ARCHITECTURE

Implement an abstraction:

```python
class EmbeddingProvider(ABC):
    async def embed(self, text: str) -> list[float]:
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    @property
    def dimension(self) -> int:
        ...
```

The system must support pluggable providers.

At minimum support:

### Local Ollama

Ollama may be used for local embeddings.

The provider must be configurable:

```text
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=<configured-model>
OLLAMA_BASE_URL=http://localhost:11434
```

Do NOT hardcode a model name.

Discover/validate the configured model.

The system must fail clearly if the configured embedding model does not exist.

---

# 12. FREE / LOCAL EMBEDDING SUPPORT

The architecture must allow free/local models.

Recommended production-capable approach:

```text
Provider
   ↓
Ollama
   ↓
Configured embedding model
```

Also allow future providers such as:

```text
SentenceTransformers
HuggingFace
OpenAI-compatible embedding APIs
Other local embedding servers
```

Do not tightly couple Memory to Ollama.

---

# 13. EMBEDDING VALIDATION

When an embedding provider starts:

Validate:

```text
model exists
embedding succeeds
dimension is stable
vector is finite
vector is non-empty
dimension matches index
```

If the embedding dimension changes:

DO NOT silently mix vectors.

Require an explicit index migration/rebuild.

---

# 14. VECTOR STORAGE

Use a real vector index.

The implementation may initially use an embedded/local vector index if appropriate for the existing architecture.

It must support:

```text
insert
update
delete
similarity search
batch insert
batch search
metadata filtering
```

Do not load the entire database into memory for every query once the production implementation is established.

---

# 15. SQLITE

SQLite should remain the authoritative structured memory store where appropriate.

Use it for:

```text
memory records
metadata
relationships
timestamps
confidence
importance
provenance
lifecycle
episodes
procedures
failures
outcomes
links
```

Use migrations.

Never destroy existing databases during development.

---

# 16. KNOWLEDGE GRAPH

Implement/retain a graph layer for:

```text
Entity → Relationship → Entity
```

Examples:

```text
NIFTY
   ↓
belongs_to
   ↓
Indian Market

NIFTY
   ↓
has_regime
   ↓
Trending

Procedure
   ↓
uses_tool
   ↓
Vision
```

Graph traversal should support memory retrieval.

Do not make the graph the only source of truth.

---

# 17. HYBRID RETRIEVAL

Memory retrieval must combine multiple signals.

Example:

```text
Query
 ↓
Structured filtering
 ↓
Vector similarity
 ↓
Graph expansion
 ↓
Recency
 ↓
Importance
 ↓
Confidence
 ↓
Task relevance
 ↓
Entity relevance
 ↓
Deduplication
 ↓
Ranking
 ↓
Context budget
```

Retrieval should produce an explanation.

Example:

```text
Retrieved memory because:

Semantic similarity: 0.91
Entity match: NIFTY
Task relevance: high
Recency: medium
Confidence: 0.94
Importance: high
```

---

# 18. CURRENT REALITY MUST WIN

Memory is historical context.

It must NOT override current reality.

Example:

Old memory:

```text
TradingView indicator at coordinate X,Y
```

Current screen:

```text
Indicator moved
```

The system must treat the old coordinate as historical context only.

Current:

* vision
* screen state
* market data
* API data
* live environment

must override stale memory.

---

# 19. MEMORY CONFIDENCE

Every memory must support confidence.

Example:

```text
confidence = 0.0 → 1.0
```

Confidence should depend on:

* source reliability
* repeated confirmation
* explicit user confirmation
* successful reuse
* contradictions
* age
* outcome

Do not blindly increase confidence because something was retrieved frequently.

---

# 20. MEMORY PROVENANCE

Every important memory should answer:

```text
Where did this come from?
```

Examples:

```text
user
agent
tool
vision
trading_api
document
episode
procedure
system
external_source
```

Store provenance.

---

# 21. MEMORY LIFECYCLE

Implement:

```text
ACTIVE
↓
STALE
↓
DECAYED
↓
ARCHIVED
```

Do not immediately delete old memories.

Support:

* TTL where appropriate
* importance
* recency
* decay
* archival
* soft deletion

Critical trading history must not be deleted by ordinary decay.

---

# 22. CONSOLIDATION

Memory consolidation must detect:

```text
duplicates
near duplicates
contradictions
outdated facts
related episodes
repeated procedures
```

Consolidation must preserve provenance.

Do not silently destroy historical evidence.

---

# 23. EPISODE → PROCEDURE LEARNING

Implement automatic procedural learning.

Flow:

```text
Episodes
   ↓
Successful repeated patterns
   ↓
Procedure candidate
   ↓
Validation
   ↓
Procedure memory
   ↓
Planner retrieval
   ↓
Procedure execution
   ↓
Outcome
   ↓
Procedure update
```

A procedure should not be created from one accidental successful action unless explicitly configured.

Use configurable confidence/repetition thresholds.

---

# 24. FAILURE-BASED PROCEDURE LEARNING

When a procedure fails:

```text
Procedure
    ↓
failed step
    ↓
failure reason
    ↓
recovery
    ↓
successful alternative
    ↓
procedure revision
```

Maintain procedure versions.

Never destroy the historical procedure version.

---

# 25. AGENT INTEGRATION

Memory must integrate with the existing Agent system.

Desired flow:

```text
User Goal
   ↓
Task
   ↓
Memory Recall
   ↓
Memory Context
   ↓
Planner
   ↓
Tool
   ↓
Observation
   ↓
Memory Update
   ↓
Next Step
   ↓
Final Outcome
   ↓
Episode
```

Memory retrieval failure should normally NOT crash the agent.

Memory must be degradable.

---

# 26. PLANNER INTEGRATION

Before planning:

retrieve relevant memory.

Pass a bounded context:

```text
MemoryContext
```

It must contain only relevant memories.

Do not dump the entire memory database into the LLM.

---

# 27. MEMORY CONTEXT BUDGET

Implement configurable limits:

```text
max_memories
max_tokens
max_chars
max_per_type
max_age
min_confidence
```

The planner should receive concise, relevant context.

---

# 28. TRADING INTELLIGENCE INTEGRATION

Another Claude agent is building Trading Intelligence.

DO NOT implement its internal trading algorithms.

Instead provide stable interfaces.

Memory should be capable of storing/retrieving:

```text
historical analysis
market regime
trading concepts
prediction history
prediction outcomes
calibration
strategy observations
successful/failed reasoning patterns
```

Use adapters where required.

If Trading Intelligence APIs do not yet exist:

create a clean integration interface.

DO NOT invent fake Trading Intelligence results.

---

# 29. AUTOMATIC MEMORY FORMATION

Memory should not depend on developers manually calling:

```python
memory.save(...)
```

for every event.

Where appropriate, use the existing EventBus.

Subscribe to meaningful events:

```text
TASK_CREATED
TASK_COMPLETED
TASK_FAILED
TOOL_EXECUTED
TOOL_FAILED
RECOVERY_COMPLETED
PREDICTION_CREATED
PREDICTION_EVALUATED
VISION_OBSERVATION
```

Use the repository's EXISTING event system.

DO NOT create a second event bus.

---

# 30. MEMORY DEDUPLICATION

Do not store the same memory repeatedly.

Deduplication should consider:

```text
content
semantic similarity
entity
source
time
memory type
```

Repeated observations may update an existing memory instead of creating thousands of duplicates.

---

# 31. MEMORY TOOLS

Provide safe tools for the Agent:

```text
remember
recall
search_memory
get_memory
update_memory
forget_memory
record_episode
record_failure
get_procedure
learn_procedure
memory_stats
```

Tools must use Memory APIs.

Do not expose raw SQLite/vector internals to the Agent.

---

# 32. USER CONTROL

Provide controls for:

```text
memory enabled/disabled
memory inspection
memory deletion
memory correction
memory export
memory statistics
```

User correction must have high authority.

---

# 33. PRIVACY / SECURITY

Memory may contain sensitive information.

Implement:

* provenance
* source tracking
* soft deletion
* access boundaries
* configurable retention
* redaction hooks
* safe logging
* no secret storage
* no API keys/passwords in memory
* no sensitive credentials embedded in embeddings

Never log raw secrets.

---

# 34. OBSERVABILITY

Provide metrics such as:

```text
memory writes
memory reads
retrieval latency
embedding latency
vector search latency
graph search latency
cache hits
cache misses
dedup rate
memory failures
retrieval failures
procedure success rate
```

Development mode should explain retrieval decisions.

---

# 35. TESTING — MANDATORY AFTER EVERY PHASE

This is extremely important.

After EVERY phase:

1. Run formatting/linting relevant to changed files.
2. Run targeted unit tests.
3. Run integration tests relevant to the phase.
4. Run the existing regression test suite where practical.
5. Inspect failures.
6. Fix failures caused by your work.
7. Re-run tests.
8. Verify no unrelated regressions were introduced.

DO NOT simply write tests and assume they pass.

Actually execute them.

---

# 36. AUTOMATIC PHASE VALIDATION

At the end of every phase, generate a phase validation report:

```text
PHASE X VALIDATION

Implemented:
...

Files changed:
...

Tests executed:
...

Tests passed:
...

Tests failed:
...

Failures caused by this phase:
...

Pre-existing failures:
...

Production concerns:
...

Remaining work:
...
```

If tests fail because of your implementation:

DO NOT mark the phase DONE.

Fix them first.

---

# 37. NO FAKE TESTS

Tests must not:

* mock the entire Memory subsystem
* mock embeddings just to claim semantic retrieval works
* return hardcoded memory results
* bypass persistence
* bypass vector search
* bypass graph search
* assert fake outputs

Mocks may be used ONLY at genuine external boundaries where appropriate.

At least one integration test must exercise:

```text
real persistence
real embedding provider
real retrieval
real memory lifecycle
```

when the environment supports it.

If a required external dependency is unavailable:

report the exact limitation.

Do not replace it with fake production behavior.

---

# 38. EMBEDDING TEST MODE

Tests must support two categories:

### Unit tests

Can use deterministic fixtures where appropriate.

### Production integration tests

Must use the configured real embedding provider.

Example:

```text
MEMORY_EMBEDDING_INTEGRATION_TESTS=true
```

When enabled:

```text
real model
real embedding
real vector index
real similarity search
```

No fake vectors.

---

# 39. CONFIGURATION

All production-sensitive settings must be configurable.

Examples:

```text
MEMORY_ENABLED
MEMORY_DATABASE_URL
MEMORY_VECTOR_BACKEND
MEMORY_EMBEDDING_PROVIDER
MEMORY_EMBEDDING_MODEL
MEMORY_EMBEDDING_DIMENSION
MEMORY_MIN_CONFIDENCE
MEMORY_MAX_RESULTS
MEMORY_CONTEXT_TOKEN_BUDGET
MEMORY_DECAY_ENABLED
MEMORY_CONSOLIDATION_ENABLED
MEMORY_AUTO_RECORD
MEMORY_AUTO_PROCEDURE_LEARNING
```

Do not hardcode environment-specific paths.

---

# 40. FAILURE BEHAVIOR

If Memory is unavailable:

AetherOS should still be able to operate where possible.

Example:

```text
Memory enabled
   ↓
database unavailable
   ↓
log clear error
   ↓
continue without memory if safe
```

But never silently pretend memory succeeded.

Distinguish:

```text
memory write succeeded
memory write skipped
memory write failed
```

---

# 41. PERFORMANCE

Do not optimize prematurely.

First make it correct.

Then measure.

Benchmark:

```text
1k memories
10k memories
50k memories
100k memories
```

where practical.

Measure:

```text
write latency
embedding latency
retrieval latency
vector search latency
graph traversal
hybrid retrieval
memory context generation
```

Do not claim scale readiness without measurements.

---

# 42. DOCUMENTATION

Maintain:

```text
docs/memory.md
```

Document:

* architecture
* memory types
* storage
* embedding provider
* Ollama setup
* vector index
* graph
* retrieval
* lifecycle
* configuration
* agent integration
* planner integration
* trading integration
* testing
* troubleshooting
* limitations

Documentation must describe the ACTUAL implementation.

---

# 43. CLI / DEBUGGING

Provide useful development commands such as:

```text
memory status
memory stats
memory search
memory inspect
memory procedures
memory episodes
memory failures
memory graph
memory embeddings
memory test
```

Do not add commands that are only decorative.

---

# 44. GIT SAFETY

Before every phase:

```text
git status
```

After every phase:

```text
git diff
```

Review all modified files.

Ensure changes belong to the Memory work.

If another agent modified a file during the phase:

DO NOT overwrite its changes.

Re-read the file and reconcile carefully.

Never use destructive git commands.

---

# 45. IMPLEMENTATION PHASES

Execute sequentially.

Do NOT skip phases silently.

## PHASE 0 — Repository + Existing Memory Audit

Read and understand the repository.

Inspect existing Memory implementation.

Inspect concurrent Trading Intelligence work.

Create architecture map.

NO major code changes.

Run baseline tests.

---

## PHASE 1 — Memory Architecture

Finalize:

* interfaces
* dependency boundaries
* provider abstraction
* lifecycle
* configuration
* integration contracts

Test architecture imports and DI.

---

## PHASE 2 — Persistent Storage

Implement/verify:

* SQLite
* schema
* migrations
* repositories
* indexes
* transactions
* persistence tests

Verify existing memory data survives restart.

---

## PHASE 3 — Memory Domain Models

Implement/verify:

* MemoryRecord
* WorkingMemory
* SemanticMemory
* EpisodicMemory
* ProceduralMemory
* PreferenceMemory
* FailureMemory
* RecoveryMemory
* TradingMemory
* MemoryRelationship
* MemoryMetadata

Serialization must be lossless.

---

## PHASE 4 — Memory Service Layer

Implement/verify:

```text
MemoryManager
MemoryWriter
MemoryReader
MemoryUpdater
MemoryValidator
MemoryScorer
```

Ensure clean DI.

---

## PHASE 5 — REAL EMBEDDING SYSTEM

Implement:

```text
EmbeddingProvider
OllamaEmbeddingProvider
provider factory
validation
batch embedding
dimension validation
error handling
```

Configure a real local embedding model through Ollama.

Do not fake embeddings.

Add integration tests.

---

## PHASE 6 — VECTOR INDEX

Implement real vector storage/retrieval.

Test:

```text
insert
search
similarity
metadata filtering
update
delete
persistence
```

---

## PHASE 7 — KNOWLEDGE GRAPH

Implement/verify:

* nodes
* edges
* entity relationships
* traversal
* persistence strategy
* graph retrieval

---

## PHASE 8 — HYBRID RETRIEVAL

Combine:

```text
SQL
Vector
Graph
Recency
Confidence
Importance
Relevance
```

Implement explainable scoring.

---

## PHASE 9 — WORKING MEMORY

Implement current task/session context.

Ensure it expires appropriately.

---

## PHASE 10 — EPISODIC MEMORY

Automatically record meaningful task episodes.

---

## PHASE 11 — FAILURE + RECOVERY

Record failures and successful recovery strategies.

---

## PHASE 12 — CONSOLIDATION

Implement:

* duplicate detection
* merge
* archive
* contradiction handling
* evidence preservation

---

## PHASE 13 — CONFIDENCE

Implement confidence scoring and updates.

---

## PHASE 14 — DECAY + LIFECYCLE

Implement:

```text
active
stale
decayed
archived
```

with safeguards for important/trading history.

---

## PHASE 15 — USER MEMORY CONTROL

Implement:

* inspect
* correct
* delete
* forget
* export
* disable

---

## PHASE 16 — TRADING MEMORY

Integrate with Trading Intelligence through stable interfaces.

Do not modify trading algorithms.

Support immutable predictions and linked outcomes.

---

## PHASE 17 — KNOWLEDGE / DOCUMENT INGESTION

Build ingestion interfaces for:

* documents
* notes
* research
* trading concepts
* structured knowledge

Use provenance.

Do not silently trust imported information.

---

## PHASE 18 — VISION + DESKTOP MEMORY

Store contextual observations.

Examples:

```text
application
window
UI element
screen observation
tool action
result
```

Historical UI positions must never override current vision.

---

## PHASE 19 — MEMORY TOOLS

Implement Agent-facing memory tools.

---

## PHASE 20 — AGENT AUTOMATIC MEMORY

Integrate memory into the existing Agent lifecycle.

Flow:

```text
Goal
→ Recall
→ Plan
→ Execute
→ Observe
→ Remember
→ Outcome
```

---

## PHASE 21 — PLANNER MEMORY

Inject bounded relevant MemoryContext before planning.

---

## PHASE 22 — AUTOMATIC EPISODE RECORDING

Ensure meaningful tasks automatically become episodes.

---

## PHASE 23 — EPISODE → PROCEDURE LEARNING

Learn reusable procedures from repeated successful episodes.

Include:

* thresholds
* confidence
* procedure versions
* validation
* success rates

---

## PHASE 24 — FAILURE-BASED PROCEDURE EVOLUTION

Allow successful recovery strategies to improve procedures.

---

## PHASE 25 — OBSERVABILITY

Implement:

* metrics
* diagnostics
* retrieval explanations
* health checks

---

## PHASE 26 — SECURITY + PRIVACY

Implement:

* redaction
* retention
* access control
* sensitive-data protection
* safe logging

---

## PHASE 27 — PERFORMANCE

Benchmark and optimize based on real measurements.

---

## PHASE 28 — CLI + DEBUGGING

Complete operational tooling.

---

## PHASE 29 — FULL SYSTEM VALIDATION

Run:

```text
unit tests
integration tests
memory tests
embedding tests
vector tests
graph tests
agent tests
planner tests
trading integration tests
regression suite
```

Validate:

```text
fresh install
existing database
restart
disabled memory
enabled memory
Ollama unavailable
embedding model unavailable
vector failure
database failure
agent failure
recovery
concurrent development changes
```

---

# 46. PHASE COMPLETION RULE

A phase is NOT complete merely because code exists.

For every phase:

```text
IMPLEMENT
↓
TEST
↓
FIX
↓
RETEST
↓
REVIEW
↓
DOCUMENT
↓
VERIFY
↓
DONE
```

Only after all required validation succeeds may you print:

```text
PHASE X — DONE
```

If incomplete:

```text
PHASE X — NOT DONE
```

Never fake completion.

---

# 47. FINAL PRODUCTION ACCEPTANCE

The Memory System is complete only when:

### Persistence

Memory survives restart.

### Embeddings

Real embeddings are generated by the configured provider.

### Retrieval

Semantic retrieval actually works.

### Vector

Real similarity search works.

### Graph

Relationships are queryable.

### Hybrid

SQL + vector + graph retrieval works together.

### Episodes

Tasks automatically produce meaningful episodes.

### Procedures

Repeated successful behavior can become reusable procedures.

### Failures

Failures and recoveries are remembered.

### Agent

Agent can recall and write memory automatically.

### Planner

Planner receives bounded relevant memory.

### Trading

Trading Intelligence can consume historical memory without owning Memory internals.

### Safety

Current reality overrides stale historical memory.

### Parallel development

Memory changes do not destroy another agent's work.

### Testing

Tests are actually executed and passing.

### Production

No fake production components remain.

---

# 48. FINAL REPORT

At the end of the entire implementation produce:

```text
========================================
AETHEROS MEMORY SYSTEM
FINAL IMPLEMENTATION REPORT
========================================

Architecture:
...

Memory Types:
...

Storage:
...

Embedding Provider:
...

Embedding Model:
...

Vector Backend:
...

Knowledge Graph:
...

Hybrid Retrieval:
...

Agent Integration:
...

Planner Integration:
...

Trading Integration:
...

Procedure Learning:
...

Failure Recovery:
...

Security:
...

Observability:
...

Performance:
...

Tests:
...

Passed:
...

Failed:
...

Pre-existing Failures:
...

Known Limitations:
...

Files Added:
...

Files Modified:
...

Files Intentionally Untouched:
...

Concurrent-Agent Conflicts:
...

Production Readiness:
...

Remaining Work:
...
```

Do not claim production-ready if critical components are missing.

---

# 49. ABSOLUTE RULES

Remember these throughout the entire task:

1. READ existing Memory first.
2. NEVER rebuild existing Memory from scratch.
3. NEVER use fake production memory.
4. NEVER use fake embeddings in production.
5. REAL embedding provider required.
6. Ollama/local embedding support is encouraged.
7. Keep embedding provider pluggable.
8. SQLite may remain structured source of truth.
9. Vector retrieval must be real.
10. Knowledge graph must be real.
11. Hybrid retrieval must be explainable.
12. Historical trading predictions are immutable.
13. Current reality overrides stale memory.
14. Memory failures should degrade gracefully.
15. Do not create a second EventBus.
16. Do not duplicate Trading Intelligence storage unnecessarily.
17. Another Claude agent is working in the same repo.
18. Never overwrite unrelated work.
19. Never reset/revert unrelated changes.
20. Test after EVERY phase.
21. Fix your failures before marking DONE.
22. Update documentation.
23. Do not claim completion without evidence.
24. No TODO pretending to be implementation.
25. No mock implementation replacing required production functionality.

START NOW.

First perform **PHASE 0 — Repository + Existing Memory Audit**.

Do not jump directly into implementation.

At the end of Phase 0, provide the audit, baseline test results, architecture map, existing-memory assessment, concurrent-agent risk assessment, and exact plan for Phase 1.

Only then:

`PHASE 0 — DONE`
