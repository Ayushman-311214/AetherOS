from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image as PILImage


@dataclass(slots=True)
class Image:
    """
    Universal image model for AetherOS.

    Every vision module should consume and return this class.
    """

    data: np.ndarray

    source: str = "unknown"

    timestamp: datetime = field(
        default_factory=datetime.utcnow
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def width(self) -> int:
        return self.data.shape[1]

    @property
    def height(self) -> int:
        return self.data.shape[0]

    @property
    def channels(self) -> int:
        if len(self.data.shape) == 2:
            return 1

        return self.data.shape[2]

    @property
    def shape(self) -> tuple[int, ...]:
        return self.data.shape

    # ==========================================================
    # Color Space
    # ==========================================================

    def rgb(self) -> "Image":

        if self.channels == 3:
            rgb = cv2.cvtColor(
                self.data,
                cv2.COLOR_BGR2RGB,
            )
            return Image(
                rgb,
                source=self.source,
                metadata=self.metadata.copy(),
            )

        return self

    def bgr(self) -> "Image":

        if self.channels == 3:
            bgr = cv2.cvtColor(
                self.data,
                cv2.COLOR_RGB2BGR,
            )
            return Image(
                bgr,
                source=self.source,
                metadata=self.metadata.copy(),
            )

        return self

    def gray(self) -> "Image":

        if self.channels == 1:
            return self

        gray = cv2.cvtColor(
            self.data,
            cv2.COLOR_BGR2GRAY,
        )

        return Image(
            gray,
            source=self.source,
            metadata=self.metadata.copy(),
        )

    # ==========================================================
    # Resize
    # ==========================================================

    def resize(
        self,
        width: int,
        height: int,
    ) -> "Image":

        image = cv2.resize(
            self.data,
            (width, height),
        )

        return Image(
            image,
            source=self.source,
            metadata=self.metadata.copy(),
        )

    # ==========================================================
    # Crop
    # ==========================================================

    def crop(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> "Image":

        image = self.data[
            y:y + height,
            x:x + width,
        ]

        return Image(
            image,
            source=self.source,
            metadata=self.metadata.copy(),
        )

    # ==========================================================
    # Copy
    # ==========================================================

    def copy(self) -> "Image":

        return Image(
            self.data.copy(),
            source=self.source,
            metadata=self.metadata.copy(),
        )

    # ==========================================================
    # Save
    # ==========================================================

    def save(
        self,
        path: str | Path,
    ) -> None:

        PILImage.fromarray(
            self.rgb().data
        ).save(path)

    # ==========================================================
    # Conversion
    # ==========================================================

    def to_numpy(self) -> np.ndarray:

        return self.data

    def to_pillow(self) -> PILImage:

        return PILImage.fromarray(
            self.rgb().data
        )

    # ==========================================================
    # Constructors
    # ==========================================================

    @classmethod
    def from_numpy(
        cls,
        array: np.ndarray,
        source: str = "numpy",
    ) -> "Image":

        return cls(
            data=array,
            source=source,
        )

    @classmethod
    def open(
        cls,
        path: str | Path,
    ) -> "Image":

        image = PILImage.open(path)

        image = np.array(image)

        return cls(
            image,
            source=str(path),
        )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:

        return (
            f"Image("
            f"{self.width}x{self.height}, "
            f"channels={self.channels}, "
            f"source='{self.source}')"
        )