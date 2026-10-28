"""The :class:`Sprite`: a positioned, scaled, transparent renderable.

A PYDEX sprite is not limited to an image file.  A sprite's pixels can come
from:

* an image asset (``pydex_ge.Sprite("player.png")`` or ``pydex_ge.Sprite(image)``),
* raw RGBA pixel data created directly by PYDEX
  (``pydex_ge.Sprite.from_pixels(...)``),
* a region of a larger texture or sprite sheet.

Sprites are drawn with ``game.renderer.draw_sprite(sprite)`` (or
``sprite.draw(renderer)``) and render hidden until their window is open.

Part 12 adds transform support on top: ``rotation``, a normalized
``origin`` (``(0, 0)`` top-left by default, ``(0.5, 0.5)`` center),
``flip_x``/``flip_y``, per-axis ``scale``, an optional ``parent`` (a
:class:`~pydex_ge.transform.Transform2D` or another ``Sprite``) with
``local_position``/``world_position``, a ``z`` draw order, named
animations with completion callbacks, and the ``fade_to``/``flash``/``tint``
effects.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from .color import normalize_rgb
from .image import Image

_EPSILON = 1e-9


def _coord(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be an integer, got {value!r}.")
    number = float(value)
    if not number.is_integer():
        raise ConfigurationError(f"{name} must be an integer, got {value!r}.")
    return int(number)


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"{name} must be a positive integer, got {value!r}.")
    return value


def _non_negative(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"{name} must be a non-negative integer, got {value!r}.")
    return value


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    return float(value)


def _positive_number(value: object, name: str) -> float:
    number = _number(value, name)
    if number <= 0:
        raise ConfigurationError(f"{name} must be greater than zero, got {value!r}.")
    return number


def _scale(value: object, name: str = "scale") -> float:
    number = _number(value, name)
    if number <= 0:
        raise ConfigurationError(f"{name} must be a number greater than zero, got {value!r}.")
    return number


def _as_scale(value: object) -> tuple[float, float]:
    if isinstance(value, (tuple, list)):
        if len(value) != 2:
            raise ConfigurationError(
                f"scale must be a number or a 2-element (x, y) pair, got {value!r}."
            )
        return _scale(value[0], "scale"), _scale(value[1], "scale")
    if hasattr(value, "x") and hasattr(value, "y") and not isinstance(value, (str, bytes)):
        return _scale(value.x, "scale"), _scale(value.y, "scale")
    return _scale(value, "scale"), _scale(value, "scale")


def _as_vector(value: object, name: str):
    from ..physics.vector import Vector2

    if isinstance(value, Vector2):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return Vector2(value[0], value[1])
    raise ConfigurationError(
        f"{name} must be a Vector2 or a 2-element (x, y) sequence, got {value!r}."
    )


def _alpha(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255:
        raise ConfigurationError(f"alpha must be an int in 0-255, got {value!r}.")
    return value


def _bool_flag(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{name} must be a bool, got {value!r}.")
    return value


def _format_scale(sx: float, sy: float) -> float | tuple[float, float]:
    if abs(sx - sy) < _EPSILON:
        return sx
    return (sx, sy)


class Sprite:
    """A renderable image with position, transform, scale, and alpha.

    Parameters
    ----------
    source:
        An :class:`~pydex_ge.graphics.image.Image` or a path to an image file.
        Pixels can instead be supplied with :meth:`from_pixels`.
    region:
        Optional source ``(x, y, width, height)`` rectangle within the image.
        When omitted the whole image is used.
    backend:
        Backend used when ``source`` is a file path.  Defaults to SDL2.
    """

    def __init__(
        self,
        source: Image | str | None = None,
        *,
        region: tuple[int, int, int, int] | None = None,
        backend=None,
        _pixels: tuple[int, int, bytes] | None = None,
    ) -> None:
        self._image: Image | None = None
        self._pixel_source: tuple[int, int, bytes] | None = None
        self._region: tuple[int, int, int, int] | None = None

        if _pixels is not None:
            width, height, pixels = _pixels
            width = _positive(width, "width")
            height = _positive(height, "height")
            if not isinstance(pixels, (bytes, bytearray, memoryview)):
                raise ConfigurationError("pixels must be an RGBA bytes-like buffer.")
            if len(pixels) != width * height * 4:
                raise ConfigurationError(
                    f"pixel buffer length {len(pixels)} does not match "
                    f"{width}x{height}x4 RGBA data."
                )
            self._pixel_source = (width, height, bytes(pixels))
        elif isinstance(source, str):
            if not source.strip():
                raise ConfigurationError("Sprite image path must be a non-empty string.")
            self._image = Image(source, backend=backend)
        elif isinstance(source, Image):
            self._image = source
        else:
            raise ConfigurationError(
                "Sprite requires an Image, a path to an image file, or pixel data."
            )

        if region is not None:
            x, y, width, height = region
            x = _non_negative(x, "region.x")
            y = _non_negative(y, "region.y")
            width = _positive(width, "region.width")
            height = _positive(height, "region.height")
            if self._image is None:
                raise ConfigurationError("A region needs an image source.")
            if x + width > self._image.width or y + height > self._image.height:
                raise ConfigurationError(
                    f"Region {region} exceeds the image size "
                    f"{self._image.width}x{self._image.height}."
                )
            self._region = (x, y, width, height)

        self.x = 0
        self.y = 0
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._alpha = 255
        self.visible = True
        self._rotation = 0.0
        self._origin = (0.0, 0.0)
        self._flip_x = False
        self._flip_y = False
        self._parent = None
        self._z = 0
        self._animation = None
        self._animation_map = None
        self._animation_name = None
        self._animation_finish_callback = None
        self._fade = None
        self._flash = None
        self._tint = (255, 255, 255)
        self._effective_tint = (255, 255, 255)

    @classmethod
    def from_pixels(
        cls,
        width: int,
        height: int,
        pixels,
        *,
        backend=None,
    ) -> Sprite:
        """Create a sprite from raw RGBA pixel data (``width * height * 4`` bytes).

        Pixel sprites need no image file and work in every backend, which
        makes them ideal for pixel-art games.
        """
        return cls(None, _pixels=(width, height, pixels))

    @property
    def position(self) -> tuple[int, int]:
        """The sprite's local top-left corner as ``(x, y)``."""
        return (self.x, self.y)

    @position.setter
    def position(self, value: tuple[int, int]) -> None:
        x, y = value
        self.x = _coord(x, "x")
        self.y = _coord(y, "y")

    @property
    def x(self) -> int | float:
        """The sprite's horizontal local top-left position."""
        return self._x

    @x.setter
    def x(self, value: object) -> None:
        number = _number(value, "x")
        self._x = int(number) if number.is_integer() else number

    @property
    def y(self) -> int | float:
        """The sprite's vertical local top-left position."""
        return self._y

    @y.setter
    def y(self, value: object) -> None:
        number = _number(value, "y")
        self._y = int(number) if number.is_integer() else number

    @property
    def width(self) -> int:
        """The source width in pixels (unscaled)."""
        if self._pixel_source is not None:
            return self._pixel_source[0]
        if self._region is not None:
            return self._region[2]
        return self._image.width

    @property
    def height(self) -> int:
        """The source height in pixels (unscaled)."""
        if self._pixel_source is not None:
            return self._pixel_source[1]
        if self._region is not None:
            return self._region[3]
        return self._image.height

    @property
    def scale(self) -> float | tuple[float, float]:
        """The scale: a float when uniform, else an ``(x, y)`` pair.

        ``sprite.scale = 2`` and ``sprite.scale = (2, 1)`` both work; when
        the scale is uniform the getter returns a plain float so existing
        code that expects ``sprite.scale == 0.5`` keeps working.
        """
        return _format_scale(self._scale_x, self._scale_y)

    @scale.setter
    def scale(self, value: object) -> None:
        self._scale_x, self._scale_y = _as_scale(value)

    @property
    def scale_x(self) -> float:
        """The horizontal scale factor."""
        return self._scale_x

    @scale_x.setter
    def scale_x(self, value: object) -> None:
        self._scale_x = _scale(value, "scale_x")

    @property
    def scale_y(self) -> float:
        """The vertical scale factor."""
        return self._scale_y

    @scale_y.setter
    def scale_y(self, value: object) -> None:
        self._scale_y = _scale(value, "scale_y")

    @property
    def alpha(self) -> int:
        """Per-sprite opacity, 0 (invisible) to 255 (opaque)."""
        return self._alpha

    @alpha.setter
    def alpha(self, value: object) -> None:
        self._alpha = _alpha(value)

    # -- transform ---------------------------------------------------------

    @property
    def rotation(self) -> float:
        """Clockwise rotation in degrees (0 = no rotation)."""
        return self._rotation

    @rotation.setter
    def rotation(self, value: object) -> None:
        self._rotation = _number(value, "rotation")

    @property
    def origin(self) -> tuple[float, float]:
        """The normalized origin ``(origin_x, origin_y)``.

        ``(0, 0)`` (the default) is the top-left corner and keeps existing
        sprites rendering identically; ``(0.5, 0.5)`` is the center.
        """
        return self._origin

    @origin.setter
    def origin(self, value: object) -> None:
        vector = _as_vector(value, "origin")
        self._origin = (vector.x, vector.y)

    @property
    def flip_x(self) -> bool:
        """True flips the sprite horizontally when drawn."""
        return self._flip_x

    @flip_x.setter
    def flip_x(self, value: object) -> None:
        self._flip_x = _bool_flag(value, "flip_x")

    @property
    def flip_y(self) -> bool:
        """True flips the sprite vertically when drawn."""
        return self._flip_y

    @flip_y.setter
    def flip_y(self, value: object) -> None:
        self._flip_y = _bool_flag(value, "flip_y")

    @property
    def parent(self):
        """The parent this sprite inherits transforms from (or None).

        A parent can be a :class:`~pydex_ge.transform.Transform2D` or another
        :class:`Sprite`.  The sprite's own ``x``/``y`` stay *local*; drawing
        uses the computed world position.
        """
        return self._parent

    @parent.setter
    def parent(self, value: object) -> None:
        if value is None:
            self._parent = None
            return
        from ..transform import Transform2D

        if isinstance(value, (Transform2D, Sprite)):
            node = value
            while isinstance(node, Sprite):
                if node is self:
                    raise ConfigurationError(
                        "parent would create a sprite cycle."
                    )
                node = node._parent
            self._parent = value
            return
        raise ConfigurationError(
            "sprite.parent must be a Transform2D, a Sprite, or None."
        )

    @property
    def local_position(self) -> tuple[int, int]:
        """The sprite's own top-left corner ``(x, y)`` (ignores the parent)."""
        return (self.x, self.y)

    @property
    def local_rotation(self) -> float:
        """The sprite's own rotation in degrees (ignores the parent)."""
        return self._rotation

    @property
    def local_scale(self) -> float | tuple[float, float]:
        """The sprite's own scale (ignores the parent)."""
        return self.scale

    @property
    def world_position(self):
        """The position in world space (parent position composed with local).

        A child's local offset is scaled and rotated with its parent, so a
        sprite attached at ``(10, 0)`` under a rotated and scaled parent
        orbits around the parent exactly like the rendered child does.
        """
        from ..physics.vector import Vector2

        if self._parent is None:
            return Vector2(self.x, self.y)
        parent_world = _as_vector(self._parent.world_position, "parent.world_position")
        offset = Vector2(self.x, self.y)
        if isinstance(self._parent, Sprite):
            parent_scale = self._parent.world_scale
        elif hasattr(self._parent, "world_scale"):
            parent_scale = self._parent.world_scale
        elif hasattr(self._parent, "scale"):
            parent_scale = self._parent.scale
        else:
            parent_scale = (1.0, 1.0)
        if isinstance(parent_scale, (tuple, list)):
            offset = Vector2(offset.x * parent_scale[0], offset.y * parent_scale[1])
        else:
            offset = Vector2(offset.x * parent_scale, offset.y * parent_scale)
        if isinstance(self._parent, Sprite):
            parent_rotation = self._parent.world_rotation
        elif hasattr(self._parent, "world_rotation"):
            parent_rotation = self._parent.world_rotation
        elif hasattr(self._parent, "rotation"):
            parent_rotation = _number(self._parent.rotation, "parent.rotation")
        else:
            parent_rotation = 0.0
        offset = offset.rotate(parent_rotation)
        return Vector2(parent_world.x + offset.x, parent_world.y + offset.y)

    @property
    def world_rotation(self) -> float:
        """The rotation in world space (parent rotation + local rotation)."""
        if self._parent is None:
            return self._rotation
        if isinstance(self._parent, Sprite):
            return self._parent.world_rotation + self._rotation
        if hasattr(self._parent, "world_rotation"):
            return self._parent.world_rotation + self._rotation
        if hasattr(self._parent, "rotation"):
            return _number(self._parent.rotation, "parent.rotation") + self._rotation
        return self._rotation

    @property
    def world_scale(self) -> float | tuple[float, float]:
        """The scale in world space (parent scale times local scale, per axis)."""
        sx, sy = self._scale_x, self._scale_y
        if self._parent is not None:
            if isinstance(self._parent, Sprite):
                parent = self._parent.world_scale
            elif hasattr(self._parent, "world_scale"):
                parent = self._parent.world_scale
            elif hasattr(self._parent, "scale"):
                parent = self._parent.scale
            else:
                parent = (1.0, 1.0)
            if isinstance(parent, (tuple, list)):
                px, py = parent[0], parent[1]
            else:
                px = py = parent
            sx *= px
            sy *= py
        return _format_scale(sx, sy)

    @property
    def z(self) -> int | float:
        """The draw order used by :class:`~pydex_ge.scene.Scene`.

        Lower ``z`` draws first; higher ``z`` draws later.  Objects with the
        same ``z`` keep their insertion order (stable sort).
        """
        return self._z

    @z.setter
    def z(self, value: object) -> None:
        number = _number(value, "z")
        self._z = int(number) if number.is_integer() else number

    # -- alpha effects -----------------------------------------------------

    @property
    def tint(self) -> tuple[int, int, int]:
        """An RGB color multiply applied when drawing (255 = no change)."""
        return self._tint

    @tint.setter
    def tint(self, value: object) -> None:
        self._tint = normalize_rgb(value, "tint")
        self._refresh_tint()

    @property
    def flash_strength(self) -> float:
        """The current flash intensity, ``1.0`` decaying to ``0.0``."""
        if self._flash is None:
            return 0.0
        return self._flash.strength

    @property
    def flashing(self) -> bool:
        """True while a :meth:`flash` is active."""
        return self._flash is not None

    def fade_to(self, target: object, duration: object) -> None:
        """Fade ``alpha`` to ``target`` (0-255) over ``duration`` seconds."""
        from .effects import Fade

        target_alpha = _alpha(target)
        duration = _positive_number(duration, "duration")
        self._fade = Fade(self._alpha, target_alpha, duration)

    def flash(self, duration: object, color: object = (255, 255, 255)) -> None:
        """Flash the sprite white (or ``color``) for ``duration`` seconds.

        The flash starts at full strength and fades out; ``sprite.update(dt)``
        advances it.  A new flash replaces any active one.
        """
        from .effects import Flash

        duration = _positive_number(duration, "duration")
        self._flash = Flash(duration, color)
        self._refresh_tint()

    def _refresh_tint(self) -> None:
        base = self._tint
        if self._flash is None:
            self._effective_tint = base
            return
        strength = self._flash.strength
        flash_color = self._flash.color
        self._effective_tint = tuple(
            int(round(base[index] + (flash_color[index] - base[index]) * strength))
            for index in range(3)
        )

    @property
    def _draw_tint(self) -> tuple[int, int, int]:
        return self._effective_tint

    # -- animation ---------------------------------------------------------

    @property
    def animation(self) -> object | None:
        """The :class:`~pydex_ge.graphics.animation.Animation` this sprite plays.

        ``None`` means the sprite draws its own static image.  Assigning
        ``sprite.animation = None`` restores static behavior.
        """
        return self._animation

    @animation.setter
    def animation(self, value: object) -> None:
        from .animation import Animation

        if value is None:
            self._animation = None
            self._animation_name = None
            self._animation_finish_callback = None
            return
        if not isinstance(value, Animation):
            raise ConfigurationError("sprite.animation must be an Animation or None.")
        self._animation = value
        self._animation_name = None
        self._animation_finish_callback = None

    @property
    def animations(self) -> dict:
        """A dict of named :class:`~pydex_ge.graphics.animation.Animation` objects.

        Use with :meth:`play_animation` to switch animations by name, or add
        new ones with :meth:`add_animation`.
        """
        if self._animation_map is None:
            self._animation_map = {}
        return self._animation_map

    @property
    def animation_names(self) -> list[str]:
        """The names of every animation registered with :meth:`add_animation`."""
        return list(self.animations.keys())

    @property
    def current_animation(self) -> str | None:
        """The name of the currently playing animation, or None."""
        return self._animation_name

    def add_animation(self, name: str, animation: object) -> None:
        """Register ``animation`` under ``name`` for :meth:`play_animation`."""
        if not isinstance(name, str) or not name.strip():
            raise ConfigurationError("add_animation() needs a non-empty animation name.")
        from .animation import Animation

        if not isinstance(animation, Animation):
            raise ConfigurationError("add_animation() needs an Animation.")
        self.animations[name] = animation

    def play_animation(self, name: str, on_finish: object = None) -> None:
        """Switch to a named animation from :attr:`animations` and play it.

        The new animation restarts from frame 0.  Switching to the same
        animation is a no-op (unless it already finished).  Unknown names
        raise :class:`~pydex_ge.exceptions.ConfigurationError`.  ``on_finish``,
        when given, is called once when a non-looping animation reaches its
        final frame; it may switch to another animation.
        """
        if on_finish is not None and not callable(on_finish):
            raise ConfigurationError("on_finish must be callable or None.")
        if not isinstance(name, str) or not name.strip():
            raise ConfigurationError("play_animation() needs a non-empty animation name.")
        animations = self.animations
        if name not in animations:
            raise ConfigurationError(
                f"Unknown animation {name!r}. Add it to sprite.animations first."
            )
        animation = animations[name]
        if (
            self._animation is animation
            and self._animation_name == name
            and not animation.finished
        ):
            self._animation_finish_callback = on_finish
            return
        self._animation = animation
        self._animation_name = name
        self._animation_finish_callback = on_finish
        animation.restart()

    def stop_animation(self) -> None:
        """Remove the active animation; the sprite returns to static drawing."""
        self._animation = None
        self._animation_name = None
        self._animation_finish_callback = None

    def play(self) -> None:
        """Start the attached animation (no-op without one)."""
        if self._animation is not None:
            self._animation.play()

    def pause(self) -> None:
        """Pause the attached animation (no-op without one)."""
        if self._animation is not None:
            self._animation.pause()

    def stop(self) -> None:
        """Stop the attached animation and rewind it (no-op without one)."""
        if self._animation is not None:
            self._animation.stop()

    def update(self, dt: object) -> None:
        """Advance the attached animation and any active effects by ``dt``.

        A non-looping animation's ``on_finish`` callback (set through
        :meth:`play_animation`) runs once when the animation finishes.
        """
        if self._animation is not None:
            was_finished = self._animation.finished
            self._animation.update(dt)
            if (
                not was_finished
                and self._animation.finished
                and self._animation_finish_callback is not None
            ):
                callback = self._animation_finish_callback
                self._animation_finish_callback = None
                callback()
        if self._fade is not None:
            self._alpha = self._fade.update(dt)
            if self._fade.finished:
                self._fade = None
        if self._flash is not None:
            self._flash.update(dt)
            if self._flash.finished:
                self._flash = None
        self._refresh_tint()

    def draw(self, renderer) -> None:
        """Draw this sprite (or its current animation frame) through a renderer."""
        if not self.visible:
            return
        if self._animation is not None:
            world = self.world_position
            self._animation.draw(
                renderer,
                (world.x, world.y),
                scale=self.world_scale,
                alpha=self.alpha,
                rotation=self.world_rotation,
                origin=self.origin,
                flip_x=self.flip_x,
                flip_y=self.flip_y,
                tint_override=self._draw_tint,
            )
            return
        renderer.draw_sprite(self)


__all__ = ["Sprite"]
