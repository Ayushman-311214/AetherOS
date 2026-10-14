from .clipboard.pyautogui_backend import PyAutoGuiClipboard
from .mouse.pyautogui_backend import PyAutoGuiMouse
from .keyboard.pyautogui_backend import PyAutoGuiKeyboard
from .screen.mss_backend import MSSScreen
from .process.psutil_backend import PsutilProcess
from .window.win32_backend import Win32Window


def status() -> dict[str, str]:
    """Return the current desktop subsystem status."""

    mouse = PyAutoGuiMouse.is_available()
    keyboard = PyAutoGuiKeyboard.is_available()
    clipboard = PyAutoGuiClipboard.is_available()
    screen = MSSScreen.is_available()
    process = PsutilProcess.is_available()
    window = Win32Window.is_available()

    return {
        "status": (
            "OK"
            if all((mouse, keyboard, clipboard, screen, process, window))
            else "DEGRADED"
        ),
        "mouse": True if mouse else "UNAVAILABLE",
        "keyboard": True if keyboard else "UNAVAILABLE",
        "clipboard": True if clipboard else "UNAVAILABLE",
        "screen": True if screen else "UNAVAILABLE",
        "process": True if process else "UNAVAILABLE",
        "window": True if window else "UNAVAILABLE",
    }
