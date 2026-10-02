"""
Signal-explanation service.

Produces a deterministic :class:`Explanation` of a finished
:class:`TradingReport` -- the spec's "explain why a signal was generated"
capability (CLAUDE.md section 1). It is pure, read-only synthesis: it gathers
every :class:`Evidence` item the report already carries (the analysis ledger plus
the one item each fused context layer contributes), de-duplicates by the
content-addressed evidence id, groups the reliable directional items into those
that agree with the fused call and those that oppose it, and writes a plain
summary of how they net out behind the recommendation.

It computes no new signal and invents no number (sections 5, 28): the direction,
confidence and recommendation are read straight off the report, and only
reliable (usable, non-mock, observed/calculated/detected) evidence contributes to
the net weight -- so a MOCK-data report explains itself honestly as the NO_TRADE
it is, with its limitations surfaced rather than hidden.
"""

from __future__ import annotations

from ...config.settings import Settings
from ..domain.enums import Direction
from ..domain.evidence import Evidence
from ..domain.explanation import EvidenceReason, Explanation
from ..domain.report import TradingReport


class ExplanationService:
    """Deterministic, read-only explanation of a composed trading report."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def explain(self, report: TradingReport) -> Explanation:
        evidence = self._collect(report)
        direction = report.direction

        supporting: list[EvidenceReason] = []
        opposing: list[EvidenceReason] = []
        reliable_count = 0
        for e in evidence:
            if e.is_reliable:
                reliable_count += 1
            reason = EvidenceReason(
                detail=e.detail,
                type=e.type.value,
                direction=e.direction,
                weight=e.weight,
                is_reliable=e.is_reliable,
            )
            # Only reliable, directional evidence is placed for/against; it is the
            # only evidence allowed to move the net weight (spec section 28).
            if not e.is_reliable or e.direction not in (Direction.UP, Direction.DOWN):
                continue
            if direction in (Direction.UP, Direction.DOWN):
                if e.direction is direction:
                    supporting.append(reason)
                else:
                    opposing.append(reason)

        supporting.sort(key=lambda r: r.weight, reverse=True)
        opposing.sort(key=lambda r: r.weight, reverse=True)
        support_w = round(sum(r.weight for r in supporting), 6)
        oppose_w = round(sum(r.weight for r in opposing), 6)

        summary = self._summarise(
            report, len(supporting), len(opposing), support_w, oppose_w,
            reliable_count,
        )

        return Explanation(
            instrument=report.instrument,
            timeframe_value=report.analysis.timeframe_value,
            direction=direction,
            recommendation=report.recommendation,
            confidence=report.confidence,
            is_actionable=report.is_actionable,
            supporting=tuple(supporting),
            opposing=tuple(opposing),
            supporting_weight=support_w,
            opposing_weight=oppose_w,
            reliable_evidence_count=reliable_count,
            total_evidence_count=len(evidence),
            critic_reasons=tuple(report.critique.reasons),
            summary=summary,
            limitations=report.limitations,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _collect(report: TradingReport) -> list[Evidence]:
        """Every evidence item the report carries, de-duplicated by content id.

        Order-preserving: the core analysis ledger first, then each fused layer's
        contribution in pipeline order. A layer that is absent, or that produced
        no evidence (e.g. an UNKNOWN read), contributes nothing.
        """
        items: list[Evidence] = list(report.analysis.evidence)

        # Layers that expose a *tuple* of evidence.
        for multi in (report.news, report.fundamentals):
            if multi is not None:
                items.extend(multi.evidence)

        # Layers that expose a single optional evidence item.
        for single in (
            report.relative_strength,
            report.anomaly,
            report.historical_analogue,
            report.macro,
            report.multi_timeframe,
            report.divergence,
        ):
            if single is not None and single.evidence is not None:
                items.append(single.evidence)

        seen: dict[str, Evidence] = {}
        for e in items:
            seen.setdefault(e.id, e)
        return list(seen.values())

    @staticmethod
    def _summarise(
        report: TradingReport,
        n_support: int,
        n_oppose: int,
        support_w: float,
        oppose_w: float,
        reliable_count: int,
    ) -> str:
        rec = report.recommendation.value.upper()
        direction = report.direction

        if direction not in (Direction.UP, Direction.DOWN):
            # No tradable side -- explain the honest NO_TRADE.
            if reliable_count == 0:
                return (
                    f"{rec}: no reliable evidence supports a directional call, so "
                    "there is nothing to act on (insufficient evidence)."
                )
            return (
                f"{rec}: the evidence did not resolve to a tradable direction "
                f"('{direction.value}'), so no side is recommended."
            )

        lean = direction.value
        verdict = report.critique.verdict.value
        base = (
            f"{rec}: {n_support} reliable item(s) (weight {support_w:g}) back the "
            f"'{lean}' read and {n_oppose} (weight {oppose_w:g}) oppose it; the "
            f"critic verdict is '{verdict}'."
        )
        if not report.is_actionable:
            base += (
                " The report is not actionable -- data quality, the critic, or the "
                "risk plan held it back (see limitations)."
            )
        return base
