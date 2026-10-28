"""dex-editor: the PYDEX project editor (a ``pydex_ge.Game`` app).

Usage::

    python -m pydex_ge.editor create path/to/project "My Game"
    python -m pydex_ge.editor path/to/project

The editor is intentionally a normal PYDEX game so it runs anywhere the
engine runs and reuses the engine's input/rendering.  It ships inside
the ``pydex_ge`` package, so ``pip install pydex_ge`` provides it too.
"""

from __future__ import annotations

import os

from ..core import Game
from ..exceptions import ConfigurationError
from ..graphics import Font
from ..ui import (
    GRAY_BORDER,
    GRAY_SELECTED,
    GRAY_SURFACE,
    Button,
    Label,
    ListBox,
    Panel,
    TextInput,
    UIRoot,
)
from . import _pixels
from . import assets as _assets
from .anim import AnimMode
from .assets import kind_of, orphaned, scan_assets, unregistered
from .codegen import generate_main, generate_scene, scene_class_name
from .project import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    AssetEntry,
    DexProject,
    SceneEntry,
    SpriteEntry,
    asset_kind,
)
from .spritemode import SpriteMode
from .viewport import Viewport

TOOLBAR_HEIGHT = 44
STATUS_HEIGHT = 26
SIDEBAR_WIDTH = 240
PROPS_WIDTH = 240

SPRITE_HELP = "Pick a sprite or create one, draw, then Save PNG."
ANIM_HELP = "Pick a source, add frames, set Speed (FPS), Play, then Export sheet."

MODE_LEVEL = "level"
MODE_SPRITE = "sprite"
MODE_ANIM = "anim"
MODES = (MODE_LEVEL, MODE_SPRITE, MODE_ANIM)

_MODE_LABELS = {MODE_LEVEL: "Level", MODE_SPRITE: "Sprites", MODE_ANIM: "Animate"}

STATUS_IDLE = ""
STATUS_SAVED = "Project saved."
STATUS_GENERATED = "main.py written."
STATUS_SKIPPED = "main.py already exists - keeping your edits."

HELP_TEXT = (
    "middle-drag: pan   +/-: zoom   "
    "click sprite: select/move   click grid: place   Del: remove"
)


class _EditorUI:
    """Builds and owns the widget tree.  Kept separate so the logic is
    testable without a live window."""

    def __init__(self, editor: Editor) -> None:
        self.editor = editor
        self.project = editor.project
        self.status = STATUS_IDLE
        self._build()

    def _build(self) -> None:
        project = self.project
        font = self.editor.font
        window = self.editor.window

        self.root = UIRoot()

        # Toolbar.
        self.toolbar = Panel(
            background=(30, 30, 36), border=GRAY_BORDER, height=TOOLBAR_HEIGHT
        )
        self.save_button = Button(
            "Save", font=font, on_click=self._on_save, width=70, height=30
        )
        self.generate_button = Button(
            "Generate main.py", font=font, on_click=self._on_generate,
            width=170, height=30,
        )
        self.toolbar.add(self.save_button, self.generate_button)

        self.mode_buttons: dict[str, Button] = {}
        for mode in MODES:
            button = Button(
                _MODE_LABELS[mode], font=font, on_click=self._make_mode_callback(mode),
                width=88, height=30,
            )
            self.mode_buttons[mode] = button
            self.toolbar.add(button)

        # Left sidebar: scenes + assets.
        self.sidebar = Panel(background=(24, 24, 30), border=GRAY_BORDER)
        self.scene_title = Label("Scenes", font=font, color=(220, 220, 220))
        self.scene_box = ListBox(
            on_select=self._on_scene_selected, font=font, item_height=22
        )
        self.scene_name = TextInput(
            "", placeholder="Scene name", font=font, on_submit=self._on_add_scene
        )
        self.add_scene_button = Button("+ Add", font=font, on_click=self._on_add_scene)
        self.asset_title = Label("Assets (images)", font=font, color=(220, 220, 220))
        self.asset_box = ListBox(
            on_select=self._on_palette_selected, font=font, item_height=22
        )
        self.refresh_button = Button(
            "Refresh", font=font, on_click=self._on_refresh, width=100, height=28
        )
        self.sidebar.add(
            self.scene_title,
            self.scene_box,
            self.scene_name,
            self.add_scene_button,
            self.asset_title,
            self.asset_box,
            self.refresh_button,
        )

        # Viewport fills the middle.
        self.viewport = Viewport(
            project=project,
            on_change=self._on_edited,
            on_message=self._on_viewport_message,
            sprite_backend=self.editor._backend,
        )

        # Right properties panel.
        self.props = Panel(background=(24, 24, 30), border=GRAY_BORDER)
        self.props_title = Label("Properties", font=font, color=(220, 220, 220))
        self.props_name_caption = Label("Name", font=font, color=(150, 150, 150))
        self.props_name = Label("(nothing selected)", font=font, color=(190, 190, 190))
        self.props_pos_caption = Label("Position", font=font, color=(150, 150, 150))
        self.props_pos = Label("", font=font, color=(150, 150, 150), align="right")
        self.snap_button = Button(
            "Snap: on", font=font, on_click=self._toggle_snap, width=140, height=28
        )
        self.remove_button = Button(
            "Remove selected", font=font, on_click=self._remove_selected,
            width=200, height=28,
        )
        self.align_button = Button(
            "Align to grid", font=font, on_click=self._align_to_grid,
            width=140, height=28,
        )
        self.grid_caption = Label("Grid (px)", font=font, color=(150, 150, 150))
        self.grid_input = TextInput("32", font=font, on_submit=self._on_set_grid)
        self.props.add(
            self.props_title,
            self.props_name_caption,
            self.props_name,
            self.props_pos_caption,
            self.props_pos,
            self.snap_button,
            self.remove_button,
            self.align_button,
            self.grid_caption,
            self.grid_input,
        )

        # Bottom status bar.
        self.status_bar = Panel(background=(30, 30, 36), border=GRAY_BORDER)
        self.status_label = Label("", font=font, color=(200, 200, 200))

        self.root.add(
            self.toolbar,
            self.sidebar,
            self.viewport,
            self.props,
            self.status_bar,
            self.status_label,
        )

        self.sprite_mode = SpriteMode(self)
        self.anim_mode = AnimMode(self)

        self.mode = MODE_LEVEL
        self._layout(window.width, window.height)
        self._set_mode(MODE_LEVEL)

        self._refresh_scene_box()
        self._refresh_asset_box()

    def _layout(self, width: int, height: int) -> None:
        """Position every widget for the given window size."""
        self.root.width, self.root.height = width, height

        # Toolbar.
        self.toolbar.x, self.toolbar.y = 0, 0
        self.toolbar.width, self.toolbar.height = width, TOOLBAR_HEIGHT
        self.save_button.x, self.save_button.y = 12, 7
        self.generate_button.x, self.generate_button.y = 92, 7
        button_x = 280
        for mode in MODES:
            button = self.mode_buttons[mode]
            button.x, button.y = button_x, 7
            button_x += 94

        # Sidebar.
        sidebar_h = max(0, height - TOOLBAR_HEIGHT - STATUS_HEIGHT)
        self.sidebar.x, self.sidebar.y = 0, TOOLBAR_HEIGHT
        self.sidebar.width, self.sidebar.height = SIDEBAR_WIDTH, sidebar_h
        self.scene_title.x, self.scene_title.y = 12, TOOLBAR_HEIGHT + 8
        self.scene_box.x, self.scene_box.y = 8, TOOLBAR_HEIGHT + 30
        self.scene_box.width, self.scene_box.height = SIDEBAR_WIDTH - 16, 132
        self.scene_name.x, self.scene_name.y = 8, TOOLBAR_HEIGHT + 172
        self.scene_name.width, self.scene_name.height = 140, 28
        self.add_scene_button.x, self.add_scene_button.y = 156, TOOLBAR_HEIGHT + 172
        self.add_scene_button.width, self.add_scene_button.height = 76, 28
        self.asset_title.x, self.asset_title.y = 12, TOOLBAR_HEIGHT + 212
        asset_top = TOOLBAR_HEIGHT + 236
        self.asset_box.x, self.asset_box.y = 8, asset_top
        self.asset_box.width = SIDEBAR_WIDTH - 16
        self.asset_box.height = max(40, (height - STATUS_HEIGHT - 46) - asset_top)
        self.refresh_button.x, self.refresh_button.y = 8, height - STATUS_HEIGHT - 38

        # Viewport.
        self.viewport.x, self.viewport.y = SIDEBAR_WIDTH, TOOLBAR_HEIGHT
        self.viewport.width = max(0, width - SIDEBAR_WIDTH - PROPS_WIDTH)
        self.viewport.height = sidebar_h

        # Properties panel.
        self.props.x, self.props.y = width - PROPS_WIDTH, TOOLBAR_HEIGHT
        self.props.width, self.props.height = PROPS_WIDTH, sidebar_h
        props_x = width - PROPS_WIDTH + 12
        props_value_w = PROPS_WIDTH - 24
        self.props_title.x, self.props_title.y = props_x, TOOLBAR_HEIGHT + 8
        self.props_name_caption.x, self.props_name_caption.y = props_x, TOOLBAR_HEIGHT + 36
        self.props_name.x, self.props_name.y = props_x, TOOLBAR_HEIGHT + 36
        self.props_name.width, self.props_name.height = props_value_w, 20
        self.props_name.align = "right"
        self.props_pos_caption.x, self.props_pos_caption.y = props_x, TOOLBAR_HEIGHT + 60
        self.props_pos.x, self.props_pos.y = props_x, TOOLBAR_HEIGHT + 60
        self.props_pos.width, self.props_pos.height = props_value_w, 20
        self.snap_button.x, self.snap_button.y = props_x, TOOLBAR_HEIGHT + 94
        self.remove_button.x, self.remove_button.y = props_x, TOOLBAR_HEIGHT + 130
        self.remove_button.width = PROPS_WIDTH - 24
        self.align_button.x, self.align_button.y = props_x, TOOLBAR_HEIGHT + 166
        self.grid_caption.x, self.grid_caption.y = props_x, TOOLBAR_HEIGHT + 202
        self.grid_input.x, self.grid_input.y = props_x, TOOLBAR_HEIGHT + 226
        self.grid_input.width, self.grid_input.height = props_value_w, 28

        # Status bar.
        self.status_bar.x, self.status_bar.y = 0, height - STATUS_HEIGHT
        self.status_bar.width, self.status_bar.height = width, STATUS_HEIGHT
        self.status_label.x, self.status_label.y = 12, height - STATUS_HEIGHT + 5

        self.sprite_mode.resize(width, height)
        self.anim_mode.resize(width, height)

    # -- modes ---------------------------------------------------------------

    def _make_mode_callback(self, mode):
        def switch():
            self._set_mode(mode)
        return switch

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        level = mode == MODE_LEVEL
        self.sidebar.visible = level
        self.viewport.visible = level
        self.props.visible = level
        self.sprite_mode.hide()
        self.anim_mode.hide()
        if mode == MODE_SPRITE:
            self.sprite_mode.show()
        elif mode == MODE_ANIM:
            self.anim_mode.show()
        for name, button in self.mode_buttons.items():
            button.background = GRAY_SELECTED if name == mode else GRAY_SURFACE
        self.status = STATUS_IDLE

    # -- layout ---------------------------------------------------------------

    def resize(self, width: int, height: int) -> None:
        """Update sizes/positions after a window resize."""
        self._layout(width, height)

    # -- UI sync ---------------------------------------------------------------

    def _refresh_scene_box(self) -> None:
        self.scene_box.clear()
        for scene in self.project.scenes:
            self.scene_box.append(scene.name)
        self.scene_box.selected = None

    def _refresh_asset_box(self) -> None:
        self.asset_box.clear()
        for entry in self.project.assets:
            if entry.kind == "image":
                self.asset_box.append(entry.filename)

    # -- actions ---------------------------------------------------------------

    def _on_save(self) -> None:
        self.project.save()
        self.status = STATUS_SAVED

    def _on_generate(self) -> None:
        path = self.project.main_path
        if os.path.exists(path):
            self.status = STATUS_SKIPPED
            return
        self.project.write_starter_code()
        self.status = STATUS_GENERATED

    def _on_refresh(self) -> None:
        unique = {}
        for entry in self.project.assets:
            unique.setdefault(entry.filename, entry)
        if len(unique) != len(self.project.assets):
            self.project.assets = list(unique.values())
            self.project.dirty = True
        removed = 0
        for name in _assets.orphaned(self.project):
            self.project.remove_asset(name)
            removed += 1
        imported = []
        supported = IMAGE_EXTENSIONS + AUDIO_EXTENSIONS
        for name in _assets.unregistered(self.project):
            if os.path.splitext(name)[1].lower() not in supported:
                continue
            path = os.path.join(self.project.assets_dir(), name)
            if os.path.isfile(path):
                self.project.import_asset(path)
                imported.append(name)
        self._refresh_asset_box()
        self.status = f"Refresh: +{len(imported)} added, -{removed} removed."

    def _on_scene_selected(self, scene_name) -> None:
        self.viewport.set_scene(str(scene_name))

    def _on_palette_selected(self, filename) -> None:
        self.viewport.palette = str(filename)

    def _on_add_scene(self) -> None:
        name = self.scene_name.value.strip()
        if not name:
            self.status = "Scene name must not be empty."
            return
        try:
            self.project.add_scene(name)
        except ConfigurationError as exc:
            self.status = str(exc)
            return
        self.scene_name.value = ""
        self.scene_name.caret = 0
        self._refresh_scene_box()
        self.viewport.set_scene(name)
        self.status = STATUS_IDLE

    def _toggle_snap(self) -> None:
        self.viewport.snap_to_grid = not self.viewport.snap_to_grid
        self.snap_button.text = f"Snap: {'on' if self.viewport.snap_to_grid else 'off'}"

    def _remove_selected(self) -> None:
        selected = self.viewport.selected
        if selected is None or self.viewport.scene is None:
            return
        scene = self.viewport.scene
        scene.sprites = [s for s in scene.sprites if s is not selected]
        self.viewport.selected = None
        self._mark_dirty()

    def _align_to_grid(self) -> None:
        moved = self.viewport.align_all_to_grid()
        if moved:
            self.status = f"Aligned {moved} sprite{'s' if moved != 1 else ''} to grid."
        else:
            self.status = "Already on grid."

    def _on_set_grid(self, value=None) -> None:
        if self.viewport.scene is None:
            self.status = "No scene selected."
            return
        raw = (value if value is not None else self.grid_input.value).strip()
        try:
            size = max(1.0, float(raw))
        except ValueError:
            self.status = "Grid must be a number."
            return
        self.viewport.scene.grid = size
        self.project.dirty = True
        self.grid_input.value = f"{size:g}"
        self.status = f"Grid set to {size:g}px"

    def _on_edited(self) -> None:
        self.status = STATUS_IDLE

    def _on_viewport_message(self, message: str) -> None:
        self.status = message

    def _mark_dirty(self) -> None:
        self.project.dirty = True
        self.status = STATUS_IDLE

    # -- per-frame ---------------------------------------------------------------

    def update_status(self) -> None:
        selected = self.viewport.selected
        if selected is None:
            self.props_name.text = "(nothing selected)"
            self.props_pos.text = ""
        else:
            self.props_name.text = selected.asset
            self.props_pos.text = (
                f"x={selected.x:g}  y={selected.y:g}  layer={selected.layer}"
            )
        if (
            self.mode == MODE_LEVEL
            and self.viewport.scene is not None
            and not self.grid_input.focused
        ):
            expected = f"{self.viewport.scene.grid:g}"
            if self.grid_input.value != expected:
                self.grid_input.value = expected
        prefix = "* " if self.project.dirty else ""
        message = self.status
        if not message and self.mode == MODE_SPRITE:
            message = self.sprite_mode.last_saved
        elif not message and self.mode == MODE_ANIM:
            message = self.anim_mode.last_saved
        self.status_label.text = f"{prefix}{message or HELP_TEXT}"
        self.sprite_mode.status_label.text = (
            f"{prefix}{self.sprite_mode.last_saved or SPRITE_HELP}"
        )
        self.anim_mode.status_label.text = (
            f"{prefix}{self.anim_mode.last_saved or ANIM_HELP}"
        )

    def update_mode(self, dt: float) -> None:
        if self.mode == MODE_ANIM:
            self.anim_mode.tick(dt)


class Editor(Game):
    """The dex-editor application."""

    def __init__(
        self,
        project: DexProject,
        *,
        width: int = 1280,
        height: int = 720,
        backend=None,
    ) -> None:
        self.project = project
        self.font: Font | None = None
        self._ui: _EditorUI | None = None
        super().__init__(
            title=f"dex-editor - {project.name}",
            width=width,
            height=height,
            fps=60,
            backend=backend,
        )

    def setup(self) -> None:
        self.background = (18, 18, 24)
        try:
            self.font = Font(size=16, backend=self._backend)
        except ConfigurationError:
            self.font = None
        self._ui = _EditorUI(self)
        if self.project.scenes:
            self._ui.viewport.set_scene(self.project.scenes[0].name)

    def _shortcuts(self) -> None:
        ui = self._ui
        if ui is None:
            return
        if self.input.is_key_pressed("escape") and ui.root.focused is None:
            ui.viewport.selected = None
            ui.viewport.palette = None
        if self.input.is_key_pressed("delete") and ui.root.focused is None:
            ui._remove_selected()
        if self.input.is_key_pressed("="):
            ui.viewport.zoom_world(1.2)
        if self.input.is_key_pressed("-"):
            ui.viewport.zoom_world(1 / 1.2)
        step = 40 / ui.viewport._zoom
        if self.input.is_key_down("left") and ui.root.focused is None:
            ui.viewport._pan_x -= step
        if self.input.is_key_down("right") and ui.root.focused is None:
            ui.viewport._pan_x += step
        if self.input.is_key_down("up") and ui.root.focused is None:
            ui.viewport._pan_y -= step
        if self.input.is_key_down("down") and ui.root.focused is None:
            ui.viewport._pan_y += step

    def update(self, dt: float) -> None:
        ui = self._ui
        if ui is None:
            return
        width, height = self.window.width, self.window.height
        if (width, height) != (ui.root.width, ui.root.height):
            ui.resize(width, height)
        if self.input.is_key_pressed("s") and (
            self.input.is_key_down("control") or self.input.is_key_down("ctrl")
        ):
            ui._on_save()
        self._shortcuts()
        ui.root.handle_input(self.input)
        ui.update_mode(dt)
        ui.update_status()

    def draw(self) -> None:
        ui = self._ui
        if ui is None:
            return
        ui.root.draw(self.window.renderer)


__all__ = [
    "Editor",
    "SpriteMode",
    "AnimMode",
    "_pixels",
    "generate_main",
    "generate_scene",
    "scene_class_name",
    "DexProject",
    "AssetEntry",
    "SceneEntry",
    "SpriteEntry",
    "asset_kind",
    "Viewport",
    "scan_assets",
    "unregistered",
    "orphaned",
    "kind_of",
    "MODE_LEVEL",
    "MODE_SPRITE",
    "MODE_ANIM",
    "MODES",
    "TOOLBAR_HEIGHT",
    "STATUS_HEIGHT",
    "SIDEBAR_WIDTH",
    "PROPS_WIDTH",
]