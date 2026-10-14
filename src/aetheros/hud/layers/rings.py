from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPen

from ..paint import RenderContext, qcolor
from ..scene import PULSE_LIFETIME
from .base import Layer


@dataclass(frozen=True, slots=True)
class RingSpec:
    """
    One arc group in the ring system.
    """

    #: Radius as a fraction of the half-width.
    radius: float

    #: How many evenly spaced arc segments.
    segments: int

    #: Fraction of each segment's slot that is drawn; the rest is gap.
    coverage: float

    #: +1 rotates with the primary direction, -1 counter-rotates.
    direction: float

    #: Stroke width as a fraction of the half-width.
    width: float

    #: Draw in the warm accent colour rather than the primary.
    warm: bool

    #: Base opacity before the state's ring intensity is applied.
    alpha: float


#: The ring system. Radii, segment counts and directions are chosen so
# no two groups share a period — the arcs never visually lock into a
# single rotating object, which is what makes the machinery read as
# many independent parts.
_RINGS = (
    RingSpec(0.44, 3, 0.80, 1.0, 0.011, False, 0.90),
    RingSpec(0.545, 6, 0.52, -1.0, 0.006, False, 0.62),
    RingSpec(0.645, 2, 0.28, 1.0, 0.015, True, 0.50),
    RingSpec(0.735, 11, 0.34, -1.0, 0.005, False, 0.46),
    RingSpec(0.84, 4, 0.16, 1.0, 0.008, True, 0.34),
)

#: Groups dropped on the "low" tier, cheapest visual loss first.
_LOW_QUALITY_RINGS = 2


class RingLayer(Layer):
    """
    Concentric rotating arc groups.

    The dominant structural element: thin technical arcs at several
    radii, counter-rotating at unrelated speeds.
    """

    name = "rings"

    def draw(self, ctx: RenderContext) -> None:

        scene = ctx.scene
        style = scene.style

        intensity = style.ring_intensity

        if intensity <= 0.01:
            return

        painter = ctx.painter
        painter.setBrush(Qt.BrushStyle.NoBrush)

        rings = _RINGS

        if ctx.quality == "low":
            rings = rings[:_LOW_QUALITY_RINGS]

        for spec in rings:

            radius = ctx.radius(spec.radius)

            if radius <= 1.0:
                continue

            rotation = (
                scene.rotation
                if spec.direction > 0
                else scene.counter_rotation
            )

            colour = style.secondary if spec.warm else style.primary

            painter.setPen(
                QPen(
                    qcolor(colour, spec.alpha * intensity),
                    max(0.7, ctx.half * spec.width),
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )

            box = QRectF(
                ctx.centre.x() - radius,
                ctx.centre.y() - radius,
                radius * 2.0,
                radius * 2.0,
            )

            slot = 360.0 / spec.segments
            span = slot * spec.coverage

            for index in range(spec.segments):

                start = rotation + index * slot

                # Qt measures arcs in 1/16th degrees, counterclockwise
                # from three o'clock.
                painter.drawArc(
                    box,
                    int(round(start * 16.0)),
                    int(round(span * 16.0)),
                )


class TickLayer(Layer):
    """
    A ring of fine radial graduations.

    Pure technical texture — the detail that makes the overlay look
    instrumented rather than merely decorative.
    """

    name = "ticks"

    #: Graduations around the circle.
    COUNT = 60

    def visible(self, ctx: RenderContext) -> bool:
        return ctx.quality != "low"

    def draw(self, ctx: RenderContext) -> None:

        scene = ctx.scene
        style = scene.style

        intensity = style.ring_intensity

        if intensity <= 0.01:
            return

        painter = ctx.painter

        base = ctx.radius(0.895)

        # Drift the other way from the inner arcs, and much slower.
        offset = math.radians(-scene.rotation * 0.22)

        short = ctx.half * 0.022
        long = ctx.half * 0.05

        pen = QPen(
            qcolor(style.primary, 0.34 * intensity),
            max(0.6, ctx.half * 0.0042),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.FlatCap,
        )

        accent = QPen(
            qcolor(style.secondary, 0.5 * intensity),
            max(0.7, ctx.half * 0.0055),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.FlatCap,
        )

        for index in range(self.COUNT):

            angle = offset + index * math.tau / self.COUNT

            major = index % 5 == 0

            painter.setPen(accent if major else pen)

            length = long if major else short

            cos = math.cos(angle)
            sin = math.sin(angle)

            painter.drawLine(
                ctx.centre.x() + cos * base,
                ctx.centre.y() + sin * base,
                ctx.centre.x() + cos * (base + length),
                ctx.centre.y() + sin * (base + length),
            )


class PulseLayer(Layer):
    """
    Rings expanding outward from the core.

    Emitted by the scene at a state-dependent rate, faster when the
    user is actually speaking, so LISTENING looks like it is receiving
    something rather than just idling brightly.
    """

    name = "pulses"

    def visible(self, ctx: RenderContext) -> bool:
        return bool(ctx.scene.pulses)

    def draw(self, ctx: RenderContext) -> None:

        scene = ctx.scene
        style = scene.style

        painter = ctx.painter
        painter.setBrush(Qt.BrushStyle.NoBrush)

        inner = scene.core_radius(ctx.half) * 1.2
        outer = ctx.radius(0.94)

        now = scene.time

        for pulse in scene.pulses:

            progress = pulse.progress(now)

            if progress <= 0.0 or progress >= 1.0:
                continue

            # Ease outward so the ring leaves the core quickly and
            # slows as it fades, which looks like energy dissipating.
            eased = 1.0 - (1.0 - progress) ** 2.2

            radius = inner + (outer - inner) * eased

            # Fade faster than it travels, so the outer edge is never a
            # hard visible boundary.
            alpha = (1.0 - progress) ** 1.7 * 0.6 * style.ring_intensity

            if alpha <= 0.006:
                continue

            painter.setPen(
                QPen(
                    qcolor(style.primary, alpha),
                    max(
                        0.6,
                        ctx.half * 0.009 * (1.0 - progress * 0.6),
                    ),
                )
            )

            painter.drawEllipse(ctx.centre, radius, radius)

        # The newest pulse gets a faint bloom at its leading edge, but
        # only where there is budget for it.
        if ctx.quality == "high" and scene.pulses:

            newest = scene.pulses[-1]
            progress = newest.progress(now)

            if 0.0 < progress < 0.55:
                ctx.draw_glow(
                    inner + (outer - inner) * progress,
                    style.glow,
                    0.1 * (1.0 - progress / 0.55),
                )


#: Exposed so tests can assert the pulse geometry matches the scene's
# lifetime without importing private names.
PULSE_SECONDS = PULSE_LIFETIME


__all__ = [
    "PULSE_SECONDS",
    "PulseLayer",
    "RingLayer",
    "RingSpec",
    "TickLayer",
]
