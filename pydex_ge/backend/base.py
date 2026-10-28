"""Backend contracts shared by every PYDEX backend implementation.

Backends sit at the bottom of the architecture.  Code in this package
must never import from :mod:`pydex_ge.core`, which keeps the dependency
direction one-way (``core -> backend``) and avoids cycles.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BackendEvent:
    """A normalized event produced by a backend.

    ``type`` is a short string such as ``"quit"``, and ``data`` carries
    any backend-specific payload.  The core package only ever sees these
    normalized values, never the OS library objects behind them.
    """

    type: str
    data: Mapping[str, Any] = field(default_factory=dict)


class BackendWindow(ABC):
    """Minimal, backend-agnostic handle to an on-screen window."""

    @abstractmethod
    def close(self) -> None:
        """Destroy the native window."""

    @property
    @abstractmethod
    def closed(self) -> bool:
        """True once the native window has been destroyed."""


class BackendImage(ABC):
    """Backend-agnostic handle to a decoded image (before it becomes a texture).

    The image holds its decoded pixel data only; turning it into a drawable
    texture requires a renderer (see ``BackendRenderer.create_texture_from_image``).
    """

    @property
    @abstractmethod
    def width(self) -> int:
        """The image width in pixels."""

    @property
    @abstractmethod
    def height(self) -> int:
        """The image height in pixels."""

    @abstractmethod
    def destroy(self) -> None:
        """Free the decoded image.  Safe to call more than once."""


class BackendTexture(ABC):
    """Backend-agnostic handle to a drawable texture owned by a renderer."""

    @property
    @abstractmethod
    def width(self) -> int:
        """The texture width in pixels."""

    @property
    @abstractmethod
    def height(self) -> int:
        """The texture height in pixels."""

    @abstractmethod
    def destroy(self) -> None:
        """Free the texture.  Safe to call more than once."""


class BackendFont(ABC):
    """Backend-agnostic handle to a loaded font file.

    Fonts are loaded from a file (``.ttf``/``.otf``) at a given size and
    can measure text and render a string to an image.  Rendering produces
    a :class:`BackendImage` that a renderer can turn into a texture.
    """

    @property
    @abstractmethod
    def size(self) -> int:
        """The font size in points it was opened with."""

    @abstractmethod
    def measure_text(self, text: str) -> tuple[int, int]:
        """Return the ``(width, height)`` the given text would occupy in pixels."""

    @abstractmethod
    def render_text(self, text: str, color: tuple[int, int, int, int]) -> BackendImage:
        """Render the text into a :class:`BackendImage` of the given RGBA color."""

    @abstractmethod
    def destroy(self) -> None:
        """Free the font.  Safe to call more than once."""


class BackendSound(ABC):
    """Backend-agnostic handle to a loaded sound effect (e.g. a WAV clip).

    Sound effects can overlap (multiple sounds playing at once).  Volume is
    in the ``0.0-1.0`` range.
    """

    @abstractmethod
    def play(self, loop: bool = False) -> None:
        """Start playing the sound (restarting it if it was already playing)."""

    @abstractmethod
    def stop(self) -> None:
        """Stop playback and reset the sound to the beginning."""

    @abstractmethod
    def pause(self) -> None:
        """Pause playback, keeping the current position."""

    @abstractmethod
    def resume(self) -> None:
        """Resume playback from a paused position."""

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """Set this sound's volume in the ``0.0-1.0`` range."""

    @property
    @abstractmethod
    def volume(self) -> float:
        """This sound's volume in the ``0.0-1.0`` range."""

    @property
    @abstractmethod
    def playing(self) -> bool:
        """True while the sound is currently playing (paused counts)."""

    @property
    @abstractmethod
    def paused(self) -> bool:
        """True while the sound is paused."""

    @abstractmethod
    def destroy(self) -> None:
        """Free the sound.  Safe to call more than once."""


class BackendMusic(ABC):
    """Backend-agnostic handle to a loaded music track.

    Only one music track plays at a time.  Volume is in the ``0.0-1.0``
    range.
    """

    @abstractmethod
    def play(self, loop: bool = True) -> None:
        """Start playing the track (replacing whatever music was playing)."""

    @abstractmethod
    def stop(self) -> None:
        """Stop playback and reset the track to the beginning."""

    @abstractmethod
    def pause(self) -> None:
        """Pause playback, keeping the current position."""

    @abstractmethod
    def resume(self) -> None:
        """Resume playback from a paused position."""

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """Set this track's volume in the ``0.0-1.0`` range."""

    @property
    @abstractmethod
    def volume(self) -> float:
        """This track's volume in the ``0.0-1.0`` range."""

    @property
    @abstractmethod
    def playing(self) -> bool:
        """True while the track is currently playing (paused counts)."""

    @property
    @abstractmethod
    def paused(self) -> bool:
        """True while the track is paused."""

    @abstractmethod
    def destroy(self) -> None:
        """Free the track.  Safe to call more than once."""


class BackendRenderer(ABC):
    """Minimal, backend-agnostic handle to a window renderer.

    Colors are passed as normalized RGBA tuples ``(r, g, b, a)`` with
    each channel an int in 0-255.  The core graphics layer performs all
    user-facing color validation before these methods are called.

    Source and destination rectangles are plain ``(x, y, width, height)``
    tuples.  ``draw_texture`` copies the given source rectangle of a
    texture into the destination rectangle; a ``None`` source rectangle
    means the entire texture.
    """

    @abstractmethod
    def clear(self, r: int, g: int, b: int, a: int = 255) -> None:
        """Clear the frame to a solid RGBA color."""

    @abstractmethod
    def present(self) -> None:
        """Present the prepared frame to the screen."""

    @abstractmethod
    def destroy(self) -> None:
        """Free the renderer.  Safe to call more than once."""

    @abstractmethod
    def draw_pixel(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        """Draw a single pixel at ``(x, y)``."""

    @abstractmethod
    def draw_line(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple[int, int, int, int],
    ) -> None:
        """Draw a line between two points."""

    @abstractmethod
    def draw_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int, int],
        filled: bool = True,
    ) -> None:
        """Draw a rectangle at ``(x, y)`` with the given size."""

    @abstractmethod
    def draw_circle(
        self,
        x: int,
        y: int,
        radius: int,
        color: tuple[int, int, int, int],
        filled: bool = True,
    ) -> None:
        """Draw a circle centered at ``(x, y)``."""

    @abstractmethod
    def create_texture_from_pixels(
        self, width: int, height: int, pixels: bytes
    ) -> BackendTexture:
        """Create a texture from raw RGBA pixel bytes (``width * height * 4`` bytes)."""

    @abstractmethod
    def create_texture_from_image(self, image: BackendImage) -> BackendTexture:
        """Create a texture from a previously loaded :class:`BackendImage`."""

    @abstractmethod
    def draw_texture(
        self,
        texture: BackendTexture,
        src_rect: tuple[int, int, int, int] | None,
        dst_rect: tuple[int, int, int, int],
        alpha: int,
        angle: float = 0,
        center: tuple[int, int] | None = None,
        flip: int = 0,
        color_mod: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        """Copy a rectangular region of a texture to the frame.

        ``dst_rect`` is the ``(x, y, width, height)`` box to draw into;
        scaling to fit is applied automatically.

        ``angle`` rotates the copy clockwise in degrees around ``center``
        (which is relative to the un-rotated ``dst_rect`` top-left;
        ``None`` means the rect center).  ``flip`` is a bitmask of SDL2
        flags (``1`` = horizontal, ``2`` = vertical).  ``color_mod`` is an
        RGB multiplier applied while drawing (``(255, 255, 255)`` disables
        it).  Backends without hardware rotation support may ignore
        ``angle``/``center``/``flip``, but the parameters must be accepted.
        """

    @abstractmethod
    def destroy_texture(self, texture: BackendTexture) -> None:
        """Free a texture created by this renderer.  Safe to call more than once."""


class Backend(ABC):
    """Interface every PYDEX backend must implement."""

    name: str = "base"

    @abstractmethod
    def init(self) -> None:
        """Initialize the backend (e.g. the SDL video subsystem)."""

    @abstractmethod
    def quit(self) -> None:
        """Shut the backend down, releasing any resources it holds."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the backend can run in this environment."""

    @abstractmethod
    def create_window(self, title: str, width: int, height: int) -> BackendWindow:
        """Create and show a native window, returning its handle."""

    @abstractmethod
    def create_renderer(self, window: BackendWindow) -> BackendRenderer:
        """Create a renderer for a window previously returned by :meth:`create_window`."""

    @abstractmethod
    def load_image(self, path: str) -> BackendImage:
        """Load an image file (PNG/JPG/BMP), returning its dimensions.

        The returned :class:`BackendImage` may hold decoded pixel data or
        just the image dimensions, depending on the backend.
        """

    @abstractmethod
    def load_font(self, path: str, size: int) -> BackendFont:
        """Load a font file (TTF/OTF) at the given size in points."""

    @abstractmethod
    def open_audio(self) -> None:
        """Initialize the audio subsystem so sounds/music can be loaded and played.

        Safe to call more than once; subsequent calls are no-ops until
        :meth:`close_audio` is called.
        """

    @abstractmethod
    def close_audio(self) -> None:
        """Shut the audio subsystem down, freeing any loaded audio resources.

        Safe to call more than once.
        """

    @abstractmethod
    def load_sound(self, path: str) -> BackendSound:
        """Load a sound-effect file (e.g. WAV) into a reusable clip."""

    @abstractmethod
    def load_music(self, path: str) -> BackendMusic:
        """Load a music file (e.g. WAV/OGG) into a reusable track."""

    @abstractmethod
    def set_master_volume(self, volume: float) -> None:
        """Set the master volume in the ``0.0-1.0`` range."""

    @abstractmethod
    def master_volume(self) -> float:
        """Return the master volume in the ``0.0-1.0`` range."""

    @abstractmethod
    def set_sound_volume(self, volume: float) -> None:
        """Set the global sound-effect volume in the ``0.0-1.0`` range."""

    @abstractmethod
    def sound_volume(self) -> float:
        """Return the global sound-effect volume in the ``0.0-1.0`` range."""

    @abstractmethod
    def set_music_volume(self, volume: float) -> None:
        """Set the global music volume in the ``0.0-1.0`` range."""

    @abstractmethod
    def music_volume(self) -> float:
        """Return the global music volume in the ``0.0-1.0`` range."""

    @abstractmethod
    def pause_all(self) -> None:
        """Pause every currently playing sound and music track."""

    @abstractmethod
    def resume_all(self) -> None:
        """Resume every sound and music track paused by :meth:`pause_all`."""

    @abstractmethod
    def stop_all(self) -> None:
        """Stop every currently playing sound and music track."""

    @abstractmethod
    def poll_events(self) -> list[BackendEvent]:
        """Return any pending OS events, normalized to :class:`BackendEvent`."""

    @abstractmethod
    def mouse_position(self) -> tuple[int, int]:
        """Return the current mouse position in window coordinates."""