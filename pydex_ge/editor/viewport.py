"""The editor canvas: a widget that renders and edits one scene.

The viewport is a normal screen-space widget whose interior switches to
world coordinates through a :class:`~pydex_ge.core.Camera2D`.  It draws a
grid, the scene's placed sprites, and a selection outline, and routes
mouse edits back into the project's :class:`SpriteEntry` list.

Mouse editing:
    * ``left`` on a sprite selects/drag-moves it,
    * ``left`` on empty grid places the palette asset (grid-snapped,
      scaled to fill the clicked cell, and refused when a sprite already
      occupies that cell),
    * ``middle`` drags to pan,
    * ``right`` (handled by the editor scene) deletes.
"""

from __future__ import annotations

import math
import os

from ..core import Camera2D
from ..graphics import Sprite
from ..ui import Panel
from .project import DexProject, SceneEntry, SpriteEntry

GRID_COLOR = (70, 70, 70)
SELECTION_COLOR = (110, 180, 255)


class Viewport(Panel):
    """A scene canvas widget bound to a project scene."""

    def __init__(
        self,
        *,
        project: DexProject | None = None,
        on_change=None,
        on_message=None,
        sprite_backend=None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("background", (26, 26, 32))
        kwargs.setdefault("border", (80, 80, 80))
        super().__init__(**kwargs)
        self._sprite_backend = sprite_backend
        self._camera: Camera2D | None = None
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._zoom = 1.0
        self.project = project
        self.scene: SceneEntry | None = None
        self._sprite_cache: dict[str, Sprite] = {}
        self._screen_rects: dict[int, tuple[int, int, int, int]] = {}
        self.selected: SpriteEntry | None = None
        self.palette: str | None = None
        self.snap_to_grid = True
        self._dragging = False
        self._drag_offset = (0.0, 0.0)
        self._panning = False
        self._last = (0, 0)
        self.on_change = on_change
        self.on_message = on_message

    def _report(self, message: str) -> None:
        """Route a user-facing status message to the editor UI (if wired)."""
        if self.on_message is not None:
            self.on_message(message)

    def _cell_occupied(self, wx: float, wy: float) -> bool:
        """True when a sprite already occupies the grid cell at ``(wx, wy)``."""
        if self.scene is None:
            return False
        cell = max(1.0, self.scene.grid)
        ci, cj = math.floor(wx / cell), math.floor(wy / cell)
        for entry in self.scene.sprites:
            if math.floor(entry.x / cell) == ci and math.floor(entry.y / cell) == cj:
                return True
        return False

    # -- project binding ----------------------------------------------------

    def set_project(self, project: DexProject, scene_name: str | None = None) -> None:
        """Point the viewport at a project (and optionally a scene)."""
        self.project = project
        self._sprite_cache.clear()
        self._screen_rects.clear()
        self.selected = None
        self.palette = None
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._zoom = 1.0
        name = scene_name or (project.scenes[0].name if project.scenes else None)
        self.scene = project.scene(name) if name is not None else None

    def set_scene(self, scene_name: str) -> None:
        if self.project is None:
            return
        self.scene = self.project.scene(scene_name)
        self.selected = None
        self._screen_rects.clear()

    # -- camera ---------------------------------------------------------------

    def _ensure_camera(self) -> None:
        if self.width <= 0 or self.height <= 0:
            return
        if self._camera is None or self._camera.width != self.width or self._camera.height != self.height:
            self._camera = Camera2D(
                self.width, self.height, position=(0, 0), zoom=1.0
            )
        self._camera.zoom = self._zoom
        # The camera maps world -> window coordinates; the widget offset is
        # baked into its position so sprites/grid land inside this panel.
        self._camera.position = (
            self._pan_x - self.x / self._zoom,
            self._pan_y - self.y / self._zoom,
        )

    def _center_on(self, wx: float, wy: float) -> None:
        self._ensure_camera()
        self._pan_x = wx
        self._pan_y = wy

    def zoom_world(self, factor: float) -> None:
        """Multiply the view zoom, keeping the panel center fixed."""
        self._zoom = min(8.0, max(0.05, self._zoom * factor))

    def _world_click(self, mx: int, my: int) -> tuple[float, float]:
        self._ensure_camera()
        if self._camera is None:
            return (0.0, 0.0)
        point = self._camera.screen_to_world((mx, my))
        return (point.x, point.y)

    # -- hit testing ---------------------------------------------------------------

    def sprite_at(self, mx: int, my: int) -> SpriteEntry | None:
        """Topmost sprite under a screen point (with a small tolerance)."""
        if self.scene is None:
            return None
        best_layer = None
        best: SpriteEntry | None = None
        for index in range(len(self.scene.sprites) - 1, -1, -1):
            entry = self.scene.sprites[index]
            rect = self._screen_rects.get(id(entry))
            if rect is None:
                continue
            x, y, width, height = rect
            pad = 4
            if x - pad <= mx < x + width + pad and y - pad <= my < y + height + pad:
                if best is None or entry.layer >= best_layer:
                    best = entry
                    best_layer = entry.layer
        if best is not None:
            return best
        if self._camera is None:
            return None
        cell = max(1, self.scene.grid)
        size = round(cell * self._zoom)
        for index in range(len(self.scene.sprites) - 1, -1, -1):
            entry = self.scene.sprites[index]
            origin = self._camera.world_to_screen((entry.x, entry.y))
            cx, cy = round(origin.x), round(origin.y)
            if cx <= mx < cx + size and cy <= my < cy + size:
                if best is None or entry.layer >= best_layer:
                    best = entry
                    best_layer = entry.layer
        return best

    # -- widget hooks ---------------------------------------------------------------

    def poll(self, input, mx: int, my: int) -> None:
        """Handle per-frame mouse interaction while the pointer is over."""
        self._ensure_camera()
        if self.scene is None or self._camera is None:
            return
        # Pan with the middle button.
        if input.is_button_down("middle"):
            if not self._panning:
                self._panning = True
                self._last = (mx, my)
            else:
                dx = mx - self._last[0]
                dy = my - self._last[1]
                self._pan_x -= dx / self._zoom
                self._pan_y -= dy / self._zoom
                self._last = (mx, my)
        elif self._panning:
            self._panning = False

        if input.is_button_pressed("left"):
            hit = self.sprite_at(mx, my)
            if hit is not None:
                self.selected = hit
                wx, wy = self._world_click(mx, my)
                self._drag_offset = (hit.x - wx, hit.y - wy)
                self._dragging = True
            else:
                self.selected = None
                self._dragging = False
                if self.palette is not None:
                    self._place_palette(mx, my)
        if input.is_button_down("left") and self._dragging and self.selected is not None:
            wx, wy = self._world_click(mx, my)
            x = wx + self._drag_offset[0]
            y = wy + self._drag_offset[1]
            if self.snap_to_grid:
                cell = max(1.0, self.scene.grid)
                x = round(x / cell) * cell
                y = round(y / cell) * cell
            self.selected.x = x
            self.selected.y = y
            self._mark_dirty()
        if not input.is_button_down("left"):
            self._dragging = False

    def handle_keys(self, input) -> None:
        return None

    def _place_palette(self, mx: int, my: int) -> bool:
        wx, wy = self._world_click(mx, my)
        if self.snap_to_grid:
            cell = max(1.0, self.scene.grid)
            wx = math.floor(wx / cell) * cell
            wy = math.floor(wy / cell) * cell
        if self._cell_occupied(wx, wy):
            self._report("That cell already has a sprite.")
            return False
        entry = SpriteEntry(self.palette, x=wx, y=wy)
        sprite = self._sprite(self.palette)
        if sprite is not None:
            cell = max(1.0, self.scene.grid)
            entry.scale = (
                cell / max(1, sprite.width),
                cell / max(1, sprite.height),
            )
        self.scene.sprites.append(entry)
        self.selected = entry
        self._mark_dirty()
        return True

    def align_all_to_grid(self) -> int:
        """Snap every sprite in the scene to the nearest grid cell.

        Returns the number of sprites that actually moved.
        """
        if self.scene is None:
            return 0
        cell = max(1.0, self.scene.grid)
        moved = 0
        for entry in self.scene.sprites:
            x = round(entry.x / cell) * cell
            y = round(entry.y / cell) * cell
            if (x, y) != (entry.x, entry.y):
                entry.x = x
                entry.y = y
                moved += 1
        if moved:
            self._mark_dirty()
        return moved

    def _mark_dirty(self) -> None:
        if self.project is not None:
            self.project.dirty = True
        if self.on_change is not None:
            self.on_change()

    # -- rendering --------------------------------------------------------------

    def draw(self, renderer) -> None:
        self._ensure_camera()
        super().draw(renderer)
        if self.scene is None or self._camera is None:
            return
        camera = self._camera
        # Grid (screen space, derived from world coordinates).  The camera
        # maps to window coordinates (the widget offset is baked into its
        # position), so the visible range is the widget's window-space rect.
        cell = max(1.0, self.scene.grid)
        tl = camera.screen_to_world((self.x, self.y))
        br = camera.screen_to_world((self.x + self.width, self.y + self.height))
        import math

        start_x = math.floor(tl.x / cell) * cell
        end_x = br.x + cell
        start_y = math.floor(tl.y / cell) * cell
        end_y = br.y + cell
        gx = start_x
        while gx <= end_x:
            sx = round(camera.world_to_screen((gx, 0)).x)
            if self.x <= sx <= self.x + self.width:
                renderer.draw.line(sx, self.y, sx, self.y + self.height, GRID_COLOR)
            gx += cell
        gy = start_y
        while gy <= end_y:
            sy = round(camera.world_to_screen((0, gy)).y)
            if self.y <= sy <= self.y + self.height:
                renderer.draw.line(self.x, sy, self.x + self.width, sy, GRID_COLOR)
            gy += cell

        # Sprites (world space through the camera).
        self._screen_rects.clear()
        renderer.begin_camera(camera)
        try:
            for entry in sorted(self.scene.sprites, key=lambda s: s.layer):
                if not entry.visible:
                    continue
                sprite = self._sprite(entry.asset)
                if sprite is None:
                    continue
                sprite.position = (round(entry.x), round(entry.y))
                sprite.scale = entry.scale
                sprite.flip_x = entry.flip_h
                sprite.flip_y = entry.flip_v
                sprite.draw(renderer)
                self._screen_rects[id(entry)] = self._world_rect(entry, sprite)
        finally:
            renderer.end_camera()

        if self.selected is not None:
            rect = self._screen_rects.get(id(self.selected))
            if rect is not None:
                x, y, width, height = rect
                renderer.draw.rect(
                    x - 3,
                    y - 3,
                    width + 6,
                    height + 6,
                    SELECTION_COLOR,
                    filled=False,
                )

    def _world_rect(self, entry: SpriteEntry, sprite: Sprite) -> tuple[int, int, int, int]:
        """The sprite's on-screen bounds (origin-centered so we offset by half)."""
        camera = self._camera
        if isinstance(entry.scale, tuple):
            scale_x, scale_y = entry.scale
        else:
            scale_x = scale_y = entry.scale
        width = max(1, round(sprite.width * scale_x * camera.zoom))
        height = max(1, round(sprite.height * scale_y * camera.zoom))
        origin = sprite.origin
        sx = camera.world_to_screen((entry.x, entry.y))
        x = round(sx.x - origin[0] * width)
        y = round(sx.y - origin[1] * height)
        return (x, y, width, height)

    def _sprite(self, filename: str) -> Sprite | None:
        cached = self._sprite_cache.get(filename)
        if cached is not None:
            return cached
        if self.project is None:
            return None
        path = os.path.join(self.project.root, "assets", filename)
        if not os.path.isfile(path):
            return None
        try:
            sprite = Sprite(path, backend=self._sprite_backend)
        except Exception:
            return None
        self._sprite_cache[filename] = sprite
        return sprite


__all__ = ["Viewport"]