"""Fonts for PYDEX text rendering.

A :class:`Font` loads a TrueType/OpenType font file (``.ttf``/``.otf``)
directly from disk at a given size.  Custom fonts load from wherever the
developer keeps them (e.g. a project ``assets/fonts/`` folder); PYDEX never
installs fonts into the operating system.

Paths: relative paths resolve against the process working directory (like
image loading), absolute paths are used as-is.  Missing files raise a clear
:class:`~pydex_ge.exceptions.BackendError`.

When no path is given, PYDEX falls back to a system font if one can be
found; custom fonts always take priority over that search.
"""

from __future__ import annotations

import os
import sys

from ..backend import select_backend
from ..backend.base import Backend, BackendFont
from ..check import _caller_info
from ..exceptions import ConfigurationError, MissingAssetError
from .color import normalize_rgba
from .image import Image


def _system_font_candidates() -> list[str]:
    candidates = []
    if sys.platform.startswith("win"):
        fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        for name in (
            "arial.ttf",
            "arialbd.ttf",
            "segoeui.ttf",
            "consola.ttf",
            "calibri.ttf",
            "tahoma.ttf",
            "times.ttf",
        ):
            candidates.append(os.path.join(fonts_dir, name))
    elif sys.platform == "darwin":
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttf",
                "/System/Library/Fonts/SFNS.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
            ]
        )
    return candidates


def _find_system_font() -> str | None:
    """Return the first usable system font path, or ``None`` if none exist."""
    for path in _system_font_candidates():
        try:
            if os.path.isfile(path):
                return path
        except OSError:
            continue
    return None


class Font:
    """A loaded font file at a fixed size.

    Parameters
    ----------
    path:
        Path to a ``.ttf``/``.otf`` font file.  Relative paths are resolved
        against the process working directory.  When ``None``, a system font
        is searched as a fallback.
    size:
        Font size in points.
    backend:
        Backend used to load the font.  Defaults to SDL2 (or
        ``PYDEX_BACKEND``).
    """

    def __init__(
        self,
        path: str | None = None,
        size: int = 24,
        *,
        backend: Backend | None = None,
    ) -> None:
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ConfigurationError("Font size must be a positive integer.")
        self._backend = backend if backend is not None else select_backend()
        if path is None:
            path = _find_system_font()
            if path is None:
                raise ConfigurationError(
                    "No font path was given and no system font could be found. "
                    "Pass a font file path, e.g. pydex_ge.Font('assets/fonts/MyGameFont.ttf')."
                )
        if not isinstance(path, str) or not path.strip():
            raise ConfigurationError("Font path must be a non-empty string.")
        self.path = os.path.abspath(path)
        self.size = size
        try:
            self._font: BackendFont = self._backend.load_font(self.path, size)
        except MissingAssetError as exc:
            if exc.requested_by is None:
                exc.requested_by = _caller_info()
            raise
        self._destroyed = False

    def _check(self) -> None:
        if self._destroyed:
            raise RuntimeError("Cannot use a font after it has been destroyed.")

    @property
    def _backend_font(self) -> BackendFont:
        self._check()
        return self._font

    def measure(self, text: str) -> tuple[int, int]:
        """Return the ``(width, height)`` in pixels the text would occupy."""
        self._check()
        if not isinstance(text, str):
            raise ConfigurationError("Text must be a string.")
        return self._font.measure_text(text)

    def render(self, text: str, color: object = (255, 255, 255)) -> Image:
        """Render the text to a new :class:`~pydex_ge.graphics.image.Image`."""
        self._check()
        if not isinstance(text, str):
            raise ConfigurationError("Text must be a string.")
        rgba = normalize_rgba(color)
        backend_image = self._font.render_text(text, rgba)
        return Image._from_backend_image(backend_image, backend=self._backend)

    def destroy(self) -> None:
        """Free the font.  Idempotent."""
        if self._destroyed:
            return
        self._font.destroy()
        self._destroyed = True


__all__ = ["Font", "_find_system_font"]
