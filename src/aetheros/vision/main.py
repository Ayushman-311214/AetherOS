import asyncio

from pathlib import Path
from .image import Image

from .controller import VisionService
from .providers import paddleocr_provider
from .providers import opencv_provider

async def start():
    vision = VisionService(
        ocr=paddleocr_provider.PaddleOCRProvider(),
        cv=opencv_provider.OpenCVProvider(),
    )
    image_path = Path(__file__).parent / "test.png"

    image = Image.open(image_path)

    res = await vision.read_text(image)

    return res


if __name__ == "__main__":
    result = asyncio.run(start())
    print("Result ===", result)