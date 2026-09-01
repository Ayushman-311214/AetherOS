from __future__ import annotations

from pathlib import Path
from typing import Any

import pyperclip

from ...core.errors.desktop_error import DesktopError
from ...core.interfaces.clipboard_controller import ClipboardController

# Windows clipboard format identifiers. Frozen Win32 API constants, spelled out
# here so this module does not need win32con at import time -- pywin32 is
# imported lazily, inside the one helper that needs it.
_CF_TEXT = 1
_CF_BITMAP = 2
_CF_TIFF = 6
_CF_OEMTEXT = 7
_CF_DIB = 8
_CF_UNICODETEXT = 13
_CF_HDROP = 15
_CF_DIBV5 = 17

# Formats grouped by the question a caller is actually asking. Groups rather than
# single formats because Windows *synthesises* related formats: putting
# CF_UNICODETEXT on the clipboard makes CF_TEXT and CF_OEMTEXT available too, and
# CF_BITMAP makes CF_DIB and CF_DIBV5 available. A synthesised format is genuinely
# retrievable, so "is any member of the group available" is the honest test for
# "can text be read from the clipboard right now".
_TEXT_FORMATS = (_CF_UNICODETEXT, _CF_TEXT, _CF_OEMTEXT)
_IMAGE_FORMATS = (_CF_DIB, _CF_DIBV5, _CF_BITMAP, _CF_TIFF)
_FILE_FORMATS = (_CF_HDROP,)


def _win32_clipboard() -> Any:
    """
    Return the ``win32clipboard`` module.

    Imported lazily so this module stays importable off Windows, and so the
    failure names the missing dependency instead of surfacing as an ImportError
    from inside a state query. Mirrors ``PyAutoGuiMouse.is_pressed``, which has
    the same platform-bound-capability shape.
    """

    try:
        import win32clipboard

    except ImportError as exc:
        raise DesktopError(
            code="CLIPBOARD_STATE_UNAVAILABLE",
            message="Inspecting clipboard formats requires pywin32.",
            hint="Install pywin32, or use paste_text and check for an empty string.",
            cause=exc,
        ) from exc

    return win32clipboard


class PyAutoGuiClipboard(ClipboardController):
    """
    Clipboard backend.

    Text transfer is implemented using pyperclip. Image and file *transfer*
    remain unsupported here and belong in a dedicated Win32 backend -- those
    methods raise, which is a missing capability rather than a wrong answer.

    Clipboard *state* queries, by contrast, are answered from the real Win32
    format list. They used to be answered from ``pyperclip.paste()``, which made
    all five of them lie:

    * ``has_image`` and ``has_files`` returned a hardcoded ``False`` -- reported
      as fact, not as "this backend cannot see that format".
    * ``has_text`` was ``bool(pyperclip.paste())``, so a deliberately copied
      empty string read as "no text at all".
    * ``is_empty`` was its inverse, so a clipboard holding an image or a file
      selection reported itself empty.
    * ``get_content_type`` fell through to ``"empty"`` for every non-text
      payload, so an image on the clipboard was described as nothing.

    Those answers feed the verification layer, whose entire job is to say
    whether an action really happened. A confidently wrong ``has_image`` there is
    worse than an error: it produces a verified-looking result for an action that
    never took place.

    ``clear`` has the same character and is fixed the same way: ``pyperclip.copy("")``
    leaves an empty text format *on* the clipboard and cannot displace an image
    or a file selection at all, so it reported success while the payload it was
    asked to remove survived. It now calls ``EmptyClipboard``.
    """

    def __init__(self) -> None:
        pass

    # ==========================================================
    # Internal
    # ==========================================================

    @staticmethod
    def _any_available(formats: tuple[int, ...]) -> bool:
        """
        Whether any of ``formats`` is currently on the clipboard.

        ``IsClipboardFormatAvailable`` deliberately does not require the
        clipboard to be opened, so this cannot fail with the access conflict that
        polling an owned clipboard would otherwise risk.
        """

        api = _win32_clipboard()

        return any(
            bool(api.IsClipboardFormatAvailable(fmt))
            for fmt in formats
        )

    # ==========================================================
    # Text
    # ==========================================================

    def copy_text(
        self,
        text: str,
    ) -> None:
        pyperclip.copy(text)

    def paste_text(self) -> str:
        return pyperclip.paste()

    # ==========================================================
    # Images
    # ==========================================================

    def copy_image(
        self,
        image: Any,
    ) -> None:
        raise NotImplementedError(
            "Image clipboard operations are not supported "
            "by the PyAutoGuiClipboard backend."
        )

    def paste_image(self) -> Any | None:
        raise NotImplementedError(
            "Image clipboard operations are not supported "
            "by the PyAutoGuiClipboard backend."
        )

    # ==========================================================
    # Files
    # ==========================================================

    def copy_files(
        self,
        paths: list[str | Path],
    ) -> None:
        raise NotImplementedError(
            "File clipboard operations are not supported "
            "by the PyAutoGuiClipboard backend."
        )

    def paste_files(self) -> list[Path]:
        raise NotImplementedError(
            "File clipboard operations are not supported "
            "by the PyAutoGuiClipboard backend."
        )

    # ==========================================================
    # Clipboard State
    # ==========================================================

    def clear(self) -> None:
        """
        Remove everything from the clipboard.

        ``EmptyClipboard`` rather than copying an empty string: the latter leaves
        a text format present and cannot displace an image or file selection, so
        it reported success without clearing what it was asked to clear.
        """

        api = _win32_clipboard()

        api.OpenClipboard()

        try:
            # Ownership transfers to this process on EmptyClipboard, which is
            # what actually discards every existing format.
            api.EmptyClipboard()

        finally:
            # In a finally block because leaving the clipboard open blocks every
            # other process on the machine from reading it.
            api.CloseClipboard()

    def has_text(self) -> bool:
        return self._any_available(_TEXT_FORMATS)

    def has_image(self) -> bool:
        return self._any_available(_IMAGE_FORMATS)

    def has_files(self) -> bool:
        return self._any_available(_FILE_FORMATS)

    def is_empty(self) -> bool:
        """
        Whether the clipboard holds no data of any format.

        Counting formats rather than testing for text: a clipboard carrying an
        image, a file selection, or an application's private format is not empty,
        however little text it contains.
        """

        api = _win32_clipboard()

        return api.CountClipboardFormats() == 0

    # ==========================================================
    # Utilities
    # ==========================================================

    def get_content_type(self) -> str:
        """
        Describe what the clipboard holds.

        Files are checked before images and images before text because Windows
        publishes several formats at once for richer payloads -- copying files in
        Explorer also offers their names as text -- and the most specific
        description is the useful one.

        ``"unknown"`` is returned when formats are present but none are
        recognised, which is the honest answer for an application's private
        format. Returning ``"empty"`` there, as this did, describes a populated
        clipboard as an empty one.
        """

        if self.has_files():
            return "files"

        if self.has_image():
            return "image"

        if self.has_text():
            return "text"

        if self.is_empty():
            return "empty"

        return "unknown"