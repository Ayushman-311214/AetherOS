"""Is move_relative's round trip exact? §6 'incorrect coordinate handling'."""
from __future__ import annotations
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyautogui
from aetheros.desktop.mouse.pyautogui_backend import PyAutoGuiMouse

async def main() -> None:
    backend = PyAutoGuiMouse()
    print(f"pyautogui {pyautogui.__version__}   FAILSAFE={pyautogui.FAILSAFE}")
    print(f"screen={pyautogui.size()}\n")

    # Start from a known interior point so no edge clamping is involved.
    pyautogui.moveTo(900, 500)
    print(f"anchor           -> {backend.position()}")

    for delta in (5, 20, 100):
        start = backend.position()
        backend.move_relative(delta, 0)
        after_out = backend.position()
        backend.move_relative(-delta, 0)
        after_back = backend.position()
        print(
            f"delta={delta:>4}  {start} -> {after_out} -> {after_back}   "
            f"out={after_out[0]-start[0]:+}  back={after_back[0]-after_out[0]:+}  "
            f"{'OK' if after_back == start else 'DRIFT'}"
        )

    # And the raw library, to place the blame correctly.
    print()
    pyautogui.moveTo(900, 500)
    for delta in (5, 20, 100):
        start = pyautogui.position()
        pyautogui.moveRel(delta, 0)
        mid = pyautogui.position()
        pyautogui.moveRel(-delta, 0)
        end = pyautogui.position()
        print(
            f"raw pyautogui delta={delta:>4}  {tuple(start)} -> {tuple(mid)} -> "
            f"{tuple(end)}   {'OK' if tuple(end) == tuple(start) else 'DRIFT'}"
        )

asyncio.run(main())
