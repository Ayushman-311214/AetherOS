"""
Historical-analogue (nearest-neighbour) service.

Answers "when this instrument's setup looked like it does right now, what tended
to happen next?" purely deterministically (CLAUDE.md sections 1, 7, 15, 27). It
reuses the look-ahead-safe causal feature matrix from the quant layer
(``quant/features.py`` -- NOT a duplicated feature set, section 22): the latest
bar's feature vector is compared, in a standardised feature space, to every past
bar whose forward outcome over ``horizon`` is fully realised, and the K nearest
analogues' realised outcomes are aggregated into an up-rate and a mean forward
return.

It follows the RegimeService / AnomalyService shape: the service operates purely
on one ``MarketData`` domain object it is handed (no LLM, no I/O), so it is
trivially unit-testable with crafted candles, and identical inputs always yield
the identical read (section 22).

The read is honest about its own reliability (sections 9, 28): mock, unusable or
too-thin history yields ``Direction.UNKNOWN`` with the reason recorded in
``limitations`` rather than a fabricated lean, while an inconclusive analogue set
(an up-rate near 50/50) is a determinate reliable SIDEWAYS read. When the read is
determinate it emits a single ``EvidenceType.HISTORICAL`` :class:`Evidence` item.

This increment is deliberately standalone: the service and its tool stand beside
the existing pipeline and are not fused into the orchestrator, so no existing
behaviour changes.
"""

from __future__ import annotations

import numpy as np

from ...config.settings import Settings
from ..domain.enums import Assertion, Confidence, Direction, EvidenceType
from ..domain.evidence import Evidence
from ..domain.historical_analogue import HistoricalAnalogueAnalysis
from ..domain.market_data import MarketData
from ..quant.features import build_features

_EPS = 1e-12

# Absolute deviation of the analogue up-rate from 0.5 that maps to a full-weight
# (weight 1.0) evidence claim; anything larger is clamped. At 0.5 (a unanimous
# analogue set) the claim is full strength. This scales the *weight* of a single
# piece of evidence -- it is never a probability.
_FULL_WEIGHT_EDGE = 0.5


class HistoricalAnalogueService:
    """Deterministic nearest-analogue forward-outcome read over candles."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def analyze(
        self,
        data: MarketData,
        *,
        horizon: int | None = None,
    ) -> HistoricalAnalogueAnalysis:
        window = horizon if horizon is not None else self._settings.TRADING_HIST_HORIZON
        k = self._settings.TRADING_HIST_NEIGHBORS
        min_analogues = self._settings.TRADING_HIST_MIN_ANALOGUES
        dead_band = self._settings.TRADING_HIST_DEAD_BAND

        limitations: list[str] = []
        if data.provenance.is_mock:
            limitations.append(
                "Data is MOCK; historical analogues are illustrative, not a real "
                "market read."
            )
        if not data.quality.ok:
            limitations.extend(data.quality.issues)

        if not data.quality.usable:
            return self._unknown(data, window, 0, 0, tuple(limitations))

        fm = build_features(
            data.closes(), data.highs(), data.lows(), data.volumes(), horizon=window
        )
        sample_size = fm.rows
        if fm.latest is None or sample_size < min_analogues:
            if fm.latest is None:
                limitations.append(
                    "The latest bar has no complete feature vector yet (indicator "
                    "warm-up); no analogue read."
                )
            if sample_size < min_analogues:
                limitations.append(
                    f"Only {sample_size} historical analogues; need at least "
                    f"{min_analogues} for a read."
                )
            return self._unknown(data, window, sample_size, 0, tuple(limitations))

        neighbors = min(k, sample_size)
        nearest, mean_distance = self._nearest(fm.X, fm.latest, neighbors)

        closes = data.closes()
        up_rate, mean_forward = self._outcomes(
            closes, fm.indices[nearest], window
        )
        if up_rate is None:
            limitations.append(
                "Analogue forward returns could not be formed (a non-positive "
                "entry price); read undetermined."
            )
            return self._unknown(
                data, window, sample_size, neighbors, tuple(limitations)
            )

        edge = up_rate - 0.5
        if edge > dead_band:
            direction = Direction.UP
        elif edge < -dead_band:
            direction = Direction.DOWN
        else:
            direction = Direction.SIDEWAYS

        weight = min(1.0, abs(edge) / _FULL_WEIGHT_EDGE)
        confidence = Confidence.from_score(weight)
        observation = self._describe(
            direction, up_rate, mean_forward, neighbors, window
        )
        evidence = self._evidence(
            data, direction, weight, confidence, up_rate, mean_forward, neighbors,
            window, observation,
        )

        return HistoricalAnalogueAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            horizon=window,
            sample_size=sample_size,
            neighbors=neighbors,
            direction=direction,
            confidence=confidence,
            up_rate=round(up_rate, 6),
            mean_forward_return=round(mean_forward, 6),
            mean_distance=round(mean_distance, 6),
            quality=data.quality,
            provenance=data.provenance,
            evidence=evidence,
            observation=observation,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _nearest(
        x: np.ndarray, latest: np.ndarray, k: int
    ) -> tuple[np.ndarray, float]:
        """Indices of the k nearest rows of ``x`` to ``latest`` in a standardised
        feature space, plus the mean distance of those k."""
        mean = np.mean(x, axis=0)
        std = np.std(x, axis=0)
        # Constant columns (std ~ 0) carry no discriminating information; zero
        # their contribution rather than dividing by ~0.
        safe = np.where(std > _EPS, std, 1.0)
        xs = (x - mean) / safe
        ls = (latest - mean) / safe
        constant = std <= _EPS
        if np.any(constant):
            xs[:, constant] = 0.0
            ls = np.where(constant, 0.0, ls)
        distances = np.sqrt(np.sum((xs - ls) ** 2, axis=1))
        order = np.argsort(distances, kind="stable")[:k]
        return order, float(np.mean(distances[order]))

    @staticmethod
    def _outcomes(
        closes: np.ndarray, idxs: np.ndarray, horizon: int
    ) -> tuple[float | None, float | None]:
        """Up-rate and mean forward return of the analogues at ``idxs``."""
        entry = closes[idxs]
        exit_ = closes[idxs + horizon]
        if np.any(entry <= 0.0):
            return None, None
        returns = exit_ / entry - 1.0
        up_rate = float(np.mean(returns > 0.0))
        return up_rate, float(np.mean(returns))

    @staticmethod
    def _describe(
        direction: Direction,
        up_rate: float,
        mean_forward: float,
        neighbors: int,
        horizon: int,
    ) -> str:
        return (
            f"Across the {neighbors} closest historical analogues, {up_rate * 100:.0f}% "
            f"rose over the next {horizon} bars (mean {mean_forward * 100:+.2f}%): "
            f"a '{direction.value}' analogue lean."
        )

    def _evidence(
        self,
        data: MarketData,
        direction: Direction,
        weight: float,
        confidence: Confidence,
        up_rate: float,
        mean_forward: float,
        neighbors: int,
        horizon: int,
        detail: str,
    ) -> Evidence:
        return Evidence(
            instrument_key=data.instrument.key,
            type=EvidenceType.HISTORICAL,
            assertion=Assertion.CALCULATED,
            direction=direction,
            detail=detail,
            weight=weight,
            confidence=confidence,
            provenance=data.provenance,
            quality=data.quality,
            data={
                "up_rate": round(up_rate, 6),
                "mean_forward_return": round(mean_forward, 6),
                "neighbors": neighbors,
                "horizon": horizon,
            },
        )

    @staticmethod
    def _unknown(
        data: MarketData,
        horizon: int,
        sample_size: int,
        neighbors: int,
        limitations: tuple[str, ...],
    ) -> HistoricalAnalogueAnalysis:
        return HistoricalAnalogueAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            horizon=horizon,
            sample_size=sample_size,
            neighbors=neighbors,
            direction=Direction.UNKNOWN,
            confidence=Confidence.LOW,
            up_rate=None,
            mean_forward_return=None,
            mean_distance=None,
            quality=data.quality,
            provenance=data.provenance,
            evidence=None,
            observation=(
                "Historical-analogue read undetermined: insufficient or unusable "
                "history."
            ),
            limitations=limitations,
        )
