"""Vision provider interfaces and implementations."""

from __future__ import annotations

from .base import (
    BaseVisionProvider,
    DetectionProvider,
    OCRProvider,
    TemplateProvider,
    VisionProvider,
)
from .opencv_provider import OpenCVProvider
from .paddleocr_provider import PaddleOCRProvider
from .template_provider import OpenCVTemplateProvider
from .yolo_provider import YOLOProvider

__all__ = [
    "BaseVisionProvider",
    "DetectionProvider",
    "OCRProvider",
    "TemplateProvider",
    "VisionProvider",
    "OpenCVProvider",
    "PaddleOCRProvider",
    "OpenCVTemplateProvider",
    "YOLOProvider",
]
