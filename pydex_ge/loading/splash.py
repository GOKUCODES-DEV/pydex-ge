"""The :class:`SplashScreen`: a loading and intro scene.

A splash screen shows a logo, a game name/version, and loading progress
while game resources are silently checked and loaded, then hands control
to the next scene.  It is a :class:`~pydex_ge.scene.scene.Scene`, so it plugs
into any :class:`~pydex_ge.scene.manager.SceneManager` stack.

Lifecycle
---------
``idle -> checking -> loading -> starting -> done``

* **checking** — when ``file_checking=True``, every referenced asset file
  is verified to exist.  The screen only ever shows a generic
  ``Checking...`` message; asset file names never appear in the UI.
* **loading** — each entry of ``loadables`` is loaded through a shared
  :class:`~pydex_ge.assets.Assets` cache, one entry every ``1/loading_speed``
  seconds.  Progress advances on the bar.
* **starting** — a brief ``Starting...`` pause once everything is loaded.
* **done** — once ``min_duration`` (if set) has elapsed, the splash
  auto-transitions to ``next_scene`` with ``manager.replace(...)``.

No phase ever ``sleep()``s.  Timing is driven deterministically by the
accumulated ``update(dt)`` time, so a headless test can advance the splash
frame by frame by calling ``update()`` directly.

Loadables
---------
``loadables`` entries are either ``('kind', path, ...)`` tuples handled by
the loader registry, or plain callables that receive the shared
:class:`Assets`:

* ``("image", path)`` — :meth:`Assets.image`
* ``("font", path, size)`` — :meth:`Assets.font`
* ``("sprite_sheet", path, cell_width, cell_height)`` — :meth:`Assets.sprite_sheet`
* ``lambda assets: assets.image("logo.png")`` — any callable (may return ``None``)

New kinds can be added with :meth:`register_loader`, a class method that
works from the class or an instance.  This is the extension point for
future asset types (including 3D loaders in a later part).

Resource ownership
------------------
When ``assets`` is given, the splash reuses it and never destroys it.  When
``assets`` is omitted, the splash creates (and owns) an :class:`Assets`,
loading everything — including a path-based ``logo`` — through it, and
frees it on exit.  A ``logo`` passed as an :class:`Image` or
:class:`~pydex_ge.graphics.sprite.Sprite` is shared and never destroyed.
"""

from __future__ import annotations

import math
import os

from ..assets import Assets
from ..check import _caller_info
from ..core.events import EventType
from ..exceptions import (
    ConfigurationError,
    MissingAssetError,
    missing_asset_message,
)
from ..graphics.color import normalize_rgba
from ..graphics.font import Font
from ..graphics.image import Image
from ..graphics.label import Label
from ..graphics.sprite import Sprite
from ..scene.scene import Scene

_SHAPES = ("none", "circle", "rounded")


def _size(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"{name} must be a positive integer, got {value!r}.")
    return value


def _positive_number(
    value: object, name: str, *, allow_none: bool = False
) -> float | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigurationError(f"{name} must be a positive number, got {value!r}.")
    return float(value)


def _require_non_empty_string(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{name} must be a non-empty string, got {value!r}.")


def _mix(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(int(c * (1 - amount) + 128 * amount) for c in color)


class SplashScreen(Scene):
    """A loading screen with a logo, progress, and an automatic transition.

    Parameters
    ----------
    logo:
        An :class:`~pydex_ge.graphics.image.Image`, a
        :class:`~pydex_ge.graphics.sprite.Sprite`, a path to an image file, or
        ``None``.  An image path is loaded (and cached) through the shared
        :class:`Assets`.
    logo_shape:
        How the logo is clipped: ``"none"`` (rectangle), ``"circle"`` (the
        logo is clipped to the ellipse inscribed in its box), or
        ``"rounded"`` (rounded corners).  Clipping is real visual clipping
        done with the existing 2D drawing primitives over the solid
        background.
    name:
        Optional game name shown under the logo.
    name_font:
        A :class:`~pydex_ge.graphics.font.Font`, a font file path, or ``None``
        for a system font (used for the name and, when present, the status
        text).
    name_color:
        RGB/RGBA color for the name and version text.
    version:
        Optional game version, rendered as ``v1.0.0`` under the name.
    loading_speed:
        How fast loadables load: one loadable every ``1/loading_speed``
        seconds (``1.0`` ≈ one second per entry).
    file_checking:
        Verify every referenced asset file exists before loading.  Missing
        files raise :class:`~pydex_ge.exceptions.BackendError`; the UI only
        ever shows a generic ``Checking...``.
    loadables:
        An iterable of ``('kind', path, ...)`` tuples or callables to load
        (see the module docstring).
    assets:
        An :class:`Assets` to reuse.  ``None`` creates a private one that
        the splash owns and frees on exit.
    next_scene:
        A :class:`~pydex_ge.scene.scene.Scene` instance, or a callable/class
        returning one, that the splash auto-transitions to once it is
        ``done`` (and ``min_duration`` has elapsed).  ``None`` keeps the
        splash on screen.
    game:
        Optional :class:`~pydex_ge.core.game.Game`.  When set (and
        ``cancellable``), ESC or a window-close event calls ``game.close()``.
    background_color:
        RGB/RGBA color the splash clears the frame to.
    loading_color:
        RGB/RGBA color of the status text and the progress bar fill.
    loading_text:
        Text shown during the loading phase (default ``"Loading..."``).
    show_progress:
        Draw the progress bar.
    cancellable:
        Allow cancelling (closing the game) with ESC when ``game`` is set.
    min_duration:
        Minimum seconds the splash stays visible before transitioning.
        ``None`` means transition as soon as loading finishes.
    width, height:
        Logical layout size used to center the elements.
    """

    _loaders = {
        "image": lambda assets, path: assets.image(path),
        "font": lambda assets, path, size: assets.font(path, size),
        "sprite_sheet": lambda assets, path, cell_width, cell_height: assets.sprite_sheet(
            path, cell_width, cell_height
        ),
    }

    _CHECK_DURATION = 0.5
    _START_DURATION = 0.4

    def __init__(
        self,
        logo: Image | Sprite | str | None = None,
        *,
        logo_shape: str = "none",
        name: str | None = None,
        name_font: Font | str | None = None,
        name_color: object = (255, 255, 255),
        version: str | None = None,
        loading_speed: object = 1.0,
        file_checking: bool = True,
        loadables=(),
        assets: Assets | None = None,
        next_scene: Scene | object | None = None,
        game=None,
        background_color: object = (0, 0, 0),
        loading_color: object = (255, 255, 255),
        loading_text: str = "Loading...",
        show_progress: bool = True,
        cancellable: bool = True,
        min_duration: object | None = None,
        width: int = 800,
        height: int = 600,
    ) -> None:
        super().__init__()
        self._requested_by = _caller_info()

        if logo_shape not in _SHAPES:
            raise ConfigurationError(
                f"logo_shape must be one of {list(_SHAPES)!r}, got {logo_shape!r}."
            )
        if name is not None:
            _require_non_empty_string(name, "name")
        if version is not None:
            _require_non_empty_string(version, "version")
        if not isinstance(loading_text, str):
            raise ConfigurationError(f"loading_text must be a string, got {loading_text!r}.")

        self._logo_shape = logo_shape
        self._name = name
        self._version = version
        self._loading_text = loading_text
        self._loading_speed = float(_positive_number(loading_speed, "loading_speed"))
        self._file_checking = bool(file_checking)
        self._show_progress = bool(show_progress)
        self._cancellable = bool(cancellable)
        self._min_duration = _positive_number(min_duration, "min_duration", allow_none=True)
        self.width = _size(width, "width")
        self.height = _size(height, "height")

        self._background_rgba = normalize_rgba(background_color, "background_color")
        self._loading_rgba = normalize_rgba(loading_color, "loading_color")
        self._name_rgba = normalize_rgba(name_color, "name_color")

        if assets is not None and not isinstance(assets, Assets):
            raise ConfigurationError("assets must be a pydex_ge.Assets or None.")
        self._assets = assets if assets is not None else Assets()
        self._owns_assets = assets is None
        self._backend = self._assets._backend

        self.game = game
        if next_scene is not None and not isinstance(next_scene, Scene) and not callable(next_scene):
            raise ConfigurationError(
                "next_scene must be a Scene, a callable/class returning a Scene, or None."
            )
        self._next_scene = next_scene

        self._loadables = [] if loadables is None else list(loadables)
        for entry in self._loadables:
            if callable(entry):
                continue
            if isinstance(entry, (tuple, list)) and entry:
                if not isinstance(entry[0], str) or not entry[0].strip():
                    raise ConfigurationError(
                        f"Loadable kind must be a non-empty string, got {entry!r}."
                    )
                if len(entry) < 2:
                    raise ConfigurationError(
                        f"Loadable {entry!r} needs at least a kind and a path."
                    )
            else:
                raise ConfigurationError(
                    f"Invalid loadable {entry!r}. Use ('kind', path, ...) or a callable."
                )
        self._load_total = len(self._loadables)

        self._logo_sprite = None
        self._logo_path = None
        if logo is not None:
            if isinstance(logo, Sprite):
                self._logo_sprite = logo
            elif isinstance(logo, Image):
                self._logo_sprite = Sprite(logo)
            elif isinstance(logo, str):
                if not logo.strip():
                    raise ConfigurationError("Logo image path must be a non-empty string.")
                self._logo_path = os.path.abspath(logo)
                self._logo_sprite = Sprite(self._assets.image(self._logo_path))
            else:
                raise ConfigurationError(
                    "logo must be a pydex_ge.Sprite, pydex_ge.Image, a path, or None."
                )

        self._name_font: Font | None = None
        self._owns_name_font = False
        if name_font is not None:
            self._name_font, self._owns_name_font = self._resolve_font(name_font, 40)
        if name is not None and self._name_font is None:
            self._name_font = Font(None, 40, backend=self._backend)
            self._owns_name_font = True

        self._status_needed = bool(self._file_checking) or bool(self._loadables)
        self._status_font: Font | None = None
        self._owns_status_font = False
        if self._status_needed:
            if self._name_font is not None:
                self._status_font = self._name_font
            else:
                self._status_font = Font(None, 18, backend=self._backend)
                self._owns_status_font = True
        self._text_font = self._status_font or self._name_font

        self._state = "idle"
        self._progress = 0.0
        self._elapsed = 0.0
        self._check_timer = 0.0
        self._step_timer = 0.0
        self._start_timer = 0.0
        self._load_index = 0
        self._loaded: list[object] = []
        self._transitioned = False

        self._layout()

    # -- layout ---------------------------------------------------------

    def _layout(self) -> None:
        self._logo_center_y = int(self.height * 0.30)
        self._name_y = int(self.height * 0.49)
        self._version_y = (
            self._name_y + 30 if self._name is not None else int(self.height * 0.53)
        )
        self._status_y = int(self.height * 0.66)
        self._progress_y = int(self.height * 0.75)
        self._branding_y = self.height - 40

        self._logo_x = 0
        self._logo_y = 0
        self._logo_w = 0
        self._logo_h = 0
        if self._logo_sprite is not None:
            self._logo_w = int(self._logo_sprite.width * self._logo_sprite.scale)
            self._logo_h = int(self._logo_sprite.height * self._logo_sprite.scale)
            self._logo_x = self.width // 2 - self._logo_w // 2
            self._logo_y = self._logo_center_y - self._logo_h // 2
            self._logo_sprite.x = self._logo_x
            self._logo_sprite.y = self._logo_y

        self._name_label = None
        if self._name is not None and self._name_font is not None:
            self._name_label = self._centered_label(
                self._name, self._name_font, self._name_rgba, self._name_y
            )
        self._version_label = None
        if self._version is not None and self._text_font is not None:
            self._version_label = self._centered_label(
                f"v{self._version}", self._text_font, self._name_rgba, self._version_y
            )
        self._branding_label = None
        if self._text_font is not None:
            self._branding_label = self._centered_label(
                self._branding_text(),
                self._text_font,
                (150, 155, 165),
                self._branding_y,
            )
        self._status_label = None
        if self._status_needed and self._status_font is not None:
            self._status_label = self._centered_label(
                self.status, self._status_font, self._loading_rgba, self._status_y
            )

    def _centered_label(self, text: str, font: Font, color, y: int) -> Label:
        label = Label(text, font=font, position=(0, y), color=color, backend=self._backend)
        label.x = self.width // 2 - label.width // 2
        return label

    def _branding_text(self) -> str:
        from .. import __version__

        return f"PYDEX {__version__}"

    def _resolve_font(self, font: Font | str | None, size: int) -> tuple[Font | None, bool]:
        if font is None:
            return None, False
        if isinstance(font, Font):
            return font, False
        if isinstance(font, str):
            if not font.strip():
                raise ConfigurationError("Font path must be a non-empty string.")
            return Font(font, size, backend=self._backend), True
        raise ConfigurationError("Fonts must be a pydex_ge.Font, a path, or None.")

    # -- lifecycle ------------------------------------------------------

    def on_enter(self) -> None:
        """Start (or restart) the splash flow when the scene becomes current."""
        self.start()

    def on_exit(self) -> None:
        """Free the assets and fonts the splash created itself."""
        self._cleanup()

    def start(self) -> None:
        """Begin (or restart) the splash lifecycle: ``idle -> checking/loading``.

        Called automatically from :meth:`on_enter`; you can also call it by
        hand to restart the flow.  Public so a headless test (or a custom
        driver) can drive the splash deterministically.
        """
        self._state = "checking" if self._file_checking else "loading"
        self._progress = 0.0
        self._elapsed = 0.0
        self._check_timer = 0.0
        self._step_timer = 0.0
        self._start_timer = 0.0
        self._load_index = 0
        self._loaded = []
        self._transitioned = False
        if self._state == "checking":
            self._check_files()
        self._sync_status_label()

    def update(self, dt: float) -> None:
        """Advance the splash by ``dt`` seconds.

        All timing is deterministic: checking, loading steps, the starting
        pause, and the ``min_duration`` hold are driven purely by the
        accumulated delta time.
        """
        super().update(dt)
        if self._state == "idle" or self._transitioned:
            return
        self._elapsed += dt
        if self._state == "checking":
            self._check_timer += dt
            if self._check_timer >= self._CHECK_DURATION:
                self._enter_loading()
        elif self._state == "loading":
            self._step_timer += dt
            step_time = 1.0 / self._loading_speed
            while self._step_timer >= step_time and self._load_index < self._load_total:
                self._step_timer -= step_time
                self._load_next()
            if self._load_total:
                self._progress = min(1.0, self._load_index / self._load_total)
            else:
                self._progress = 1.0
            if self._load_index >= self._load_total:
                self._enter_starting()
        elif self._state == "starting":
            self._start_timer += dt
            if self._start_timer >= self._START_DURATION:
                self._enter_done()
        elif self._state == "done":
            self._maybe_transition()

    def draw(self, renderer) -> None:
        """Draw the splash: background, clipped logo, text, and progress."""
        renderer.clear(self._background_rgba[:3])
        if self._logo_sprite is not None:
            self._logo_sprite.draw(renderer)
            if self._logo_shape != "none":
                self._clip_logo(renderer)
        if self._name_label is not None:
            renderer.draw_label(self._name_label)
        if self._version_label is not None:
            renderer.draw_label(self._version_label)
        if self._branding_label is not None:
            renderer.draw_label(self._branding_label)
        if self._status_label is not None:
            renderer.draw_label(self._status_label)
        if self._show_progress:
            self._draw_progress(renderer)

    def handle_event(self, event) -> None:
        """Cancel (close the attached game) on ESC or a window-close event.

        Cancellation only happens when a ``game`` is attached and
        ``cancellable`` is true; otherwise the event is ignored safely.
        """
        super().handle_event(event)
        if not self._cancellable or self.game is None:
            return
        if event.type is EventType.QUIT or event.type is EventType.WINDOW_CLOSE:
            self.game.close()
        elif event.type is EventType.KEY_DOWN:
            key = event.data.get("key")
            if isinstance(key, str) and key.strip().lower() == "escape":
                self.game.close()

    # -- state machine --------------------------------------------------

    def _enter_loading(self) -> None:
        self._state = "loading"
        self._step_timer = 0.0
        self._progress = 0.0
        self._sync_status_label()
        if self._load_total == 0:
            self._progress = 1.0
            self._enter_starting()

    def _enter_starting(self) -> None:
        self._state = "starting"
        self._start_timer = 0.0
        self._progress = 1.0
        self._sync_status_label()

    def _enter_done(self) -> None:
        self._state = "done"
        self._progress = 1.0
        self._sync_status_label()
        self._maybe_transition()

    def _maybe_transition(self) -> None:
        if self._transitioned or self._next_scene is None or self.manager is None:
            return
        if self._min_duration is not None and self._elapsed < self._min_duration:
            return
        self._transitioned = True
        self.manager.replace(self._build_next_scene())

    def _build_next_scene(self) -> Scene:
        target = self._next_scene
        if not isinstance(target, Scene):
            target = target()
        return target

    def _sync_status_label(self) -> None:
        if self._status_label is None:
            return
        self._status_label.text = self.status
        self._status_label.x = self.width // 2 - self._status_label.width // 2

    # -- checking / loading ---------------------------------------------

    def _check_files(self) -> None:
        paths = []
        if self._logo_path is not None:
            paths.append(self._logo_path)
        for entry in self._loadables:
            if isinstance(entry, (tuple, list)) and len(entry) >= 2:
                kind, path = entry[0], entry[1]
                if kind in ("image", "font", "sprite_sheet") and isinstance(path, str):
                    paths.append(path)
        for path in paths:
            if not os.path.isfile(path):
                exc = MissingAssetError(missing_asset_message(path), path=path)
                exc.requested_by = self._requested_by
                raise exc

    def _load_next(self) -> None:
        entry = self._loadables[self._load_index]
        if callable(entry):
            result = entry(self._assets)
        else:
            kind = entry[0]
            loader = self._loaders.get(kind)
            if loader is None:
                raise ConfigurationError(f"Unknown loadable kind {kind!r}.")
            result = loader(self._assets, *entry[1:])
        self._load_index += 1
        self._loaded.append(result)

    @classmethod
    def register_loader(cls, kind: str, loader) -> None:
        """Register a loader for a new ``loadables`` kind.

        A class method, so it can be called as ``SplashScreen.register_loader(...)``
        or on an instance.  ``loader`` is called as ``loader(assets, *args)``
        where ``args`` are the remaining tuple elements of a ``('kind', *args)``
        loadable.  This is the extension point for future asset types
        (including 3D loaders in a later part).
        """
        if not isinstance(kind, str) or not kind.strip():
            raise ConfigurationError("Loader kind must be a non-empty string.")
        if not callable(loader):
            raise ConfigurationError("Loader must be callable.")
        registry = dict(cls._loaders)
        registry[kind] = loader
        cls._loaders = registry

    # -- drawing helpers ------------------------------------------------

    def _clip_logo(self, renderer) -> None:
        if self._logo_shape == "circle":
            self._clip_ellipse(renderer)
        elif self._logo_shape == "rounded":
            self._clip_rounded(renderer)

    def _clip_ellipse(self, renderer) -> None:
        """Clip the logo box to the ellipse inscribed in it, scanline by scanline.

        The background is solid, so drawing background-colored 1px-tall rects
        over every row that sticks out of the inscribed ellipse visually
        erases the corners — true clipping with the existing primitives.
        """
        x, y, w, h = self._logo_x, self._logo_y, self._logo_w, self._logo_h
        bg = self._background_rgba[:3]
        cx, cy = x + w // 2, y + h // 2
        rx, ry = w / 2.0, h / 2.0
        draw = renderer.draw
        for row in range(y, y + h):
            dy = abs(row - cy)
            if dy >= ry:
                draw.rect(x, row, w, 1, bg)
                continue
            half = int(round(rx * math.sqrt(max(0.0, 1.0 - (dy / ry) ** 2))))
            left = cx - half
            right = cx + half
            if left > x:
                draw.rect(x, row, left - x, 1, bg)
            if right < x + w - 1:
                draw.rect(right + 1, row, x + w - (right + 1), 1, bg)

    def _clip_rounded(self, renderer) -> None:
        """Clip the logo box to a rounded rectangle with a corner radius.

        Rows near the top/bottom edges are masked by a background-colored
        rect on each side, with an inset following the corner circle.
        """
        x, y, w, h = self._logo_x, self._logo_y, self._logo_w, self._logo_h
        bg = self._background_rgba[:3]
        radius = max(1, min(w, h) // 4)
        draw = renderer.draw
        for row in range(y, y + h):
            rel = row - y
            if rel < radius:
                inner = radius - math.sqrt(max(0.0, radius * radius - (rel - radius) ** 2))
            elif rel > h - radius:
                rel2 = rel - (h - radius)
                inner = radius - math.sqrt(max(0.0, radius * radius - rel2 * rel2))
            else:
                inner = 0.0
            start = int(math.floor(x + inner))
            end = int(math.ceil(x + w - inner))
            if start > x:
                draw.rect(x, row, start - x, 1, bg)
            if end < x + w:
                draw.rect(end, row, x + w - end, 1, bg)

    def _draw_progress(self, renderer) -> None:
        bar_w = int(self.width * 0.6)
        bar_h = 14
        bx = (self.width - bar_w) // 2
        by = self._progress_y
        track = _mix(self._background_rgba[:3], 0.4)
        renderer.draw.rect(bx, by, bar_w, bar_h, track)
        if self._progress > 0:
            fill_w = max(1, int(bar_w * self._progress))
            renderer.draw.rect(bx, by, fill_w, bar_h, self._loading_rgba[:3])

    # -- cleanup --------------------------------------------------------

    def _cleanup(self) -> None:
        if self._owns_assets:
            self._assets.clear()
            self._owns_assets = False
        for font, owns in (
            (self._name_font, self._owns_name_font),
            (self._status_font, self._owns_status_font),
        ):
            if font is not None and owns:
                font.destroy()
        if self._owns_name_font:
            self._owns_name_font = False
        if self._owns_status_font:
            self._owns_status_font = False

    # -- queries --------------------------------------------------------

    @property
    def state(self) -> str:
        """The current phase: ``idle``, ``checking``, ``loading``, ``starting``, or ``done``."""
        return self._state

    @property
    def progress(self) -> float:
        """Loading progress, clamped to ``0.0``–``1.0``."""
        return self._progress

    @property
    def status(self) -> str:
        """The current generic status message shown under the logo."""
        if self._state == "checking":
            return "Checking..."
        if self._state == "loading":
            return self._loading_text
        if self._state in ("starting", "done"):
            return "Starting..."
        return ""

    @property
    def loaded(self) -> list[object]:
        """The objects loaded so far, in loadable order."""
        return list(self._loaded)

    @property
    def logo(self) -> Sprite | None:
        """The resolved logo sprite, or ``None`` when no logo was given."""
        return self._logo_sprite

    @property
    def assets(self) -> Assets:
        """The shared :class:`Assets` the splash loads through."""
        return self._assets


__all__ = ["SplashScreen"]
