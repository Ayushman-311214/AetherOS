from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPen, QRadialGradient

from ..paint import RenderContext, qcolor
from .base import Layer


class CoreLayer(Layer):
    """
    The glowing central core.

    Drawn as stacked additive blooms under a hot inner disc, so it
    reads as a light source rather than a filled circle. Breathing and
    audio response both arrive through the scene's core radius.
    """

    name = "core"

    def draw(self, ctx: RenderContext) -> None:

        scene = ctx.scene
        style = scene.style

        radius = scene.core_radius(ctx.half)
        intensity = style.glow_intensity

        # ------------------------------------------------------
        # Outer bloom
        # ------------------------------------------------------

        passes = scene.glow_passes

        # Widest and faintest first. On "low" only the middle bloom
        # survives, which keeps the core recognisable at a third of
        # the cost.
        if passes >= 3:
            ctx.draw_glow(
                scene.glow_radius(ctx.half),
                style.glow,
                intensity * 0.3,
            )

        if passes >= 2:
            ctx.draw_glow(
                radius * 2.6,
                style.primary,
                intensity * 0.34,
            )

        ctx.draw_glow(
            radius * 1.5,
            style.primary,
            intensity * 0.55,
        )

        # ------------------------------------------------------
        # Inner disc
        # ------------------------------------------------------

        painter = ctx.painter

        gradient = QRadialGradient(ctx.centre, radius)

        # A white-hot centre is what separates "energy source" from
        # "coloured dot"; the primary colour only takes over further
        # out.
        gradient.setColorAt(0.0, qcolor((255, 255, 255), 0.95))
        gradient.setColorAt(0.35, qcolor(style.primary, 0.9))
        gradient.setColorAt(0.82, qcolor(style.primary, 0.42))
        gradient.setColorAt(1.0, qcolor(style.primary, 0.0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(ctx.centre, radius, radius)

        # ------------------------------------------------------
        # Rim
        # ------------------------------------------------------

        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(
            QPen(
                qcolor(style.primary, 0.75),
                max(0.8, ctx.half * 0.006),
            )
        )

        painter.drawEllipse(
            ctx.centre,
            radius * 1.16,
            radius * 1.16,
        )

        # A second, tighter rim in the warm accent colour, offset by
        # the breath so the two never sit exactly together.
        wobble = 1.0 + 0.03 * math.sin(scene.time * 1.7)

        painter.setPen(
            QPen(
                qcolor(style.secondary, 0.26 * intensity),
                max(0.6, ctx.half * 0.004),
            )
        )

        painter.drawEllipse(
            ctx.centre,
            radius * 1.34 * wobble,
            radius * 1.34 * wobble,
        )

        # ------------------------------------------------------
        # Amplitude spike
        # ------------------------------------------------------

        # A brief hot flash on transients, so loud speech visibly
        # strikes the core instead of merely scaling it.
        if style.amplitude_response > 0.0 and scene.amplitude > 0.55:

            flash = (scene.amplitude - 0.55) / 0.45

            ctx.draw_glow(
                radius * 1.1,
                (255, 255, 255),
                0.3 * flash * style.amplitude_response,
            )


class VignetteLayer(Layer):
    """
    A barely-there radial wash behind everything.

    Gives the luminous elements something to sit against without
    filling the window: the corners stay genuinely transparent so the
    overlay never looks like a floating rectangle.
    """

    name = "vignette"

    def visible(self, ctx: RenderContext) -> bool:
        return ctx.quality != "low"

    def draw(self, ctx: RenderContext) -> None:

        theme = ctx.scene.theme

        gradient = QRadialGradient(ctx.centre, ctx.half)

        # Kept deliberately faint with a fast falloff. Enough to give
        # the luminous elements something to sit against on a light
        # desktop; not enough to read as a dark disc floating on the
        # screen, which is exactly what an overlay must not look like.
        gradient.setColorAt(0.0, qcolor(theme.background, 0.34))
        gradient.setColorAt(0.45, qcolor(theme.background, 0.19))
        gradient.setColorAt(0.75, qcolor(theme.background, 0.055))
        gradient.setColorAt(1.0, qcolor(theme.background, 0.0))

        ctx.painter.setPen(Qt.PenStyle.NoPen)
        ctx.painter.setBrush(gradient)

        ctx.painter.drawEllipse(
            QPointF(ctx.centre),
            ctx.half,
            ctx.half,
        )


__all__ = [
    "CoreLayer",
    "VignetteLayer",
]
