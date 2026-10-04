"""
Memory validator (spec Phase 4; enforces CLAUDE.md section 15).

Gatekeeper on the write path. Beyond basic shape checks it enforces the
project's epistemic rule that a model/prediction-sourced memory may never be
stored as a FACT -- the single most important integrity constraint for a
trading-intelligence system, where mistaking a prediction for a fact is exactly
the failure the whole product is built to avoid.
"""

from __future__ import annotations

from ..domain.enums import SourceType, Veracity
from ..domain.memory import Memory
from ...core.errors.memory_error import MemoryValidationError

# Sources whose content is inherently uncertain; asserting it as FACT is a bug.
_NON_FACTUAL_SOURCES = {
    SourceType.PREDICTION,
    SourceType.MODEL,
    SourceType.INFERENCE,
}


class MemoryValidator:
    """Validate (and lightly normalise) a memory before it is persisted."""

    def validate(self, memory: Memory) -> Memory:
        if not memory.content or not memory.content.strip():
            raise MemoryValidationError(
                "A memory must have non-empty content.",
                hint="Provide a human-readable statement for the memory.",
            )

        if not (0.0 <= memory.confidence <= 1.0):
            raise MemoryValidationError(
                f"Confidence {memory.confidence} is outside [0, 1].",
            )

        if (
            memory.veracity is Veracity.FACT
            and memory.source.source_type in _NON_FACTUAL_SOURCES
        ):
            raise MemoryValidationError(
                "A prediction/model/inference-sourced memory cannot be stored as "
                "a FACT (CLAUDE.md section 15).",
                hint="Use Veracity.PREDICTION, MODEL_OUTPUT or ASSUMPTION instead.",
            )

        # Normalise tags/entities in place: trimmed, de-duplicated, non-empty.
        memory.tags = list(
            dict.fromkeys(t.strip() for t in memory.tags if t and t.strip())
        )
        memory.entities = list(
            dict.fromkeys(e.strip() for e in memory.entities if e and e.strip())
        )
        return memory
