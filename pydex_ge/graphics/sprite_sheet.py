"""Sprite sheets: select rectangular regions of one larger image.

A :class:`SpriteSheet` wraps a single image and returns :class:`Sprite`
objects (or :class:`TextureRegion` objects) for rectangular parts of it.
Animation can later step through these regions.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from .animation import Animation
from .image import Image
from .sprite import Sprite
from .texture import TextureRegion, _positive


class SpriteSheet:
    """A collection of sprite regions cut from one image.

    Parameters
    ----------
    image:
        The sheet image.
    cell_width, cell_height:
        Optional uniform cell size for ``cell()`` access.  Region access via
        :meth:`region` / :meth:`sprite` does not require them.
    """

    def __init__(
        self,
        image: Image,
        cell_width: int | None = None,
        cell_height: int | None = None,
    ) -> None:
        if not isinstance(image, Image):
            raise ConfigurationError("SpriteSheet requires a pydex_ge.Image.")
        self.image = image
        self.cell_width = _positive(cell_width, "cell_width") if cell_width is not None else None
        self.cell_height = _positive(cell_height, "cell_height") if cell_height is not None else None

    @property
    def columns(self) -> int | None:
        """Number of cells across the sheet, if cell sizes are set."""
        if self.cell_width is None:
            return None
        return self.image.width // self.cell_width

    @property
    def rows(self) -> int | None:
        """Number of cells down the sheet, if cell sizes are set."""
        if self.cell_height is None:
            return None
        return self.image.height // self.cell_height

    def region(self, x: int, y: int, width: int, height: int) -> TextureRegion:
        """Return a :class:`TextureRegion` for the given part of the sheet."""
        return TextureRegion(self.image, x, y, width, height)

    def sprite(self, x: int, y: int, width: int, height: int) -> Sprite:
        """Return a :class:`Sprite` drawing only that part of the sheet."""
        return Sprite(self.image, region=(x, y, width, height))

    def cell(self, column: int, row: int) -> Sprite:
        """Return the sprite at a cell grid position, using the cell sizes."""
        if self.cell_width is None or self.cell_height is None:
            raise ConfigurationError(
                "cell() needs cell_width and cell_height to be set."
            )
        if column < 0 or row < 0:
            raise ConfigurationError("cell column and row must be non-negative.")
        x = column * self.cell_width
        y = row * self.cell_height
        if x + self.cell_width > self.image.width or y + self.cell_height > self.image.height:
            raise ConfigurationError("cell index is outside the sheet.")
        return self.sprite(x, y, self.cell_width, self.cell_height)

    def animation(
        self,
        frames,
        *,
        fps: object | None = None,
        loop: bool = True,
        speed: object = 1.0,
    ) -> Animation:
        """Build an :class:`~pydex_ge.graphics.animation.Animation` from cells.

        Each ``frames`` item is a ``(column, row)`` cell coordinate, or a
        ``(column, row, duration_seconds)`` tuple for a custom frame
        duration.  Requires ``cell_width``/``cell_height`` to be set.
        """
        built = []
        for item in frames:
            if isinstance(item, (tuple, list)) and len(item) in (2, 3):
                column, row = item[0], item[1]
                sprite = self.cell(column, row)
                if len(item) == 3:
                    built.append((sprite, item[2]))
                else:
                    built.append(sprite)
            else:
                raise ConfigurationError(
                    "sheet.animation() frames must be (column, row) or "
                    "(column, row, duration) tuples."
                )
        return Animation(built, fps=fps, loop=loop, speed=speed)

    def animation_run(
        self,
        column: int,
        row: int,
        count: int,
        *,
        fps: object | None = None,
        loop: bool = True,
        speed: object = 1.0,
    ) -> Animation:
        """Build a sequential animation of ``count`` cells in a row.

        Starts at ``(column, row)`` and steps rightwards one cell at a
        time, e.g. ``animation_run(0, 0, 4)`` uses cells ``(0,0)``,
        ``(1,0)``, ``(2,0)``, and ``(3,0)``.  Cells must stay inside the
        sheet.
        """
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ConfigurationError("count must be a positive integer.")
        return self.animation(
            [(column + index, row) for index in range(count)],
            fps=fps,
            loop=loop,
            speed=speed,
        )


__all__ = ["SpriteSheet"]