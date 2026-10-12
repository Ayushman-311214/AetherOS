"""
Signal scoring -- raw evidence score, model score, probability, confidence.

The four quantities the spec insists stay *separate*, so a reader can always
tell an input from a computation from a calibrated estimate:

* **raw_evidence_score** -- the weighted net of the evidence ledger, mapped to
  ``[-1, 1]``. It is an *aggregation of the evidence*, nothing more; it is NOT
  a probability and is never read as one.
* **model_score** -- the score a downstream model produces (currently the
  raw score passed through, but kept as a distinct field so a calibrated model
  can slot in behind the same contract).
* **probability** -- the calibrated P(up) for the fused direction, produced by
  the quant layer when it is wired and *reliable*, else ``None``. An estimate
  under stated conditions, never a guarantee -- and never a raw score dressed
  up as one.
* **confidence** -- a qualitative band (LOW/MEDIUM/HIGH) reflecting *how much
  trustworthy evidence stood behind the read* (reliability + coverage +
  agreement), NOT the probability. A thin or contradictory read is low
  confidence even when its probability looks strong.

The formulas are documented and linear -- no hidden magic weight. The
calibration assumption is stated, not dressed up: until the quant layer is
wired the ``probability`` is ``None`` and only the raw/model scores exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..domain.enums import Confidence, Direction
from .evidence import EvidenceLedger

#: The number of expected evidence sources a full read draws on. Used for the
#: coverage input to confidence -- a read on half its sources is thinner.
EXPECTED_SOURCES = 8

#: The weight scale that maps net evidence weight onto a [-1,1] raw score.
#: A net directional weight of ~2 (a couple of strong agreeing items) saturates
#: the score. Linear cap, not a fit.
_NET_WEIGHT_SCALE = 2.0

#: Confidence floor: with zero reliable evidence the read is LOW by definition.
_MIN_RELIABLE_FOR_MEDIUM = 2


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """
    The honest separation of a signal's quantitative pieces.

    Every field is a distinct, documented quantity -- raw aggregate, model
    score, calibrated probability, qualitative confidence, and the three inputs
    that drove confidence (reliability, coverage, agreement).
    """

    raw_evidence_score: float        # -1..1 aggregated net evidence
    model_score: float               # the score a model produced (same scale)
    probability_up: float | None     # calibrated P(up), None when unavailable
    direction: Direction
    confidence: Confidence
    reliable_evidence_count: int
    coverage: float                  # 0..1 share of expected sources present
    agreement: float                 # 0..1 share of directional weight agreeing
    has_calibrated_probability: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_evidence_score": self.raw_evidence_score,
            "model_score": self.model_score,
            "probability": (
                {"up": self.probability_up, "down": 1.0 - self.probability_up}
                if self.probability_up is not None
                else None
            ),
            "has_calibrated_probability": self.has_calibrated_probability,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "reliable_evidence_count": self.reliable_evidence_count,
            "coverage": self.coverage,
            "agreement": self.agreement,
            "semantics": {
                "raw_evidence_score": "weighted net evidence, not a probability",
                "probability": "calibrated estimate; None when not reliable",
                "confidence": "qualitative band from reliability+coverage+"
                              "agreement, not a probability",
            },
        }


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def compute_scores(
    ledger: EvidenceLedger,
    *,
    expected_sources: int = EXPECTED_SOURCES,
    calibrated_probability: float | None = None,
    probability_reliable: bool = False,
) -> ScoreBreakdown:
    """
    Fuse an ``EvidenceLedger`` into a ``ScoreBreakdown``.

    ``calibrated_probability`` is the quant layer's P(up) when wired and
    reliable; it is surfaced verbatim (never recomputed) and is ``None`` when
    the estimate isn't reliable or isn't wired -- so the raw score is never
    back-filled into a fake probability.
    """
    direction = ledger.fused_direction
    net = ledger.net_weight
    raw = _clamp(net / _NET_WEIGHT_SCALE)
    coverage = ledger.coverage(expected_sources)

    # Agreement: share of reliable directional weight on the fused side.
    directional = ledger.supporting_weight + ledger.opposing_weight
    agreement = (
        ledger.supporting_weight / directional if directional > 0 else 0.0
    )

    # Confidence: reliability + coverage + agreement (a qualitative band).
    confidence = _confidence(
        reliable=ledger.reliable_count,
        coverage=coverage,
        agreement=agreement,
        has_direction=direction in (Direction.UP, Direction.DOWN),
    )

    # The probability is surfaced only when the calibrated estimate is reliable
    # -- a raw score is never substituted for it.
    p_up = calibrated_probability if probability_reliable else None

    return ScoreBreakdown(
        raw_evidence_score=round(raw, 4),
        model_score=round(raw, 4),  # passthrough until a calibrated model is wired
        probability_up=round(p_up, 4) if p_up is not None else None,
        direction=direction,
        confidence=confidence,
        reliable_evidence_count=ledger.reliable_count,
        coverage=coverage,
        agreement=round(agreement, 4),
        has_calibrated_probability=probability_reliable and p_up is not None,
    )


def _confidence(
    *,
    reliable: int,
    coverage: float,
    agreement: float,
    has_direction: bool,
) -> Confidence:
    """
    A qualitative confidence band from evidence quality, NOT a probability.

    HIGH needs directional evidence, reasonable coverage and agreement; MEDIUM
    needs at least a directional read with some reliable evidence; everything
    else is LOW. Thin or contradictory evidence can never read as confident.
    """
    if not has_direction or reliable == 0:
        return Confidence.LOW
    score = 0.4 * coverage + 0.4 * agreement + 0.2 * min(1.0, reliable / 4.0)
    if score >= 0.70 and reliable >= _MIN_RELIABLE_FOR_MEDIUM:
        return Confidence.HIGH
    if score >= 0.40 and reliable >= 1:
        return Confidence.MEDIUM
    return Confidence.LOW
