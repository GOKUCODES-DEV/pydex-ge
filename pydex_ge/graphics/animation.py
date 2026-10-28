"""Framed 2D animation for PYDEX.

An :class:`Animation` is a list of frames played over time.  Frames are
reused from the existing texture/region system: each frame is either a
:class:`~pydex_ge.graphics.sprite.Sprite` or a
:class:`~pydex_ge.graphics.texture.TextureRegion` (a :class:`SpriteSheet` cell
is a sprite, so ``sheet.cell(...)`` frames work directly).  The animation
only decides *which* frame is shown; the renderer stays responsible for
*how* it is drawn.

Timing is based on elapsed seconds (``update(dt)``), never on a fixed
60 FPS assumption, so changing the game's frame rate does not change
animation speed.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from .sprite import Sprite
from .texture import TextureRegion


def _positive_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    number = float(value)
    if number <= 0:
        raise ConfigurationError(f"{name} must be greater than zero, got {value!r}.")
    return number


def _dt(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"dt must be a number, got {value!r}.")
    number = float(value)
    if number < 0:
        raise ConfigurationError("dt must be non-negative.")
    return number


def _as_frame_sprite(source: object) -> Sprite:
    """Normalize one frame source to a :class:`Sprite` for drawing."""
    if isinstance(source, TextureRegion):
        return source.sprite()
    if isinstance(source, Sprite):
        return source
    if isinstance(source, str):
        raise ConfigurationError(
            "Animation frames must be Sprites or TextureRegions, not filenames."
        )
    raise ConfigurationError(
        f"Animation frames must be Sprites or TextureRegions, got {source!r}."
    )


class AnimationFrame:
    """One frame of an animation: a drawable sprite and a duration.

    Frames are built internally by :class:`Animation`; you normally pass
    frame sources (Sprites/TextureRegions) to the animation constructor.
    """

    __slots__ = ("sprite", "duration")

    def __init__(self, sprite: Sprite, duration: float) -> None:
        self.sprite = sprite
        self.duration = duration


class Animation:
    """A list of frames played over time.

    Parameters
    ----------
    frames:
        A list of frame sources.  Each item is either a
        :class:`~pydex_ge.graphics.sprite.Sprite` or a
        :class:`~pydex_ge.graphics.texture.TextureRegion`, or a
        ``(source, duration_seconds)`` tuple for an explicit per-frame
        duration.  Empty frame lists raise :class:`ConfigurationError`.
    fps:
        Frames per second.  When given, every frame lasts ``1 / fps``
        seconds.  Per-frame tuple durations override this base value.
        ``fps`` must be positive.  When ``None``, every frame needs an
        explicit tuple duration.
    loop:
        Whether the animation restarts from frame 0 after the final frame.
        Non-looping animations stop on the final frame with
        :attr:`finished` set to ``True``.
    speed:
        Playback speed multiplier (``2.0`` = twice as fast, ``0.5`` = half
        speed).  Must be greater than zero.

    Example
    -------
    ::

        animation = pydex_ge.Animation(
            frames=[sheet.cell(0, 0), sheet.cell(1, 0), sheet.cell(2, 0)],
            fps=12,
            loop=True,
        )
        animation.play()

    Timing uses elapsed seconds, so ``animation.update(dt)`` works with the
    game loop's real delta time no matter what FPS the game is running at.
    """

    def __init__(
        self,
        frames,
        fps: object | None = None,
        *,
        loop: bool = True,
        speed: object = 1.0,
    ) -> None:
        if isinstance(loop, bool) is False:
            raise ConfigurationError("loop must be a bool.")
        self._loop = loop
        self._speed = _positive_number(speed, "speed")

        base_duration = None
        if fps is not None:
            base_duration = 1.0 / _positive_number(fps, "fps")

        if isinstance(frames, (str, bytes)) or not hasattr(frames, "__iter__"):
            raise ConfigurationError(
                "frames must be an iterable of frame sources or "
                "(source, duration) tuples."
            )
        frame_list = list(frames)
        if not frame_list:
            raise ConfigurationError("Animation needs at least one frame.")

        built: list[AnimationFrame] = []
        for item in frame_list:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                source, duration = item
                duration = _positive_number(duration, "frame duration")
            else:
                source = item
                duration = base_duration
            if duration is None:
                raise ConfigurationError(
                    "Each frame needs a duration: provide fps or "
                    "(frame, duration) tuples."
                )
            built.append(AnimationFrame(_as_frame_sprite(source), duration))

        self._frames = built
        self._index = 0
        self._time = 0.0
        self._playing = False
        self._finished = False

    # -- state ------------------------------------------------------------

    @property
    def current_frame(self) -> Sprite:
        """The current frame as a drawable :class:`Sprite`."""
        return self._frames[self._index].sprite

    @property
    def frame_index(self) -> int:
        """The index of the current frame (``0`` to ``frame_count - 1``)."""
        return self._index

    @property
    def current_index(self) -> int:
        """Alias for :attr:`frame_index`."""
        return self._index

    @property
    def playing(self) -> bool:
        """True while the animation is advancing over time."""
        return self._playing

    @property
    def loop(self) -> bool:
        """Whether the animation repeats from frame 0 after the last frame."""
        return self._loop

    @loop.setter
    def loop(self, value: object) -> None:
        if isinstance(value, bool) is False:
            raise ConfigurationError("loop must be a bool.")
        self._loop = value

    @property
    def finished(self) -> bool:
        """True when a non-looping animation has reached its final frame."""
        return self._finished

    @property
    def time(self) -> float:
        """Seconds elapsed into the current frame."""
        return self._time

    @property
    def frame_count(self) -> int:
        """The number of frames in this animation."""
        return len(self._frames)

    @property
    def speed(self) -> float:
        """Playback speed multiplier (``1.0`` = normal speed)."""
        return self._speed

    @speed.setter
    def speed(self, value: object) -> None:
        self._speed = _positive_number(value, "speed")

    def __len__(self) -> int:
        return self.frame_count

    def __repr__(self) -> str:
        return (
            f"Animation(frames={self.frame_count}, "
            f"frame_index={self._index}, playing={self._playing}, "
            f"loop={self._loop}, finished={self._finished})"
        )

    # -- controls ---------------------------------------------------------

    def play(self) -> None:
        """Start (or restart, after finishing) playing from the current frame."""
        if self._finished:
            self._index = 0
            self._time = 0.0
            self._finished = False
        self._playing = True

    def pause(self) -> None:
        """Freeze playback on the current frame."""
        self._playing = False

    def resume(self) -> None:
        """Continue playback from the current frame (restarting if finished)."""
        if self._finished:
            self._index = 0
            self._time = 0.0
            self._finished = False
        self._playing = True

    def stop(self) -> None:
        """Stop playback and return to the first frame."""
        self._playing = False
        self._index = 0
        self._time = 0.0
        self._finished = False

    def reset(self) -> None:
        """Return to the first frame without changing the playing state."""
        self._index = 0
        self._time = 0.0
        self._finished = False

    def restart(self) -> None:
        """Return to the first frame and start playing."""
        self._index = 0
        self._time = 0.0
        self._finished = False
        self._playing = True

    # -- timing -----------------------------------------------------------

    def update(self, dt: object) -> None:
        """Advance the animation by ``dt`` seconds (scaled by :attr:`speed`).

        Large ``dt`` values advance multiple frames correctly (no
        frame-skipping).  Negative ``dt`` raises
        :class:`ConfigurationError`.
        """
        dt = _dt(dt)
        if not self._playing or self._finished:
            return
        self._time += dt * self._speed
        while self._playing and self._time >= self._frames[self._index].duration:
            self._time -= self._frames[self._index].duration
            self._index += 1
            if self._index >= self.frame_count:
                if self._loop:
                    self._index = 0
                else:
                    self._index = self.frame_count - 1
                    self._time = 0.0
                    self._finished = True
                    self._playing = False

    # -- drawing ----------------------------------------------------------

    def draw(
        self,
        renderer,
        position,
        *,
        scale: object = 1.0,
        alpha: object = 255,
        rotation: object = 0.0,
        origin: object = (0, 0),
        flip_x: object = False,
        flip_y: object = False,
        tint_override: object = None,
    ) -> None:
        """Draw the current frame through ``renderer`` at ``position``.

        ``position`` is the top-left ``(x, y)`` (a :class:`~pydex_ge.physics.Vector2`
        or a 2-element sequence).  ``scale`` and ``alpha`` reuse the sprite
        drawing conventions (scale > 0, alpha 0-255).  ``rotation``,
        ``origin``, and the flip flags are forwarded to the frame sprite so
        animated sprites support the same transforms as static ones.
        ``tint_override``, when given, is an RGB color multiply forwarded to
        the renderer on top of the frame sprite's own tint.
        """
        if isinstance(position, (tuple, list)):
            if len(position) != 2:
                raise ConfigurationError("position must be an (x, y) pair.")
            x, y = position[0], position[1]
        elif hasattr(position, "x") and hasattr(position, "y"):
            x, y = position.x, position.y
        else:
            raise ConfigurationError(
                f"position must be an (x, y) pair or a Vector2, got {position!r}."
            )
        sprite = self.current_frame
        saved = (
            sprite.x,
            sprite.y,
            sprite.scale,
            sprite.alpha,
            sprite.rotation,
            sprite.origin,
            sprite.flip_x,
            sprite.flip_y,
        )
        try:
            sprite.x = x
            sprite.y = y
            sprite.scale = scale
            sprite.alpha = alpha
            sprite.rotation = rotation
            sprite.origin = origin
            sprite.flip_x = flip_x
            sprite.flip_y = flip_y
            renderer.draw_sprite(sprite, tint_override=tint_override)
        finally:
            (
                sprite.x,
                sprite.y,
                sprite.scale,
                sprite.alpha,
                sprite.rotation,
                sprite.origin,
                sprite.flip_x,
                sprite.flip_y,
            ) = saved


__all__ = ["Animation"]
