"""
Vision system for AetherOS.

Provides OCR, object detection, template matching,
and computer vision capabilities.
"""

from __future__ import annotations

from .controller import VisionService
from .image import Image
from .models.detection import Detection
from .models.match import TemplateMatch
from .models.text import TextBlock
from .providers.base import (
    BaseVisionProvider,
    DetectionProvider,
    OCRProvider,
    TemplateProvider,
    VisionProvider,
)
from .providers.opencv_provider import OpenCVProvider
from .providers.paddleocr_provider import PaddleOCRProvider
from .providers.template_provider import OpenCVTemplateProvider
from .providers.yolo_provider import YOLOProvider

__all__ = [
    # Core
    "VisionService",
    "Image",
    # Models
    "Detection",
    "TemplateMatch",
    "TextBlock",
    # Provider interfaces
    "BaseVisionProvider",
    "DetectionProvider",
    "OCRProvider",
    "TemplateProvider",
    "VisionProvider",
    # Concrete providers
    "OpenCVProvider",
    "PaddleOCRProvider",
    "OpenCVTemplateProvider",
    "YOLOProvider",
]
