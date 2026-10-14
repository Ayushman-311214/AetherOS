"""
The 3D liquidity surface -- X = price, Y = time, Z = liquidity intensity.

A reusable *data* representation, deliberately separate from any renderer. The
surface is just the same bounded cell grid re-expressed as a
``(price, time) -> intensity`` matrix, so a terminal, a future GUI or a web
dashboard can all consume the identical numbers. No renderer is required for
the core intelligence; the surface is a pure projection of the grid.

For a terminal (which cannot draw a true 3D surface) :meth:`project` produces a
2D intensity matrix plus the axis labels -- a faithful, lossless-in-value
projection of the same cells, not a corrupted or resampled copy. The underlying
``HeatmapCell`` data is untouched by the projection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .grid import HeatmapGrid


@dataclass(frozen=True, slots=True)
class LiquiditySurface:
    """
    A price x time x intensity surface.

    ``prices`` are the ascending distinct price-bin bounds, ``timestamps`` the
    ascending distinct time-bucket starts, and ``values`` a ``len(timestamps)``
    x ``len(prices)`` matrix where ``values[t][p]`` is the channel intensity for
    that (price, time) cell -- ``0.0`` where the grid had no cell. ``channel``
    names which quantity this surface encodes.
    """

    symbol: str
    channel: str
    prices: tuple[float, ...]
    timestamps: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "channel": self.channel,
            "prices": list(self.prices),
            "timestamps": list(self.timestamps),
            "values": [list(row) for row in self.values],
            "is_mock": self.is_mock,
        }


def surface(
    grid: HeatmapGrid,
    channel: str = "total_intensity",
) -> LiquiditySurface:
    """
    Project the shared grid into a price x time intensity surface.

    Reads the same cells the 2D views use; only the *shape* differs. A missing
    cell reads as ``0.0`` -- an honest "no liquidity observed there", never an
    interpolated fill.
    """
    cells = grid.cells
    prices = sorted({c.price for c in cells})
    times = sorted({c.timestamp for c in cells})
    pindex = {p: i for i, p in enumerate(prices)}
    tindex = {t: i for i, t in enumerate(times)}

    matrix = [[0.0 for _ in prices] for _ in times]
    for c in cells:
        matrix[tindex[c.timestamp]][pindex[c.price]] = float(
            getattr(c, channel, c.total_intensity)
        )

    return LiquiditySurface(
        symbol=grid.symbol,
        channel=channel,
        prices=tuple(prices),
        timestamps=tuple(times),
        values=tuple(tuple(row) for row in matrix),
        is_mock=any(c.is_mock for c in cells),
    )


def project(
    surface_obj: LiquiditySurface,
    *,
    width: int = 60,
    charset: str = " .:-=+*#%@",
) -> str:
    """
    A terminal-friendly 2D projection of the surface as a text intensity map.

    Rows are time (oldest at top), columns are price (ascending left to right),
    and each glyph encodes the cell's intensity against the surface's own
    observed max -- so the shading is honest about its range and a flat/zero
    surface renders as blanks, not a fabricated gradient. ``width`` caps the
    column count for a terminal row; longer price axes are downsampled by max
    (a windowed peak, so a hot cell is never averaged away).
    """
    prices = surface_obj.prices
    times = surface_obj.timestamps
    values = surface_obj.values
    if not prices or not times:
        return "(empty liquidity surface)"

    hi = max((v for row in values for v in row), default=0.0)

    # Downsample columns to `width` by taking the max of each window.
    n = len(prices)
    step = max(1, (n + width - 1) // width)
    def _cell_char(v: float) -> str:
        if hi <= 0 or v <= 0:
            return " "
        level = min(len(charset) - 1, int(round(v / hi * (len(charset) - 1))))
        return charset[level]

    lines = []
    for t, row in zip(times, values):
        glyphs = []
        for start in range(0, n, step):
            window = row[start : start + step]
            glyphs.append(_cell_char(max(window)))
        label = t[11:19] if len(t) >= 19 else t  # HH:MM:SS from ISO
        lines.append(f"{label} |{''.join(glyphs)}")

    lo_p, hi_p = prices[0], prices[-1]
    header = f"{'time':>8} {lo_p:.2f} .. {hi_p:.2f}  (intensity x{hi:.2f})"
    return header + "\n" + "\n".join(lines)
