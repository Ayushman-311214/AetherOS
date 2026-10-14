"""
Evidence-based signal, probability, risk and explanation engine (Phase 5).

The layer that turns observations and features into *explainable* trading
intelligence -- a probabilistic assessment, never a claim of certainty. It
aggregates evidence across every available source, weights it, surfaces the
contradictions it could not resolve, and produces a ``SignalAssessment`` whose
probability, confidence and risk geometry are each honestly separated.

Honesty rules the whole layer is built around (CLAUDE.md sections 2, 3, 28):

* **A signal is a probabilistic assessment, not a verdict.** ``probability``,
  ``confidence``, the ``raw_evidence_score`` and the ``model_score`` are kept
  distinct so a reader can see exactly what was an input, what was computed and
  what was calibrated -- a raw score is never dressed up as a calibrated
  probability.
* **Missing evidence is explicit, never silently neutral.** A source that was
  not provided is recorded as ``MissingSource`` with a reason; it counts toward
  the coverage read, and it can never be folded into the score as if it had
  voted.
* **Contradictions are never hidden.** Supporting and contradicting evidence
  are reported separately and both carried; a signal under disagreement is a
  weaker, more honest signal, not a cleaned-up one.
* **The LLM is never the source of a number.** Everything here is
  deterministic/programmatic; an LLM may *narrate* a produced assessment but
  can never be where the numbers come from.
"""

from __future__ import annotations

from .assessment import SignalAssessment
from .evidence import EvidenceLedger, MissingSource
from .scoring import ScoreBreakdown
from .service import SignalEngineService

__all__ = [
    "EvidenceLedger",
    "MissingSource",
    "ScoreBreakdown",
    "SignalAssessment",
    "SignalEngineService",
]
