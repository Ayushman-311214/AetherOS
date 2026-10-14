from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPen

from ..paint import RenderContext, qcolor
from .base import Layer

#: Furthest a particle may orbit, as a fraction of the half-width.
# Matches the outer reach of the tick ring so the field stays within
# the same circular envelope as the rest of the geometry.
_MAX_ORBIT = 0.93

#: How many particles may carry a bloom. Each bloom is an additive
# pixmap blit — the single most expensive thing in the field — so this
# is capped rather than driven by a brightness threshold, which at full
# intensity would have meant roughly twenty blits every frame.
_MAX_GLOW_PARTICLES = 6


class ParticleLayer(Layer):
    """
    An orbiting particle field.

    Positions are a closed-form function of the scene clock rather than
    integrated velocities, so the field never drifts, costs nothing to
    seek, and looks identical on every run.
    """

    name = "particles"

    def visible(self, ctx: RenderContext) -> bool:
        return ctx.scene.style.particle_intensity > 0.01

    def draw(self, ctx: RenderContext) -> None:

        scene = ctx.scene
        style = scene.style

        painter = ctx.painter
        painter.setPen(Qt.PenStyle.NoPen)

        intensity = max(0.0, min(1.0, style.particle_intensity))

        spread = style.particle_spread
        phase = scene.orbit_phase
        now = scene.time

        # Trails only at the top tier, and only when the field is
        # actually moving fast enough for them to read as motion.
        trails = ctx.quality == "high" and style.particle_speed > 0.7

        trail_pen = QPen(
            qcolor(style.primary, 0.22 * intensity),
            max(0.5, ctx.half * 0.0035),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )

        visible = list(scene.visible_particles())

        # The field is sorted dim-first, so the brightest few are at
        # the end; only those earn a bloom.
        glow_from = (
            len(visible) - _MAX_GLOW_PARTICLES
            if ctx.quality == "high"
            else len(visible)
        )

        for index, particle in enumerate(visible):

            angle = particle.angle + phase * particle.speed

            orbit = particle.orbit + spread * math.sin(
                now * particle.wobble + particle.phase
            )

            # Keep the field inside the window. Without this, the
            # high-spread states (THINKING, EXECUTING) push particles
            # past the edge and they visibly clip against it.
            radius = ctx.half * min(orbit, _MAX_ORBIT)

            if radius <= 0.0:
                continue

            position = QPointF(
                ctx.centre.x() + math.cos(angle) * radius,
                ctx.centre.y() + math.sin(angle) * radius,
            )

            alpha = particle.brightness * (0.3 + 0.7 * intensity)

            # ----------------------------------------------
            # Trail
            # ----------------------------------------------

            if trails:

                lag = 0.09 * particle.speed * style.particle_speed

                behind = angle - lag

                painter.setPen(trail_pen)

                painter.drawLine(
                    QPointF(
                        ctx.centre.x() + math.cos(behind) * radius,
                        ctx.centre.y() + math.sin(behind) * radius,
                    ),
                    position,
                )

                painter.setPen(Qt.PenStyle.NoPen)

            # ----------------------------------------------
            # Dot
            # ----------------------------------------------

            size = particle.size * max(0.6, ctx.half / 170.0)

            # The warm accent appears on a minority of particles, which
            # keeps it a highlight rather than a second theme colour.
            colour = (
                style.secondary
                if particle.brightness > 0.88
                else style.primary
            )

            painter.setBrush(qcolor(colour, alpha))
            painter.drawEllipse(position, size, size)

            # A bloom on the brightest few only; this is the single
            # most expensive thing in the field.
            if index >= glow_from:
                ctx.draw_glow(
                    size * 4.0,
                    colour,
                    0.16 * alpha,
                    position,
                )
                painter.setPen(Qt.PenStyle.NoPen)


__all__ = ["ParticleLayer"]
