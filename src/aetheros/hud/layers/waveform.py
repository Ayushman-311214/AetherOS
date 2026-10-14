from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPen

from ..paint import RenderContext, qcolor
from .base import Layer

#: Fixed per-bin weighting. Gives the ring a stable, organic profile
# so it reads as a spectrum rather than a uniform ring of equal bars —
# without running an FFT. The visualization is amplitude-driven by
# design; this shapes it, it does not fabricate frequency data.
_PROFILE_HARMONICS = (
    (1.0, 0.55),
    (2.0, 0.24),
    (3.0, 0.13),
    (5.0, 0.08),
)


def _bin_weight(index: int, count: int) -> float:
    """
    Stable 0.35..1.0 weight for one bin.
    """

    angle = index / max(1, count) * math.tau

    value = 0.0

    for harmonic, amount in _PROFILE_HARMONICS:
        value += amount * math.sin(angle * harmonic + harmonic * 1.7)

    # Map the roughly -1..1 sum onto a floor-limited range so no bar
    # ever fully disappears.
    return 0.35 + 0.65 * (0.5 + 0.5 * value)


class WaveformLayer(Layer):
    """
    A radial waveform around the core.

    Bars read the scene's amplitude history, which advances at a fixed
    rate, so the wave visibly travels around the ring as audio flows.
    Only LISTENING and SPEAKING give it any gain — outside those states
    the scene has already decayed amplitude to zero, so a late level
    message cannot leave the visualizer stuck.
    """

    name = "waveform"

    def visible(self, ctx: RenderContext) -> bool:
        return ctx.scene.style.waveform_gain > 0.01

    def draw(self, ctx: RenderContext) -> None:

        scene = ctx.scene
        style = scene.style

        gain = style.waveform_gain

        samples = scene.waveform()
        count = len(samples)

        if count == 0:
            return

        painter = ctx.painter

        base = scene.core_radius(ctx.half) * 1.55
        span = ctx.half * 0.20 * gain

        width = max(0.8, ctx.half * 0.0125)

        # Rotate slowly so the wave orbits rather than sitting still.
        offset = math.radians(scene.rotation * 0.5)

        peak_alpha = 0.0
        peak_angle = 0.0

        for index in range(count):

            value = samples[index]

            if value <= 0.004:
                continue

            weight = _bin_weight(index, count)

            length = span * value * weight

            if length <= 0.4:
                continue

            angle = offset + index * math.tau / count

            cos = math.cos(angle)
            sin = math.sin(angle)

            alpha = min(1.0, 0.28 + value * 0.72) * gain

            if alpha > peak_alpha:
                peak_alpha = alpha
                peak_angle = angle

            # Warm tips on the loudest bars only.
            colour = (
                style.secondary if value > 0.78 else style.primary
            )

            painter.setPen(
                QPen(
                    qcolor(colour, alpha),
                    width,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )

            painter.drawLine(
                ctx.centre.x() + cos * base,
                ctx.centre.y() + sin * base,
                ctx.centre.x() + cos * (base + length),
                ctx.centre.y() + sin * (base + length),
            )

        # A single bloom at the loudest bar, rather than one per bar:
        # the same visual payoff for a fraction of the cost.
        if ctx.quality == "high" and peak_alpha > 0.5:

            reach = base + span * 0.6

            ctx.draw_glow(
                ctx.half * 0.07,
                style.primary,
                0.2 * peak_alpha,
                QPointF(
                    ctx.centre.x() + math.cos(peak_angle) * reach,
                    ctx.centre.y() + math.sin(peak_angle) * reach,
                ),
            )


__all__ = ["WaveformLayer"]
