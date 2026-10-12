"""
The six canonical heatmap views over one shared grid.

A "heatmap" here is a named projection of the :class:`HeatmapCell` grid: it
picks which cell quantity becomes the *intensity* channel for that view and
normalises it to ``[0, 1]`` for rendering. All six read the SAME underlying
cells -- they are six lenses, not six engines -- so they can never disagree
about what the data was; they only disagree about what is being emphasised.

A :class:`HeatmapView` is the rendered payload: the grid's cells re-expressed
as ``(timestamp, price, intensity)`` triples plus the normalisation metadata a
renderer needs (min/max actually observed, so a colour scale is honest about
its range rather than stretched to fill it).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cell import HeatmapCell
from .grid import HeatmapGrid

#: Each view is (name, intensity accessor). The accessor reads a cell and
#: returns the raw quantity that view emphasises.
_VIEW_CHANNELS: dict[str, str] = {
    "liquidity": "total_intensity",     # resting liquidity shown in the bin
    "persistence": "persistence",       # how long liquidity stood there
    "flow": "net_flow",                 # aggressor-signed executed flow
    "sweep": "sweep_score",             # sweep intensity (rejection+acceptance)
    "absorption": "absorption_score",   # absorption divergence strength
    "pressure": "pressure_score",       # derived market-pressure magnitude
}


@dataclass(frozen=True, slots=True)
class HeatmapPoint:
    """One rendered cell: its bin coordinates and the view's intensity."""

    timestamp: str
    price: float
    intensity: float
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "price": self.price,
            "intensity": self.intensity,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True, slots=True)
class HeatmapView:
    """
    A rendered heatmap projection.

    ``kind`` names which lens this is; ``points`` are the cells' (time, price,
    intensity) triples in deterministic (time, price) order; ``min``/``max``
    record the observed range so a colour scale is honest rather than stretched
    to fill an arbitrary band. ``cells`` is the shared underlying grid cells
    for consumers that want the full detail rather than the projected channel.
    """

    kind: str
    symbol: str
    price_step: float
    bucket_seconds: float
    points: tuple[HeatmapPoint, ...]
    min_intensity: float
    max_intensity: float
    cell_count: int
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "symbol": self.symbol,
            "price_step": self.price_step,
            "bucket_seconds": self.bucket_seconds,
            "min_intensity": self.min_intensity,
            "max_intensity": self.max_intensity,
            "cell_count": self.cell_count,
            "is_mock": self.is_mock,
            "points": [p.to_dict() for p in self.points],
        }


def _channel_value(cell: HeatmapCell, channel: str) -> float:
    """Read one cell's raw channel quantity for a view."""
    return float(getattr(cell, channel))


def render(
    grid: HeatmapGrid,
    kind: str,
    *,
    normalize: bool = True,
) -> HeatmapView:
    """
    Project a grid into one named view.

    ``normalize`` scales intensities to ``[0, 1]`` over the observed range; a
    view whose channel is all-zero (or all-equal) reports ``min == max`` and
    emits honest flat intensities rather than dividing by zero or fabricating a
    range. Cells are returned in deterministic (time, price) order.
    """
    if kind not in _VIEW_CHANNELS:
        raise ValueError(
            f"Unknown heatmap kind '{kind}'. "
            f"Supported: {', '.join(sorted(_VIEW_CHANNELS))}."
        )
    channel = _VIEW_CHANNELS[kind]
    cells = sorted(grid.cells, key=lambda c: (c.timestamp, c.price))

    raw = [_channel_value(c, channel) for c in cells]
    lo = min(raw, default=0.0)
    hi = max(raw, default=0.0)
    span = hi - lo

    points = tuple(
        HeatmapPoint(
            timestamp=c.timestamp,
            price=c.price,
            intensity=(
                round((v - lo) / span, 4)
                if normalize and span > 0
                else (round(v, 4) if not normalize else 0.0)
            ),
            is_mock=c.is_mock,
        )
        for c, v in zip(cells, raw)
    )

    return HeatmapView(
        kind=kind,
        symbol=grid.symbol,
        price_step=grid.price_step,
        bucket_seconds=grid.bucket_seconds,
        points=points,
        min_intensity=lo,
        max_intensity=hi,
        cell_count=grid.cell_count,
        is_mock=any(c.is_mock for c in cells),
    )


def available_views() -> tuple[str, ...]:
    """The view kinds this layer can render."""
    return tuple(sorted(_VIEW_CHANNELS))
