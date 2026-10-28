"""The top-level :class:`Game` object that ties the core systems together."""

from __future__ import annotations

from ..backend import select_backend
from ..backend.base import Backend
from ..exceptions import ConfigurationError
from ..input import Input
from ..scene.manager import SceneManager
from .clock import Clock
from .events import EventManager, EventType
from .renderer import normalize_color
from .window import Window


class Game:
    """Top-level application object.

    A :class:`Game` owns its window, clock, event system, and renderer,
    and runs the main loop.  Subclass it and override :meth:`update` and
    :meth:`draw` to drive behaviour.

    Parameters
    ----------
    title, width, height:
        Passed to the underlying :class:`Window`.
    fps:
        Maximum frames per second while the loop runs.  ``None`` means
        unlimited (no frame-rate cap).
    backend:
        Backend to use.  Defaults to SDL2 (or ``PYDEX_BACKEND``).
    """

    def __init__(
        self,
        title: str = "PYDEX",
        width: int = 800,
        height: int = 600,
        *,
        fps: float | int | None = 60,
        backend: Backend | None = None,
    ) -> None:
        self.fps = fps
        self._backend = backend if backend is not None else select_backend()
        self.window = Window(title, width, height, backend=self._backend)
        self.clock = Clock()
        self.events = EventManager(backend=self._backend)
        self.input = Input(backend=self._backend)
        self.scenes = SceneManager()
        self.background = (0, 0, 0)
        self._running = False
        self.setup()

    @property
    def background(self) -> tuple[int, int, int]:
        """The color the frame is cleared to each frame, as ``(r, g, b)``."""
        return self._background

    @background.setter
    def background(self, color: object) -> None:
        r, g, b = normalize_color(color, "background")
        self._background = (r, g, b)

    @property
    def fps(self) -> float | int | None:
        """The target frame rate, or ``None`` for unlimited (no cap)."""
        return self._fps

    @fps.setter
    def fps(self, value: object) -> None:
        if value is None:
            self._fps = None
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ConfigurationError(
                "fps must be a positive number or None for unlimited."
            )
        self._fps = value

    @property
    def renderer(self):
        """The window renderer (only while the window is open)."""
        return self.window.renderer

    @property
    def screen(self) -> tuple:
        """The window as an ``(title, width, height, fps)`` tuple.

        Assign a new ``(title, width, height)`` or ``(title, width, height,
        fps)`` tuple to change the window before it opens (e.g. inside
        :meth:`setup`):

        ``self.screen = "Game", 800, 600``
        ``self.screen = "Game", 800, 600, 60``
        """
        return (self.window.title, self.window.width, self.window.height, self.fps)

    @screen.setter
    def screen(self, value: object) -> None:
        try:
            parts = tuple(value)
        except TypeError:
            raise ConfigurationError(
                "screen must be a (title, width, height[, fps]) tuple, "
                f"got {value!r}."
            )
        if not (3 <= len(parts) <= 4):
            raise ConfigurationError(
                "screen must be a (title, width, height[, fps]) tuple, "
                f"got {len(parts)} values."
            )
        title, width, height = parts[0], parts[1], parts[2]
        self.window.title = title
        self.window.resize(width, height)
        if len(parts) == 4:
            self.fps = parts[3]

    def setup(self) -> None:
        """Override to configure the game *without* writing ``__init__``.

        Called automatically at the end of :meth:`__init__`, once the
        default window, clock, input and scenes already exist.  Use it to
        set ``self.screen``, ``self.fps`` and ``self.background``:

        .. code-block:: python

            class MyGame(pydex_ge.Game):
                def setup(self):
                    self.screen = "My Game", 800, 600   # title, w, h
                    self.fps = 60
                    self.background = (20, 22, 30)
        """

    def update(self, dt: float) -> None:
        """Override to update game logic.  Called once per frame with the delta time in seconds.

        The current scene (if any) is updated right after this hook runs,
        so a scene-based game does not need to override this method.
        """

    def draw(self) -> None:
        """Override to draw the frame (onto the cleared background).

        Use ``self.renderer.draw`` to draw pixels, lines, rectangles, and
        circles.  The current scene (if any) is drawn right after this
        hook, then the frame is presented automatically.
        """

    def run(self, *, max_frames: int | None = None) -> None:
        """Run the main loop until the game closes or ``max_frames`` is reached.

        Each frame: poll events, compute delta time, call :meth:`update`,
        update the current scene, clear the frame to :attr:`background`,
        call :meth:`draw`, draw the current scene, then present the frame.
        The window and backend are always cleaned up, even if the loop
        exits with an error.
        """
        if self._running:
            raise RuntimeError("Game.run() was called while already running.")
        self._running = True
        frame = 0
        try:
            self.window.open()
            while self._running:
                self.events.poll()
                self.input.begin_frame()
                close_requested = self.window.closed
                for event in self.events:
                    self.input.handle_event(event)
                    self.scenes.handle_event(event)
                    if event.type is EventType.QUIT or event.type is EventType.WINDOW_CLOSE:
                        close_requested = True
                    elif event.type is EventType.WINDOW_RESIZED:
                        self.window.resize(event.data["width"], event.data["height"])
                if close_requested:
                    break
                dt = self.clock.tick(self.fps)
                self.update(dt)
                self.scenes.update(dt)
                if not self._running:
                    break
                self.window.renderer.clear(self._background)
                self.draw()
                self.scenes.draw(self.window.renderer)
                if not self._running:
                    break
                self.window.renderer.present()
                frame += 1
                if max_frames is not None and frame >= max_frames:
                    break
        finally:
            self._running = False
            self.window.close()
            self._backend.quit()

    def close(self) -> None:
        """Stop the loop (if running) and release the window and backend."""
        self._running = False
        self.window.close()
        self._backend.quit()


__all__ = ["Game"]