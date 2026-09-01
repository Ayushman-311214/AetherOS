"""How long does OCR actually take, cold then warm? The executor allows 30s."""
from __future__ import annotations
import asyncio, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

async def main() -> None:
    t0 = time.perf_counter()
    from aetheros.bootstrap.bootstrapper import Bootstrapper
    boot = Bootstrapper()
    await boot.start()
    print(f"bootstrap                 {time.perf_counter()-t0:7.2f}s")

    from aetheros.tools.registry import tool_registry
    from aetheros.tools.executor import ToolExecutor
    # Generous ceiling so we measure instead of truncating.
    ex = ToolExecutor(tool_registry, timeout_seconds=600)

    for label in ("cold", "warm"):
        t = time.perf_counter()
        r = await ex.execute_safe("read_screen_text", {})
        dt = time.perf_counter() - t
        text = (str(r.value)[:60] + "...") if r.ok else r.error
        print(f"read_screen_text {label:5}    {dt:7.2f}s  ok={r.ok}  {text}")

    await boot.shutdown()

asyncio.run(main())
