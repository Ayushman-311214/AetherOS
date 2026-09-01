from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QFontMetricsF, QPen

from ..paint import RenderContext, qcolor
from ..state import HUDState
from ..theme import RGB
from .base import Layer

#: Windows-first font stacks, with fallbacks so the overlay still
# renders sensibly if a family is missing.
_DISPLAY_FAMILIES = "Segoe UI Semibold, Segoe UI, Arial, sans-serif"
_TECHNICAL_FAMILIES = "Consolas, Cascadia Mono, Courier New, monospace"


def _font(
    families: str,
    size: float,
    *,
    tracking: float = 0.0,
    weight: QFont.Weight = QFont.Weight.Normal,
) -> QFont:
    """
    Build a font, scaled and optionally letterspaced.
    """

    font = QFont()
    font.setFamilies([name.strip() for name in families.split(",")])
    font.setPointSizeF(max(6.0, size))
    font.setWeight(weight)

    if tracking:
        font.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing,
            tracking,
        )

    return font


class TextLayer(Layer):
    """
    The overlay's text: identity, state, and one line of context.

    Held deliberately to three short lines. The HUD is a status
    indicator, not a dashboard — anything longer belongs in the CLI.
    """

    name = "text"

    def draw(self, ctx: RenderContext) -> None:

        scene = ctx.scene
        config = scene.config

        painter = ctx.painter

        # Text should not inherit additive compositing from a glow.
        painter.setCompositionMode(
            painter.CompositionMode.CompositionMode_SourceOver
        )

        self._draw_title(ctx)

        if config.show_status:
            self._draw_state(ctx)

        if not config.show_transcript:
            return

        content, colour = self._content(ctx)

        if not content:
            return

        self._draw_line(
            ctx,
            content,
            colour,
            y=ctx.centre.y() + ctx.half * 0.60,
            size=ctx.half * 0.058,
            families=_TECHNICAL_FAMILIES,
            alpha=0.72,
        )

    # ==========================================================
    # Elements
    # ==========================================================

    def _draw_title(self, ctx: RenderContext) -> None:
        """
        The wordmark, above the core.
        """

        theme = ctx.scene.theme

        font = _font(
            _DISPLAY_FAMILIES,
            ctx.half * 0.082,
            tracking=max(1.5, ctx.half * 0.026),
            weight=QFont.Weight.DemiBold,
        )

        ctx.painter.setFont(font)
        ctx.painter.setPen(QPen(qcolor(theme.text, 0.5)))

        self._centred(
            ctx,
            "AETHEROS",
            ctx.centre.y() - ctx.half * 0.60,
            font,
        )

    def _draw_state(self, ctx: RenderContext) -> None:
        """
        The state name, below the core, with flanking rules.
        """

        style = ctx.scene.style

        label = style.label

        font = _font(
            _TECHNICAL_FAMILIES,
            ctx.half * 0.066,
            tracking=max(1.0, ctx.half * 0.018),
        )

        ctx.painter.setFont(font)
        ctx.painter.setPen(QPen(qcolor(style.primary, 0.9)))

        y = ctx.centre.y() + ctx.half * 0.44

        self._centred(ctx, label, y, font)

        # Short rules either side, sized to the text: a technical
        # flourish that also visually separates state from transcript.
        metrics = QFontMetricsF(font)
        half_text = metrics.horizontalAdvance(label) / 2.0

        gap = ctx.half * 0.05
        length = ctx.half * 0.13

        ctx.painter.setPen(
            QPen(
                qcolor(style.primary, 0.32),
                max(0.6, ctx.half * 0.004),
            )
        )

        for direction in (-1.0, 1.0):

            start = ctx.centre.x() + direction * (half_text + gap)
            end = start + direction * length

            ctx.painter.drawLine(start, y, end, y)

    def _draw_line(
        self,
        ctx: RenderContext,
        text: str,
        colour: RGB,
        *,
        y: float,
        size: float,
        families: str,
        alpha: float,
    ) -> None:
        """
        One elided, centred line of secondary text.
        """

        font = _font(families, size)

        ctx.painter.setFont(font)
        ctx.painter.setPen(QPen(qcolor(colour, alpha)))

        limit = ctx.scene.config.max_text_length

        trimmed = text if len(text) <= limit else text[:limit]

        metrics = QFontMetricsF(font)

        available = ctx.half * 1.5

        self._centred(
            ctx,
            metrics.elidedText(
                trimmed,
                Qt.TextElideMode.ElideRight,
                available,
            ),
            y,
            font,
        )

    # ==========================================================
    # Content selection
    # ==========================================================

    def _content(
        self,
        ctx: RenderContext,
    ) -> tuple[str, RGB]:
        """
        Choose the single most relevant line for this moment.
        """

        scene = ctx.scene
        snapshot = scene.snapshot
        theme = scene.theme
        state = snapshot.state

        if state is HUDState.ERROR and snapshot.message:
            return snapshot.message, scene.style.primary

        if state is HUDState.EXECUTING and snapshot.action:
            return f"> {snapshot.action}", scene.style.secondary

        if state is HUDState.SPEAKING and snapshot.response:
            return snapshot.response, theme.text

        if snapshot.transcript:
            return f'"{snapshot.transcript}"', theme.text_dim

        return "", theme.text_dim

    # ==========================================================
    # Helpers
    # ==========================================================

    def _centred(
        self,
        ctx: RenderContext,
        text: str,
        y: float,
        font: QFont,
    ) -> None:
        """
        Draw text centred horizontally on the given baseline row.
        """

        metrics = QFontMetricsF(font)
        height = metrics.height()

        box = QRectF(
            ctx.centre.x() - ctx.width / 2.0,
            y - height / 2.0,
            ctx.width,
            height,
        )

        ctx.painter.drawText(
            box,
            int(
                Qt.AlignmentFlag.AlignHCenter
                | Qt.AlignmentFlag.AlignVCenter
            ),
            text,
        )


__all__ = ["TextLayer"]
