"""
Memory validator (spec Phase 4; enforces CLAUDE.md section 15).

Gatekeeper on the write path. Beyond basic shape checks it enforces the
project's epistemic rule that a model/prediction-sourced memory may never be
stored as a FACT -- the single most important integrity constraint for a
trading-intelligence system, where mistaking a prediction for a fact is exactly
the failure the whole product is built to avoid.

It also applies the content-safety foundation (spec Phase 3): bounded content /
payload size and secret redaction-or-rejection, so no unbounded blob and no
obvious credential is ever persisted. These run on *every* write from the first
write path, not deferred to a later security phase.
"""

from __future__ import annotations

import json

from ..domain.content_policy import ContentPolicy, SecretAction, redact_text, scan_secrets
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

    def __init__(self, policy: ContentPolicy | None = None) -> None:
        self._policy = policy or ContentPolicy()

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

        self._enforce_limits(memory)
        self._enforce_secret_policy(memory)

        # Normalise tags/entities in place: trimmed, de-duplicated, non-empty.
        memory.tags = list(
            dict.fromkeys(t.strip() for t in memory.tags if t and t.strip())
        )
        memory.entities = list(
            dict.fromkeys(e.strip() for e in memory.entities if e and e.strip())
        )
        return memory

    # ------------------------------------------------------------------
    # Content-safety foundation (spec Phase 3)
    # ------------------------------------------------------------------

    def _enforce_limits(self, memory: Memory) -> None:
        if len(memory.content) > self._policy.max_content_chars:
            raise MemoryValidationError(
                f"Memory content exceeds the {self._policy.max_content_chars}-char "
                "limit.",
                hint="Store large text via document ingestion, not a single memory.",
            )
        try:
            payload_bytes = len(json.dumps(memory.data, default=str).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise MemoryValidationError(
                "Memory payload is not JSON-serialisable.",
                cause=exc,
            ) from exc
        if payload_bytes > self._policy.max_payload_bytes:
            raise MemoryValidationError(
                f"Memory payload ({payload_bytes} bytes) exceeds the "
                f"{self._policy.max_payload_bytes}-byte limit.",
            )

    def _enforce_secret_policy(self, memory: Memory) -> None:
        if self._policy.on_secret is SecretAction.ALLOW:
            return
        if self._policy.on_secret is SecretAction.REJECT:
            found = scan_secrets(memory.content)
            if found:
                raise MemoryValidationError(
                    "Memory content appears to contain a secret "
                    f"({', '.join(found)}); refusing to persist it.",
                    hint="Remove the credential, or store a non-sensitive summary.",
                )
            return
        # REDACT (default): clean content in place and record what was removed.
        cleaned, kinds = redact_text(memory.content)
        if kinds:
            memory.content = cleaned
            removed = memory.metadata.setdefault("redacted_secret_kinds", [])
            for kind in kinds:
                if kind not in removed:
                    removed.append(kind)
