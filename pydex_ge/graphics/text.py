"""The :class:`Text` renderable: a string drawn with a font.

A :class:`Text` bundles a string, a font, a position, and a color.  It owns
its font only when it created it internally; a :class:`Font` passed in is
shared and never destroyed by the text, so many labels can safely use one
developer-created font.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from .color import normalize_rgba
from .font import Font


def _coord(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer, got {value!r}.")
    return value


class Text:
    """A positioned, colored string rendered with a font.

    Parameters
    ----------
    text:
        The string to render.
    font:
        A :class:`~pydex_ge.graphics.font.Font`, a font file path, or ``None``
        to use a system font.  A :class:`Font` instance is shared (never
        destroyed by this text); a path/``None`` creates an owned font.
    font_size:
        Point size used when a font is created internally (ignored when
        ``font`` is a :class:`Font` instance).
    position:
        Top-left ``(x, y)`` in pixels.
    color:
        An RGB or RGBA tuple, each channel 0-255.
    visible:
        Whether the text is drawn.
    """

    def __init__(
        self,
        text: str = "",
        font: Font | str | None = None,
        *,
        font_size: int = 24,
        position: tuple[int, int] = (0, 0),
        color: object = (255, 255, 255),
        visible: bool = True,
        backend=None,
    ) -> None:
        if not isinstance(text, str):
            raise ConfigurationError("Text must be a string.")
        self._text = text
        self._font, self._owns_font = self._resolve_font(font, font_size, backend)
        self._position = (0, 0)
        self.position = position
        self._color = normalize_rgba(color)
        self.visible = visible

    @staticmethod
    def _resolve_font(
        font: Font | str | None, font_size: int, backend=None
    ) -> tuple[Font, bool]:
        if isinstance(font, Font):
            return font, False
        if isinstance(font, str):
            return Font(font, font_size, backend=backend), True
        return Font(None, font_size, backend=backend), True

    @property
    def text(self) -> str:
        """The string being rendered."""
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        if not isinstance(value, str):
            raise ConfigurationError("Text must be a string.")
        self._text = value

    @property
    def position(self) -> tuple[int, int]:
        """The top-left corner as ``(x, y)``."""
        return self._position

    @position.setter
    def position(self, value: object) -> None:
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise ConfigurationError(f"position must be an (x, y) pair, got {value!r}.")
        x, y = value
        self.x = _coord(x, "x")
        self.y = _coord(y, "y")

    @property
    def x(self) -> int:
        """The X coordinate of the top-left corner."""
        return self._position[0]

    @x.setter
    def x(self, value: object) -> None:
        self._position = (_coord(value, "x"), self._position[1])

    @property
    def y(self) -> int:
        """The Y coordinate of the top-left corner."""
        return self._position[1]

    @y.setter
    def y(self, value: object) -> None:
        self._position = (self._position[0], _coord(value, "y"))

    @property
    def color(self) -> tuple[int, int, int, int]:
        """The text color as an RGBA tuple."""
        return self._color

    @color.setter
    def color(self, value: object) -> None:
        self._color = normalize_rgba(value)

    @property
    def font(self) -> Font:
        """The font used to render this text."""
        return self._check()

    def _check(self) -> Font:
        if self._font is None:
            raise RuntimeError("This Text has been destroyed.")
        return self._font

    @property
    def font_size(self) -> int:
        """The font size in points."""
        return self._check().size

    @font_size.setter
    def font_size(self, value: object) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ConfigurationError("font_size must be a positive integer.")
        if self._font is None:
            raise RuntimeError("This Text has been destroyed.")
        if not self._owns_font:
            raise ConfigurationError(
                "Cannot change the size of a shared font. Create a new Font "
                "and pass it to the text instead."
            )
        new_font = Font(self._font.path, value, backend=self._font._backend)
        self._font.destroy()
        self._font = new_font
        self._owns_font = True

    @property
    def width(self) -> int:
        """The rendered width in pixels at the current text and font."""
        return self._check().measure(self._text)[0]

    @property
    def height(self) -> int:
        """The rendered height in pixels at the current text and font."""
        return self._check().measure(self._text)[1]

    def draw(self, renderer) -> None:
        """Draw this text through a window renderer."""
        if not self.visible or self._font is None:
            return
        renderer.draw_text(self)

    def destroy(self) -> None:
        """Free the owned font, if any.  A shared font is left untouched."""
        if self._owns_font:
            self._font.destroy()
            self._owns_font = False
        self._font = None


__all__ = ["Text"]
