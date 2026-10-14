from __future__ import annotations

from abc import ABC, abstractmethod

from ..paint import RenderContext


class Layer(ABC):
    """
    One element of the overlay, drawn back to front.

    Layers are stateless with respect to animation: everything that
    changes over time lives in the Scene, so a layer is a pure function
    from scene to pixels. That keeps ordering, quality and state
    handling in one place instead of spread across the visuals.
    """

    #: Identifies the layer in logs and quality decisions.
    name: str = "layer"

    def visible(self, ctx: RenderContext) -> bool:
        """
        Whether this layer should draw at all this frame.
        """

        return True

    @abstractmethod
    def draw(self, ctx: RenderContext) -> None:
        """
        Paint this layer.
        """


__all__ = ["Layer"]
