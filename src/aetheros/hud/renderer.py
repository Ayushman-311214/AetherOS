from __future__ import annotations

import time

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter

from .layers import (
    CoreLayer,
    Layer,
    ParticleLayer,
    PulseLayer,
    RingLayer,
    TextLayer,
    TickLayer,
    VignetteLayer,
    WaveformLayer,
)
from .paint import GlowCache, RenderContext
from .scene import Scene

#: Consecutive layer failures before a layer is retired for the rest
# of the session. A broken visual must degrade the overlay, not kill
# it — and must not spam the log at 60 Hz either.
_FAILURE_LIMIT = 3


class Renderer:
    """
    Draws the scene, back to front.

    Owns the layer stack and the glow cache. Each layer is isolated:
    one that raises is retired after a few failures and the rest keep
    drawing, so a rendering fault degrades the overlay instead of
    taking the window down.
    """

    def __init__(self) -> None:

        self._glow = GlowCache()

        #: Back to front. Vignette first so everything else sits on it;
        # text last so nothing draws over it.
        self._layers: list[Layer] = [
            VignetteLayer(),
            TickLayer(),
            RingLayer(),
            PulseLayer(),
            ParticleLayer(),
            WaveformLayer(),
            CoreLayer(),
            TextLayer(),
        ]

        self._failures: dict[str, int] = {}
        self._retired: set[str] = set()

        #: Reported to the caller so it can surface a warning once.
        self._last_error: str | None = None

    # ==========================================================
    # Accessors
    # ==========================================================

    @property
    def layers(self) -> tuple[Layer, ...]:
        return tuple(self._layers)

    @property
    def retired(self) -> frozenset[str]:
        return frozenset(self._retired)

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def take_error(self) -> str | None:
        """
        Read and clear the most recent layer failure.
        """

        error = self._last_error
        self._last_error = None

        return error

    def invalidate(self) -> None:
        """
        Drop cached pixmaps, e.g. after a resize or theme change.
        """

        self._glow.clear()

    # ==========================================================
    # Rendering
    # ==========================================================

    def render(
        self,
        painter: QPainter,
        scene: Scene,
        width: float,
        height: float,
        device_ratio: float = 1.0,
    ) -> float:
        """
        Draw one frame. Returns how long it took, in seconds.
        """

        started = time.perf_counter()

        self._glow.set_device_ratio(device_ratio)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            scene.quality != "low",
        )

        painter.setRenderHint(
            QPainter.RenderHint.TextAntialiasing,
            True,
        )

        context = RenderContext(
            painter=painter,
            scene=scene,
            glow=self._glow,
            centre=QPointF(width / 2.0, height / 2.0),
            half=min(width, height) / 2.0,
            width=width,
            height=height,
        )

        for layer in self._layers:

            if layer.name in self._retired:
                continue

            try:
                if not layer.visible(context):
                    continue

                # Every layer starts from a known pen/brush state, so
                # one layer's leftovers cannot corrupt the next.
                painter.save()

                try:
                    painter.setCompositionMode(
                        QPainter.CompositionMode.CompositionMode_SourceOver
                    )
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)

                    layer.draw(context)

                finally:
                    painter.restore()

                self._failures.pop(layer.name, None)

            except Exception as exc:
                self._record_failure(layer.name, exc)

        return time.perf_counter() - started

    # ==========================================================
    # Failure handling
    # ==========================================================

    def _record_failure(self, name: str, exc: Exception) -> None:

        count = self._failures.get(name, 0) + 1
        self._failures[name] = count

        # Only the first failure of a run is reported upward; after
        # that the counter does the talking.
        if count == 1:
            self._last_error = f"HUD layer '{name}' failed: {exc}"

        if count >= _FAILURE_LIMIT:
            self._retired.add(name)
            self._last_error = (
                f"HUD layer '{name}' disabled after "
                f"{count} failures: {exc}"
            )


__all__ = ["Renderer"]
