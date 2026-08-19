from __future__ import annotations

import cv2
import numpy as np

from ..image import Image
from ..models.match import TemplateMatch
from .base import TemplateProvider


class OpenCVTemplateProvider(TemplateProvider):
    """
    Template matching using OpenCV.
    """

    @property
    def name(self) -> str:
        return "OpenCV Template Matching"

    @property
    def version(self) -> str:
        return cv2.__version__

    # ==========================================================
    # Template Matching
    # ==========================================================

    async def find(
        self,
        image: Image,
        template: Image,
        threshold: float = 0.90,
        method: int = cv2.TM_CCOEFF_NORMED,
    ) -> list[TemplateMatch]:
        """
        Find template in image using OpenCV.

        Args:
            image: Source image to search in
            template: Template image to find
            threshold: Confidence threshold (0.0 - 1.0)
            method: OpenCV matching method

        Returns:
            List of matches above threshold
        """

        # Convert to grayscale for better matching
        img_gray = cv2.cvtColor(
            image.data,
            cv2.COLOR_BGR2GRAY,
        ) if image.channels == 3 else image.data

        template_gray = cv2.cvtColor(
            template.data,
            cv2.COLOR_BGR2GRAY,
        ) if template.channels == 3 else template.data

        # Perform template matching
        result = cv2.matchTemplate(
            img_gray,
            template_gray,
            method,
        )

        # Find locations above threshold
        locations = np.where(result >= threshold)

        matches: list[TemplateMatch] = []

        template_height, template_width = template_gray.shape

        # Group nearby matches
        for y, x in zip(*locations):

            confidence = float(result[y, x])

            # Check if this match is too close to existing ones
            is_duplicate = False

            for existing in matches:

                dx = abs(existing.x - x)
                dy = abs(existing.y - y)

                # If within 10 pixels, consider duplicate
                if dx < 10 and dy < 10:
                    # Keep higher confidence match
                    if confidence > existing.confidence:
                        matches.remove(existing)
                    else:
                        is_duplicate = True
                    break

            if not is_duplicate:
                matches.append(
                    TemplateMatch(
                        x=int(x),
                        y=int(y),
                        width=template_width,
                        height=template_height,
                        confidence=confidence,
                    )
                )

        # Sort by confidence
        matches.sort(
            key=lambda m: m.confidence,
            reverse=True,
        )

        return matches

    # ==========================================================
    # Multi-scale Matching
    # ==========================================================

    async def find_multiscale(
        self,
        image: Image,
        template: Image,
        threshold: float = 0.90,
        scales: list[float] | None = None,
    ) -> list[TemplateMatch]:
        """
        Find template at multiple scales.

        Useful when template size might vary.
        """

        if scales is None:
            scales = [0.8, 0.9, 1.0, 1.1, 1.2]

        all_matches: list[TemplateMatch] = []

        for scale in scales:

            # Resize template
            new_width = int(template.width * scale)
            new_height = int(template.height * scale)

            if new_width < 10 or new_height < 10:
                continue

            if new_width > image.width or new_height > image.height:
                continue

            scaled_template = cv2.resize(
                template.data,
                (new_width, new_height),
                interpolation=cv2.INTER_LINEAR,
            )

            scaled_template_img = Image(
                data=scaled_template,
                source=template.source,
            )

            # Find matches at this scale
            matches = await self.find(
                image,
                scaled_template_img,
                threshold,
            )

            all_matches.extend(matches)

        # Remove duplicates and sort
        all_matches.sort(
            key=lambda m: m.confidence,
            reverse=True,
        )

        return all_matches
