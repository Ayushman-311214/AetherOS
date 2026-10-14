"""
Vision performance benchmark — REAL numbers only.

Measures the stages that can actually run in the current environment and,
crucially, refuses to fabricate numbers for stages whose heavy dependencies are
absent. On this CPU-only box (torch+cpu, no ultralytics / paddleocr / paddle)
that means:

    measurable   : screen capture, region capture, and every cv2/PIL image
                   conversion the pipeline performs (without_alpha, bgr, gray,
                   resize, downscale-to-VISION_WIDTH, ascontiguousarray)
    unavailable  : object detection, OCR, grounding — the packages that do the
                   inference are not installed and CUDA is unavailable, so any
                   latency printed here would be invented rather than measured.

Run on a GPU/model-equipped machine to get the detection/OCR/grounding numbers;
this script auto-detects the packages and measures them when present.

    python .audit/vision_bench.py [iterations]
"""
from __future__ import annotations

import asyncio
import importlib.util
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402


def _have(pkg: str) -> bool:
    try:
        return importlib.util.find_spec(pkg) is not None
    except Exception:
        return False


def _cuda() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _bench(label: str, fn, iterations: int) -> None:
    """Time ``fn`` ``iterations`` times and print avg/min/max in ms."""
    samples: list[float] = []
    for _ in range(iterations):
        t = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t) * 1000.0)

    print(
        f"  {label:<34} "
        f"avg {statistics.mean(samples):8.2f}  "
        f"min {min(samples):8.2f}  "
        f"max {max(samples):8.2f}   ms   (n={iterations})"
    )


async def main() -> None:
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 20

    print("=" * 78)
    print("AetherOS Vision Benchmark")
    print("=" * 78)

    have_torch = _have("torch")
    torch_ver = "n/a"
    if have_torch:
        import torch

        torch_ver = torch.__version__

    print("Environment")
    print(f"  torch                 {torch_ver}")
    print(f"  cuda_available        {_cuda()}")
    print(f"  ultralytics installed {_have('ultralytics')}")
    print(f"  paddleocr installed   {_have('paddleocr')}")
    print(f"  paddle installed      {_have('paddle')}")
    print()

    from aetheros.config.config_loader import get_settings
    from aetheros.desktop.screen.controller import ScreenService
    from aetheros.desktop.screen.mss_backend import MSSScreen
    from aetheros.vision.image import Image

    settings = get_settings()
    print("Config")
    print(f"  VISION_WIDTH          {settings.VISION_WIDTH}  (0 = full res)")
    print(f"  VISION_FRAME_TTL_MS   {settings.VISION_FRAME_TTL_MS}")
    print(f"  VISION_DETECTION_IMGSZ {settings.VISION_DETECTION_IMGSZ}")
    print(f"  VISION_MODEL          {settings.VISION_MODEL}")
    print()

    # ----------------------------------------------------------
    # Capture (measurable everywhere with a display)
    # ----------------------------------------------------------
    screen = ScreenService(MSSScreen())

    print("Capture")

    # capture() is async, and we are already inside a running loop, so time it
    # inline with await rather than through the synchronous _bench helper.
    cap_iters = max(3, iterations // 2)
    cap_samples: list[float] = []
    frame = None
    for _ in range(cap_iters):
        t = time.perf_counter()
        frame = await screen.capture()
        cap_samples.append((time.perf_counter() - t) * 1000.0)

    print(
        f"  {'screen.capture (full)':<34} "
        f"avg {statistics.mean(cap_samples):8.2f}  "
        f"min {min(cap_samples):8.2f}  "
        f"max {max(cap_samples):8.2f}   ms   (n={cap_iters})"
    )

    h, w = frame.shape[0], frame.shape[1]
    print(f"  captured frame        {w}x{h}, channels={frame.shape[2] if frame.ndim == 3 else 1}")
    print()

    # ----------------------------------------------------------
    # Image conversions (the per-request preprocessing cost)
    # ----------------------------------------------------------
    img = Image.from_numpy(frame, source="bench", color_space="bgr")

    print("Image conversions")
    _bench("without_alpha()", lambda: img.without_alpha(), iterations)
    _bench("bgr()", lambda: img.bgr(), iterations)
    _bench("gray()", lambda: img.gray(), iterations)

    target_w = settings.VISION_WIDTH or 1280
    target_h = int(round(img.height * target_w / img.width))
    _bench(
        f"resize -> {target_w}x{target_h}",
        lambda: img.resize(target_w, target_h),
        iterations,
    )

    # The exact downscale PaddleOCRProvider._maybe_downscale performs.
    import cv2

    def _downscale() -> None:
        cv2.resize(
            frame[:, :, :3],
            (target_w, target_h),
            interpolation=cv2.INTER_AREA,
        )

    _bench(f"cv2 INTER_AREA -> w={target_w}", _downscale, iterations)
    _bench(
        "ascontiguousarray(:3)",
        lambda: np.ascontiguousarray(frame[:, :, :3]),
        iterations,
    )
    print()

    # ----------------------------------------------------------
    # Heavy stages — measured ONLY if the packages are present.
    # ----------------------------------------------------------
    print("Detection / OCR / Grounding")
    if not _have("ultralytics"):
        print("  detection             UNAVAILABLE -- not measured "
              "(ultralytics not installed)")
    if not (_have("paddleocr") or _have("paddle")):
        print("  ocr                   UNAVAILABLE -- not measured "
              "(paddleocr/paddle not installed)")
    if not _have("ultralytics") or not (_have("paddleocr") or _have("paddle")):
        print("  grounding             UNAVAILABLE -- not measured "
              "(depends on detection + ocr)")

    if _have("ultralytics") or _have("paddleocr"):
        # On an equipped machine, drive the real tools through the executor so
        # the numbers include model init (cold) then warm reuse.
        from aetheros.bootstrap.bootstrapper import Bootstrapper
        from aetheros.tools.executor import ToolExecutor
        from aetheros.tools.registry import tool_registry

        boot = Bootstrapper()
        await boot.start()
        ex = ToolExecutor(tool_registry, timeout_seconds=600)

        async def _time_tool(name: str, args: dict) -> None:
            for label in ("cold", "warm"):
                t = time.perf_counter()
                r = await ex.execute_safe(name, args)
                dt = (time.perf_counter() - t) * 1000.0
                print(f"  {name:<28} {label:<5} {dt:9.2f} ms  ok={r.ok}")

        if _have("ultralytics"):
            await _time_tool("detect_screen_objects", {})
        if _have("paddleocr"):
            await _time_tool("read_screen_text", {})
        if _have("ultralytics") and _have("paddleocr"):
            await _time_tool("ground_target", {"target": "the Search button"})

        await boot.shutdown()

    print()
    print("=" * 78)
    print("Note: any stage marked UNAVAILABLE was NOT measured. No inference")
    print("latency is reported for packages that are not installed.")
    print("=" * 78)


if __name__ == "__main__":
    asyncio.run(main())
