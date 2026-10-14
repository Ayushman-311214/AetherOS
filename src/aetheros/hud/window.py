from __future__ import annotations

import sys
import time
from typing import Callable

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from .config import HUDConfig
from .renderer import Renderer
from .scene import Scene
from .state import HUDSnapshot, HUDState

#: Win32 constants for the click-through and no-activate styles.
_GWL_EXSTYLE = -20
_WS_EX_TRANSPARENT = 0x00000020
_WS_EX_LAYERED = 0x00080000
_WS_EX_NOACTIVATE = 0x08000000

#: Consecutive paint failures before the window gives up on the
# renderer and falls back to a minimal indicator.
_PAINT_FAILURE_LIMIT = 5


class HUDWindow(QWidget):
    """
    The overlay window.

    Frameless, translucent, DPI-aware and optionally click-through.
    Owns the frame timer and delegates all drawing to the Renderer;
    a paint failure degrades to a minimal indicator rather than
    killing the process.
    """

    def __init__(
        self,
        config: HUDConfig,
        *,
        on_close: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:

        super().__init__()

        self._config = config
        self._on_close = on_close
        self._on_error = on_error

        self._scene = Scene(config)
        self._renderer = Renderer()

        self._last_frame = time.perf_counter()
        self._paint_failures = 0
        self._degraded = False

        #: Drag origin while the window is being moved.
        self._drag_from: QPoint | None = None

        self._configure_window()
        self._apply_geometry()

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)

    # ==========================================================
    # Accessors
    # ==========================================================

    @property
    def scene(self) -> Scene:
        return self._scene

    @property
    def renderer(self) -> Renderer:
        return self._renderer

    @property
    def config(self) -> HUDConfig:
        return self._config

    @property
    def degraded(self) -> bool:
        """
        Whether the rich renderer has been abandoned.
        """

        return self._degraded

    # ==========================================================
    # Window setup
    # ==========================================================

    def _configure_window(self) -> None:
        """
        Apply frameless, translucent and stacking behaviour.
        """

        flags = (
            Qt.WindowType.FramelessWindowHint
            # Tool keeps the overlay out of the taskbar and the
            # alt-tab list, which is what makes it read as an
            # overlay rather than an application window.
            | Qt.WindowType.Tool
        )

        if self._config.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

        # Never steal focus from the terminal the user is typing in.
        self.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating,
            True,
        )

        self.setWindowTitle("AetherOS")

        self.setWindowOpacity(self._config.opacity)

        if not self._config.movable or self._config.click_through:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _apply_geometry(self) -> None:
        """
        Size the window and place it on the configured anchor.
        """

        edge = self._config.pixel_size

        self.setFixedSize(edge, edge)

        screen = self.screen()

        if screen is None:
            return

        area = screen.availableGeometry()
        margin = self._config.margin

        position = self._config.position.strip().lower()

        # An explicit "x,y" wins over the named anchors.
        if "," in position:
            try:
                x_text, y_text = position.split(",", 1)

                self.move(int(float(x_text)), int(float(y_text)))

                return

            except ValueError:
                position = "bottom-right"

        left = area.left() + margin
        right = area.right() - margin - edge
        top = area.top() + margin
        bottom = area.bottom() - margin - edge

        centre_x = area.left() + (area.width() - edge) // 2
        centre_y = area.top() + (area.height() - edge) // 2

        anchors = {
            "top-left": (left, top),
            "top-right": (right, top),
            "bottom-left": (left, bottom),
            "bottom-right": (right, bottom),
            "top": (centre_x, top),
            "bottom": (centre_x, bottom),
            "left": (left, centre_y),
            "right": (right, centre_y),
            "centre": (centre_x, centre_y),
            "center": (centre_x, centre_y),
        }

        self.move(*anchors.get(position, (right, bottom)))

    def apply_click_through(self) -> None:
        """
        Make the window ignore the mouse, if configured to.

        Qt's own WA_TransparentForMouseEvents is not enough on Windows:
        the compositor still routes clicks to the window unless the
        native extended style says otherwise. Must be called after the
        window has a native handle.
        """

        if not sys.platform.startswith("win"):
            # Qt's attribute is sufficient elsewhere.
            self.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                self._config.click_through,
            )

            return

        try:
            import ctypes

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]

            user32.GetWindowLongW.restype = ctypes.c_long
            user32.GetWindowLongW.argtypes = [
                ctypes.c_void_p,
                ctypes.c_int,
            ]

            user32.SetWindowLongW.restype = ctypes.c_long
            user32.SetWindowLongW.argtypes = [
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_long,
            ]

            handle = ctypes.c_void_p(int(self.winId()))

            style = user32.GetWindowLongW(handle, _GWL_EXSTYLE)

            # NOACTIVATE always: an overlay that takes focus when
            # clicked would interrupt whatever the user is typing.
            style |= _WS_EX_NOACTIVATE

            if self._config.click_through:
                style |= _WS_EX_TRANSPARENT | _WS_EX_LAYERED

            else:
                style &= ~_WS_EX_TRANSPARENT

            user32.SetWindowLongW(handle, _GWL_EXSTYLE, style)

        except Exception as exc:
            self._report(f"Could not apply click-through: {exc}")

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def start(self) -> None:
        """
        Show the overlay and begin animating.
        """

        self.show()

        # The native handle only exists once shown.
        self.apply_click_through()

        self._last_frame = time.perf_counter()

        self._timer.start(self._config.frame_interval_ms)

    def stop(self) -> None:
        """
        Stop animating and release cached pixmaps.
        """

        self._timer.stop()

        self._renderer.invalidate()

    # ==========================================================
    # State
    # ==========================================================

    def apply_snapshot(self, snapshot: HUDSnapshot) -> None:
        """
        Adopt a new state snapshot.
        """

        self._scene.apply(snapshot)

    def apply_config(self, config: HUDConfig) -> None:
        """
        Adopt new configuration, re-applying window properties.

        Rolls back on failure. Applying a config touches several pieces
        of window state in sequence, and a half-applied one would leave
        the overlay in a state no later message could repair.
        """

        was_running = self._timer.isActive()
        previous = self._config

        try:
            self._config = config

            self._scene.apply_config(config)
            self._renderer.invalidate()

            self._configure_window()
            self._apply_geometry()

            self.apply_click_through()

        except Exception as exc:

            self._config = previous

            try:
                self._scene.apply_config(previous)

            except Exception:
                pass

            self._report(f"Rejected HUD config: {exc}")

        finally:
            if was_running:
                self._timer.start(self._config.frame_interval_ms)

    # ==========================================================
    # Frame loop
    # ==========================================================

    def _tick(self) -> None:
        """
        Advance the animation and request a repaint.
        """

        now = time.perf_counter()
        delta = now - self._last_frame
        self._last_frame = now

        self._scene.advance(delta)

        # A stale ERROR settles back to IDLE on its own, so a dropped
        # message cannot leave the overlay showing a fault forever.
        if self._scene.should_return_to_idle():
            self._scene.apply(
                self._scene.snapshot.with_state(HUDState.IDLE)
            )

        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:

        painter = QPainter(self)

        try:
            if self._degraded:
                self._paint_minimal(painter)
                return

            duration = self._renderer.render(
                painter,
                self._scene,
                float(self.width()),
                float(self.height()),
                self.devicePixelRatioF(),
            )

            self._scene.record_frame(duration)

            error = self._renderer.take_error()

            if error is not None:
                self._report(error)

            self._paint_failures = 0

        except Exception as exc:

            self._paint_failures += 1

            if self._paint_failures == 1:
                self._report(f"HUD paint failed: {exc}")

            if self._paint_failures >= _PAINT_FAILURE_LIMIT:
                self._degrade(str(exc))

        finally:
            painter.end()

    def _paint_minimal(self, painter: QPainter) -> None:
        """
        The fallback indicator.

        Deliberately trivial — a single dot in the state colour. If even
        the simplest path is failing, the problem is not something the
        HUD can draw its way out of.
        """

        try:
            from .paint import qcolor

            style = self._scene.theme.style(str(self._scene.state))

            painter.setRenderHint(
                QPainter.RenderHint.Antialiasing,
                True,
            )

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(qcolor(style.primary, 0.85))

            radius = min(self.width(), self.height()) * 0.06

            painter.drawEllipse(
                self.rect().center(),
                int(radius),
                int(radius),
            )

        except Exception:
            # Nothing further to try.
            pass

    def _degrade(self, reason: str) -> None:
        """
        Abandon the rich renderer for the rest of the session.
        """

        if self._degraded:
            return

        self._degraded = True

        # Drop to 30 FPS. Deliberately a literal rather than derived
        # from config: this path runs precisely when something is
        # already wrong, and it must not be able to fail itself.
        try:
            self._timer.setInterval(33)

        except Exception:
            pass

        self._report(
            f"HUD rendering degraded to minimal mode: {reason}"
        )

    def _report(self, message: str) -> None:

        if self._on_error is not None:
            try:
                self._on_error(message)

            except Exception:
                pass

    # ==========================================================
    # Interaction
    # ==========================================================

    def mousePressEvent(self, event: QMouseEvent) -> None:

        if (
            self._config.movable
            and event.button() is Qt.MouseButton.LeftButton
        ):
            self._drag_from = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

            event.accept()

            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:

        origin = self._drag_from

        if origin is not None and (
            event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - origin)

            event.accept()

            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:

        self._drag_from = None

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:

        if event.key() == Qt.Key.Key_Escape:
            self.close()

            return

        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """
        Stop the timer before the window goes away.
        """

        self._timer.stop()

        if self._on_close is not None:
            try:
                self._on_close()

            except Exception:
                pass

        super().closeEvent(event)


__all__ = ["HUDWindow"]
