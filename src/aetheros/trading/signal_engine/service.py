"""
The signal engine service (Phase 5).

The composition point that turns observations and features into an explainable
:class:`SignalAssessment`. It aggregates evidence across every available
source -- market structure, liquidity, heatmap-derived features, volume, price
action, technical indicators, market regime, and the news/sentiment interfaces
when wired -- into an :class:`EvidenceLedger`, scores it (raw / model /
probability / confidence honestly separated), computes the risk geometry, and
surfaces supporting *and* contradicting evidence side by side.

It holds no analytical judgement of its own: the direction is the analysis's
fused read, the probability is the quant layer's calibrated estimate surfaced
verbatim (only when reliable), the risk is the deterministic risk engine's
output, and the scores are a documented linear aggregation. The service can
never invent a number, never hide a contradiction, and never treat a missing
source as a neutral vote.
"""

from __future__ import annotations

from ...config.settings import Settings
from ...core.logging import get_logger
from ..domain.analysis import TradingAnalysis
from ..domain.enums import Direction
from ..domain.evidence import Evidence
from ..domain.probability import ProbabilityEstimate
from ..domain.risk import RiskAssessment
from .assessment import SignalAssessment
from .evidence import EvidenceLedger, MissingSource
from .features import features_to_evidence
from .scoring import compute_scores

logger = get_logger("trading.signal_engine")


class SignalEngineService:
    """
    Aggregates evidence + features into an explainable SignalAssessment.

    ``risk_service`` and ``probability_service`` are injected (the deterministic
    risk engine and the calibrated quant layer); when the latter is wired the
    assessment surfaces its calibrated probability, else ``None``. ``analyze``
    takes a finished ``TradingAnalysis`` plus whatever feature-layer reads the
    caller holds (liquidity, market-intel, heatmap) -- sources that aren't
    provided are recorded as ``MissingSource``, never assumed neutral.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def assess(
        self,
        analysis: TradingAnalysis,
        *,
        risk: RiskAssessment | None = None,
        probability: ProbabilityEstimate | None = None,
        market_features=None,
        liquidity_features=None,
        heatmap_cells: tuple = (),
        expected_sources: int | None = None,
    ) -> SignalAssessment:
        """
        Build a signal assessment from a fused analysis plus feature reads.

        ``analysis`` carries the core directional read + evidence; ``risk``
        and ``probability`` are the deterministic/calibrated layers' outputs
        (optional -- the assessment honestly notes their absence); the feature
        objects are the Phase 2-4 vectors, converted to evidence items so a
        quantitative feature is recorded *as* evidence, never silently folded
        into a direction it didn't vote for.
        """
        direction = analysis.direction
        items: list[Evidence] = list(analysis.evidence)
        missing: list[MissingSource] = []
        provided = 0

        # Fold the feature vectors into the evidence ledger.
        feat_evidence, feat_missing, feat_provided = features_to_evidence(
            market_features=market_features,
            liquidity_features=liquidity_features,
            heatmap_cells=heatmap_cells,
            instrument=analysis.instrument,
            timeframe=analysis.timeframe_value,
            provenance=analysis.provenance,
            quality=analysis.quality,
        )
        items.extend(feat_evidence)
        missing.extend(feat_missing)
        provided += feat_provided

        if risk is None:
            missing.append(MissingSource("risk", "risk engine not wired"))
        if probability is None:
            missing.append(
                MissingSource(
                    "probability",
                    "calibrated estimate not wired or not reliable",
                )
            )
        provided += int(risk is not None) + int(probability is not None)

        # Expected sources = the feature layers supplied + the base layers
        # (core analysis + risk + probability + the always-present evidence
        # the analysis itself carries). A caller can override.
        expected = expected_sources or (feat_provided + 4)
        ledger = EvidenceLedger(
            items=tuple(items),
            missing=tuple(missing),
            fused_direction=direction,
        )
        scores = compute_scores(
            ledger,
            expected_sources=max(1, expected),
            calibrated_probability=(
                probability.p_up if probability is not None else None
            ),
            probability_reliable=(
                probability.is_reliable if probability is not None else False
            ),
        )

        # Contradiction split (reliable items only).
        supporting = ledger.supporting
        contradicting = ledger.opposing
        risk_factors = self._risk_factors(ledger, risk)

        is_actionable = (
            analysis.is_actionable
            and direction in (Direction.UP, Direction.DOWN)
            and scores.agreement >= 0.5
            and (risk.is_actionable if risk is not None else True)
        )

        # Limitations: surface the analysis's own plus the missing-data read.
        limitations = list(analysis.limitations)
        if missing:
            limitations.append(
                f"{len(missing)} expected source(s) unavailable: "
                + ", ".join(m.source for m in missing)
                + "."
            )
        if scores.probability_up is None:
            limitations.append(
                "No reliable calibrated probability; only raw/model scores "
                "are shown (never fabricated as a probability)."
            )
        if contradicting:
            limitations.append(
                f"{len(contradicting)} contradicting evidence item(s) "
                "surface the disagreement; the read is weaker for it."
            )

        return SignalAssessment(
            instrument=analysis.instrument,
            timeframe=analysis.timeframe_value,
            direction=direction,
            probability_up=scores.probability_up,
            confidence=scores.confidence,
            scores=scores,
            expected_move=self._expected_move(direction),
            time_horizon=analysis.timeframe_value,
            risk_reward_ratio=(
                risk.risk_reward_ratio if risk is not None else None
            ),
            entry=risk.entry if risk is not None else None,
            invalidation=(
                risk.invalidation
                if risk is not None
                else "No invalidation computed; risk engine not wired."
            ),
            targets=risk.targets if risk is not None else (),
            risk_band=(
                risk.overall_risk
                if risk is not None
                else _risk_band_unknown()
            ),
            supporting=tuple(supporting),
            contradicting=tuple(contradicting),
            risk_factors=risk_factors,
            missing_sources=tuple(missing),
            coverage=scores.coverage,
            is_actionable=is_actionable,
            is_mock=analysis.provenance.is_mock,
            limitations=tuple(limitations),
            model="deterministic-evidence/1.0",
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _expected_move(direction: Direction) -> str:
        return {
            Direction.UP: "up",
            Direction.DOWN: "down",
            Direction.SIDEWAYS: "sideways",
        }.get(direction, "unknown")

    @staticmethod
    def _risk_factors(
        ledger: EvidenceLedger, risk: RiskAssessment | None
    ) -> tuple[str, ...]:
        """Named risk considerations for the assessment."""
        factors: list[str] = []
        if risk is not None:
            if risk.volatility_risk.value == "high":
                factors.append(
                    f"High volatility: ATR is {risk.atr_pct * 100:.2f}% of price."
                )
            if risk.stop_distance_pct is not None and risk.stop_distance_pct > 0.03:
                factors.append(
                    f"Wide stop ({risk.stop_distance_pct * 100:.1f}%) increases "
                    "tail risk."
                )
        # Contradicting evidence is itself a risk factor.
        if ledger.opposing:
            factors.append(
                f"{len(ledger.opposing)} contradicting evidence item(s)."
            )
        if ledger.missing:
            factors.append(
                f"{len(ledger.missing)} expected source(s) missing."
            )
        return tuple(factors)


def _risk_band_unknown():
    from ..domain.enums import RiskBand
    return RiskBand.UNKNOWN
