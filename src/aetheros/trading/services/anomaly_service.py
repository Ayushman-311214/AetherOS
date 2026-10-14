"""
Statistical-anomaly detection service.

Flags whether the most recent bar is a statistical outlier against the
instrument's own trailing baseline -- an unusually large return, an unusual
volume, or an unusual overnight gap -- each expressed as a z-score. This is the
deterministic engine that populates the previously-unpopulated
``EvidenceType.ANOMALY`` line (CLAUDE.md sections 5, 9, 27). It follows the same
shape as :class:`RegimeService` and :class:`RelativeStrengthService`: the service
operates purely on one ``MarketData`` domain object it is handed (no LLM, no
I/O), so it is trivially unit-testable with crafted candles, and identical
inputs always yield the identical read (section 22).

The read is honest about its own reliability (sections 9, 15, 28): mock,
unusable or too-thin data yields ``Direction.UNKNOWN`` with the reason recorded
in ``limitations`` rather than a fabricated z-score, while a quiet tape with no
outlier is a *determinate* reliable "no anomaly" read (SIDEWAYS). When a genuine
outlier is present the service emits a single ``EvidenceType.ANOMALY``
:class:`Evidence` item so downstream layers can consume the detection like any
other piece of evidence.

This increment is deliberately standalone: the service and its tool stand beside
the existing pipeline and are not fused into the orchestrator, so no existing
behaviour changes.
"""

from __future__ import annotations

import numpy as np

from ...config.settings import Settings
from ..domain.anomaly import AnomalyAnalysis
from ..domain.enums import Assertion, Confidence, Direction, EvidenceType
from ..domain.evidence import Evidence
from ..domain.market_data import MarketData

# Absolute z-score that maps to a full-strength (weight 1.0) evidence claim;
# anything larger is clamped. A 6-sigma move is treated as a maximally notable
# outlier. This scales the *weight* of a single piece of evidence -- it is never
# a probability.
_FULL_WEIGHT_Z = 6.0


class AnomalyService:
    """Deterministic last-bar statistical-outlier read over candles."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def analyze(self, data: MarketData) -> AnomalyAnalysis:
        lookback = self._settings.TRADING_ANOMALY_LOOKBACK
        min_bars = self._settings.TRADING_ANOMALY_MIN_BARS
        z_thresh = self._settings.TRADING_ANOMALY_Z

        limitations: list[str] = []
        if data.provenance.is_mock:
            limitations.append(
                "Data is MOCK; anomaly detection is illustrative, not a real "
                "market read."
            )
        if not data.quality.ok:
            limitations.extend(data.quality.issues)

        n = data.count
        # Baseline observations available = (n - 1) returns, minus the last one
        # being tested. Cap that at the configured lookback window.
        used = min(lookback, n - 2)
        if not data.quality.usable or used < min_bars:
            if used < min_bars:
                limitations.append(
                    f"Only {max(used, 0)} baseline bars; need at least "
                    f"{min_bars} for an anomaly read."
                )
            return self._unknown(data, max(used, 0), tuple(limitations))

        closes = data.closes()
        volumes = data.volumes()
        opens = data.opens()

        return_z, last_return = self._return_zscore(closes, used)
        volume_z = self._volume_zscore(volumes, used)
        gap_z, last_gap = self._gap_zscore(opens, closes, used)

        return_fires = return_z is not None and abs(return_z) >= z_thresh
        volume_fires = volume_z is not None and abs(volume_z) >= z_thresh
        gap_fires = gap_z is not None and abs(gap_z) >= z_thresh
        is_anomalous = return_fires or volume_fires or gap_fires

        direction = self._lean(
            return_fires, volume_fires, gap_fires, last_return, last_gap
        )

        if not is_anomalous:
            return AnomalyAnalysis(
                instrument=data.instrument,
                timeframe_value=data.timeframe.value,
                lookback=used,
                is_anomalous=False,
                return_z=self._round(return_z),
                volume_z=self._round(volume_z),
                gap_z=self._round(gap_z),
                last_return=self._round(last_return),
                direction=Direction.SIDEWAYS,
                confidence=Confidence.LOW,
                quality=data.quality,
                provenance=data.provenance,
                evidence=None,
                observation=(
                    f"No statistical anomaly over the last bar vs its {used}-bar "
                    "baseline (return/volume/gap all within tolerance)."
                ),
                limitations=tuple(limitations),
            )

        # Weight from the strongest z among the measures that actually fired.
        firing = [
            abs(z)
            for z, fired in (
                (return_z, return_fires),
                (volume_z, volume_fires),
                (gap_z, gap_fires),
            )
            if fired and z is not None
        ]
        max_z = max(firing)
        weight = min(1.0, max_z / _FULL_WEIGHT_Z)
        confidence = Confidence.from_score(weight)
        observation = self._describe(
            used, return_z, volume_z, gap_z, return_fires, volume_fires, gap_fires,
            z_thresh, direction,
        )
        evidence = self._evidence(
            data, direction, weight, confidence, return_z, volume_z, gap_z, used,
            observation,
        )

        return AnomalyAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            lookback=used,
            is_anomalous=True,
            return_z=self._round(return_z),
            volume_z=self._round(volume_z),
            gap_z=self._round(gap_z),
            last_return=self._round(last_return),
            direction=direction,
            confidence=confidence,
            quality=data.quality,
            provenance=data.provenance,
            evidence=evidence,
            observation=observation,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _zscore(series: np.ndarray, used: int) -> tuple[float | None, float]:
        """z-score of the last element vs the prior ``used`` elements.

        Returns ``(z, last)``; z is None when the baseline std is zero or not
        finite (a degenerate baseline can't establish what "unusual" means).
        """
        last = float(series[-1])
        baseline = series[-(used + 1) : -1]
        mean = float(np.mean(baseline))
        std = float(np.std(baseline))
        if std <= 0.0 or not np.isfinite(std):
            return None, last
        z = (last - mean) / std
        if not np.isfinite(z):
            return None, last
        return z, last

    def _return_zscore(
        self, closes: np.ndarray, used: int
    ) -> tuple[float | None, float | None]:
        if np.any(closes[:-1] <= 0.0):
            return None, None
        rets = closes[1:] / closes[:-1] - 1.0
        if rets.size < used + 1:
            return None, None
        z, last = self._zscore(rets, used)
        return z, last

    def _volume_zscore(self, volumes: np.ndarray, used: int) -> float | None:
        if volumes.size < used + 1:
            return None
        z, _ = self._zscore(volumes, used)
        return z

    def _gap_zscore(
        self, opens: np.ndarray, closes: np.ndarray, used: int
    ) -> tuple[float | None, float | None]:
        # Overnight gap of bar i = open[i] / close[i-1] - 1.
        if np.any(closes[:-1] <= 0.0):
            return None, None
        gaps = opens[1:] / closes[:-1] - 1.0
        if gaps.size < used + 1:
            return None, None
        z, last = self._zscore(gaps, used)
        return z, last

    @staticmethod
    def _lean(
        return_fires: bool,
        volume_fires: bool,
        gap_fires: bool,
        last_return: float | None,
        last_gap: float | None,
    ) -> Direction:
        """Directional lean of the detected anomaly.

        A return outlier leans with the sign of the move; failing that a gap
        outlier leans with the sign of the gap; a volume-only spike is a notable
        but non-directional event (SIDEWAYS).
        """
        if return_fires and last_return is not None:
            return Direction.UP if last_return > 0 else Direction.DOWN
        if gap_fires and last_gap is not None:
            return Direction.UP if last_gap > 0 else Direction.DOWN
        return Direction.SIDEWAYS

    @staticmethod
    def _round(value: float | None) -> float | None:
        return round(value, 4) if value is not None else None

    @staticmethod
    def _describe(
        used: int,
        return_z: float | None,
        volume_z: float | None,
        gap_z: float | None,
        return_fires: bool,
        volume_fires: bool,
        gap_fires: bool,
        z_thresh: float,
        direction: Direction,
    ) -> str:
        parts: list[str] = []
        if return_fires and return_z is not None:
            parts.append(f"return {return_z:+.1f}sigma")
        if volume_fires and volume_z is not None:
            parts.append(f"volume {volume_z:+.1f}sigma")
        if gap_fires and gap_z is not None:
            parts.append(f"gap {gap_z:+.1f}sigma")
        drivers = ", ".join(parts)
        return (
            f"Statistical anomaly on the last bar vs its {used}-bar baseline "
            f"({drivers}; threshold {z_thresh:g}sigma): "
            f"'{direction.value}' lean."
        )

    def _evidence(
        self,
        data: MarketData,
        direction: Direction,
        weight: float,
        confidence: Confidence,
        return_z: float | None,
        volume_z: float | None,
        gap_z: float | None,
        used: int,
        detail: str,
    ) -> Evidence:
        return Evidence(
            instrument_key=data.instrument.key,
            type=EvidenceType.ANOMALY,
            assertion=Assertion.DETECTED,
            direction=direction,
            detail=detail,
            weight=weight,
            confidence=confidence,
            provenance=data.provenance,
            quality=data.quality,
            data={
                "return_z": self._round(return_z),
                "volume_z": self._round(volume_z),
                "gap_z": self._round(gap_z),
                "lookback": used,
            },
        )

    @staticmethod
    def _unknown(
        data: MarketData,
        used: int,
        limitations: tuple[str, ...],
    ) -> AnomalyAnalysis:
        return AnomalyAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            lookback=used,
            is_anomalous=False,
            return_z=None,
            volume_z=None,
            gap_z=None,
            last_return=None,
            direction=Direction.UNKNOWN,
            confidence=Confidence.LOW,
            quality=data.quality,
            provenance=data.provenance,
            evidence=None,
            observation=(
                "Anomaly detection undetermined: insufficient or unusable data."
            ),
            limitations=limitations,
        )
