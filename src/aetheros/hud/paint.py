from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPixmap,
    QRadialGradient,
)

from .scene import Scene
from .theme import RGB

#: Cache granularity. Radii are bucketed to this many pixels and
# alphas to this many levels, which keeps the number of distinct glow
# pixmaps small while remaining visually continuous.
_RADIUS_BUCKET = 3.0
_ALPHA_BUCKET = 10

#: Above this many cached pixmaps the cache is dropped wholesale.
# Simpler than an LRU and adequate: the working set is a handful of
# radii per state, and a state change is exactly when discarding is
# cheap.
_MAX_CACHE = 96


def qcolor(rgb: RGB, alpha: float = 1.0) -> QColor:
    """
    Convert a theme colour and 0..1 alpha into a QColor.
    """

    return QColor(
        rgb[0],
        rgb[1],
        rgb[2],
        max(0, min(255, int(round(alpha * 255.0)))),
    )


class GlowCache:
    """
    Pre-rendered radial glows.

    Radial gradients are by far the most expensive part of this visual
    language, and the same few appear every frame. Rendering each once
    into a pixmap and blitting it additively is what makes the look
    affordable at 60 FPS.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[int, int, int, int, int], QPixmap] = {}
        self._ratio = 1.0

    @property
    def size(self) -> int:
        return len(self._cache)

    def set_device_ratio(self, ratio: float) -> None:
        """
        Set the device pixel ratio.

        Cached pixmaps are rendered at physical resolution, so a move
        between displays with different scaling invalidates them.
        """

        value = max(1.0, float(ratio))

        if abs(value - self._ratio) > 0.01:
            self._ratio = value
            self._cache.clear()

    def clear(self) -> None:
        self._cache.clear()

    def glow(
        self,
        radius: float,
        colour: RGB,
        alpha: float,
    ) -> QPixmap:
        """
        A soft circular glow of the given radius and colour.
        """

        bucket = self._key(radius, colour, alpha)

        cached = self._cache.get(bucket)

        if cached is not None:
            return cached

        if len(self._cache) >= _MAX_CACHE:
            self._cache.clear()

        pixmap = self._render(bucket)

        self._cache[bucket] = pixmap

        return pixmap

    # ----------------------------------------------------------
    # Internals
    # ----------------------------------------------------------

    def _key(
        self,
        radius: float,
        colour: RGB,
        alpha: float,
    ) -> tuple[int, int, int, int, int]:

        return (
            max(1, int(round(radius / _RADIUS_BUCKET))),
            colour[0] // 4,
            colour[1] // 4,
            colour[2] // 4,
            max(
                0,
                min(
                    _ALPHA_BUCKET,
                    int(round(alpha * _ALPHA_BUCKET)),
                ),
            ),
        )

    def _render(
        self,
        key: tuple[int, int, int, int, int],
    ) -> QPixmap:

        radius = key[0] * _RADIUS_BUCKET
        colour = (key[1] * 4, key[2] * 4, key[3] * 4)
        alpha = key[4] / _ALPHA_BUCKET

        edge = int(round(radius * 2.0))
        physical = max(2, int(round(edge * self._ratio)))

        pixmap = QPixmap(physical, physical)
        pixmap.setDevicePixelRatio(self._ratio)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)

        try:
            painter.setRenderHint(
                QPainter.RenderHint.Antialiasing,
                True,
            )

            centre = QPointF(edge / 2.0, edge / 2.0)

            gradient = QRadialGradient(centre, radius)

            # A steep inner falloff plus a long tail reads as light
            # bloom rather than as a flat translucent disc.
            gradient.setColorAt(0.0, qcolor(colour, alpha))
            gradient.setColorAt(0.18, qcolor(colour, alpha * 0.72))
            gradient.setColorAt(0.42, qcolor(colour, alpha * 0.3))
            gradient.setColorAt(0.7, qcolor(colour, alpha * 0.09))
            gradient.setColorAt(1.0, qcolor(colour, 0.0))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawEllipse(centre, radius, radius)

        finally:
            painter.end()

        return pixmap


@dataclass(slots=True)
class RenderContext:
    """
    Everything a layer needs to draw one frame.
    """

    painter: QPainter
    scene: Scene
    glow: GlowCache

    #: Centre of the overlay, in logical pixels.
    centre: QPointF

    #: Half the shorter edge: the radius everything is expressed in.
    half: float

    width: float
    height: float

    @property
    def quality(self) -> str:
        return self.scene.quality

    def radius(self, fraction: float) -> float:
        """
        Convert a fraction of the half-width into pixels.
        """

        return self.half * fraction

    def draw_glow(
        self,
        radius: float,
        colour: RGB,
        alpha: float,
        centre: QPointF | None = None,
    ) -> None:
        """
        Blit an additive glow.

        Additive compositing is what makes overlapping energy read as
        light instead of as stacked translucent shapes.
        """

        if radius <= 0.5 or alpha <= 0.004:
            return

        pixmap = self.glow.glow(radius, colour, alpha)

        at = centre or self.centre

        # Pixmaps are device-pixel sized but positioned logically.
        edge = pixmap.width() / pixmap.devicePixelRatio()

        previous = self.painter.compositionMode()

        self.painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Plus
        )

        self.painter.drawPixmap(
            QPointF(at.x() - edge / 2.0, at.y() - edge / 2.0),
            pixmap,
        )

        self.painter.setCompositionMode(previous)


def sweep_gradient(
    centre: QPointF,
    radius: float,
    colour: RGB,
    alpha: float,
) -> QLinearGradient:
    """
    A directional fade across a ring, used to make arcs look lit from
    one side rather than uniformly bright.
    """

    gradient = QLinearGradient(
        centre.x() - radius,
        centre.y() - radius,
        centre.x() + radius,
        centre.y() + radius,
    )

    gradient.setColorAt(0.0, qcolor(colour, alpha * 0.15))
    gradient.setColorAt(0.5, qcolor(colour, alpha))
    gradient.setColorAt(1.0, qcolor(colour, alpha * 0.2))

    return gradient


__all__ = [
    "GlowCache",
    "RenderContext",
    "qcolor",
    "sweep_gradient",
]
