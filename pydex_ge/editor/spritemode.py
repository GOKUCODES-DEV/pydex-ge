"""Sprites mode: the dexpen pixel editor as a dex-editor feature.

Lets you draw a new sprite or edit an existing image asset, then save it
back into the project's ``assets/`` folder where the level viewport can
use it.
"""

from __future__ import annotations

import os

from ..dexpen import (
    PALETTE,
    TOOL_BUCKET,
    TOOL_ERASER,
    TOOL_PENCIL,
    Canvas,
    CanvasPane,
)
from ..exceptions import ConfigurationError
from ..ui import (
    GRAY_BORDER,
    GRAY_SELECTED,
    GRAY_SURFACE,
    WHITE,
    Button,
    Label,
    ListBox,
    Panel,
    TextInput,
)

_PANEL_MARGIN = 8
_LEFT_WIDTH = 220


class SpriteMode:
    """The dexpen feature embedded in the dex-editor window."""

    def __init__(self, ui) -> None:
        self.ui = ui
        self.editor = ui.editor
        self.project = ui.project
        self.canvas = Canvas(16, 16, color=(0, 0, 0, 0))
        self.last_saved: str | None = None
        self._build()

    # -- build ---------------------------------------------------------------

    def _build(self) -> None:
        window = self.editor.window
        font = self.editor.font
        self.panel = Panel(
            background=(24, 24, 30),
            border=GRAY_BORDER,
        )
        self.status_label = Label("", font=font, color=(200, 200, 200))

        self.asset_title = Label("Sprites (images)", font=font, color=(220, 220, 220))
        self.asset_list = ListBox(
            on_select=self._on_pick, font=font, item_height=22
        )
        self.new_title = Label("New sprite  W x H", font=font, color=(200, 200, 200))
        self.new_w = TextInput("16", font=font)
        self.new_h = TextInput("16", font=font)
        self.new_button = Button(
            "Create", font=font, on_click=self._on_new, width=120, height=28
        )
        self.save_button = Button(
            "Save PNG", font=font, on_click=self._on_save, width=120, height=28
        )
        self.tool_button = Button(
            "Eraser", font=font, on_click=self._toggle_eraser, width=99, height=28
        )
        self.fill_button = Button(
            "Fill", font=font, on_click=self._toggle_fill, width=99, height=28
        )
        self.undo_button = Button(
            "Undo", font=font, on_click=self._on_undo, width=99, height=28
        )
        self.redo_button = Button(
            "Redo", font=font, on_click=self._on_redo, width=99, height=28
        )
        self.color_caption = Label("Colors", font=font, color=(220, 220, 220))
        self.color_swatches: list[Button] = []
        for rgb in PALETTE:
            swatch = Button(
                "",
                on_click=lambda rgb=rgb: self._pick_color(rgb),
                background=rgb,
                hover=rgb,
                border=(220, 220, 220),
                text_color=(200, 200, 200),
            )
            self.color_swatches.append(swatch)
        self._color_index = 1
        self.pane = CanvasPane(
            self.canvas,
            on_change=self._on_edited,
        )
        self.pane.color = PALETTE[self._color_index] + (255,)
        self._refresh_swatch_highlight()
        self.panel.add(
            self.asset_title,
            self.asset_list,
            self.new_title,
            self.new_w,
            self.new_h,
            self.new_button,
            self.save_button,
            self.tool_button,
            self.fill_button,
            self.undo_button,
            self.redo_button,
            self.color_caption,
            *self.color_swatches,
            self.pane,
            self.status_label,
        )
        self.ui.root.add(self.panel)
        self.resize(window.width, window.height)

    def _layout(self, width: int, height: int) -> None:
        panel_top = 44
        self.panel.x, self.panel.y = 0, panel_top
        self.panel.width, self.panel.height = width, max(0, height - panel_top)
        self.status_label.x, self.status_label.y = _LEFT_WIDTH + 12, panel_top + 8

        self.asset_title.x, self.asset_title.y = 12, panel_top + 10
        self.asset_list.x, self.asset_list.y = _PANEL_MARGIN, panel_top + 34
        self.asset_list.width = _LEFT_WIDTH - 16
        self.asset_list.height = 150

        self.new_title.x, self.new_title.y = 12, panel_top + 196
        self.new_w.x, self.new_w.y = _PANEL_MARGIN, panel_top + 222
        self.new_w.width, self.new_w.height = 64, 26
        self.new_h.x, self.new_h.y = _PANEL_MARGIN + 72, panel_top + 222
        self.new_h.width, self.new_h.height = 64, 26
        self.new_button.x, self.new_button.y = _PANEL_MARGIN, panel_top + 258
        self.new_button.width = _LEFT_WIDTH - 16
        self.save_button.x, self.save_button.y = _PANEL_MARGIN, panel_top + 294
        self.save_button.width = _LEFT_WIDTH - 16
        self.tool_button.x, self.tool_button.y = _PANEL_MARGIN, panel_top + 330
        self.tool_button.width = 99
        self.fill_button.x, self.fill_button.y = _PANEL_MARGIN + 105, panel_top + 330
        self.fill_button.width = 99
        self.undo_button.x, self.undo_button.y = _PANEL_MARGIN, panel_top + 366
        self.undo_button.width = 99
        self.redo_button.x, self.redo_button.y = _PANEL_MARGIN + 105, panel_top + 366
        self.redo_button.width = 99

        # Color swatch strip (2 rows x 5).
        self.color_caption.x, self.color_caption.y = 12, panel_top + 408
        for index, swatch in enumerate(self.color_swatches):
            row, col = divmod(index, 5)
            swatch.x = _PANEL_MARGIN + col * 40
            swatch.y = panel_top + 434 + row * 32
            swatch.width, swatch.height = 34, 26

        self.pane.x, self.pane.y = _LEFT_WIDTH, panel_top + 16
        self.pane.width = max(0, width - _LEFT_WIDTH - _PANEL_MARGIN)
        self.pane.height = max(0, height - panel_top - 16 - _PANEL_MARGIN)
        self.pane._layout()

    # -- lifecycle -------------------------------------------------------------

    def refresh(self) -> None:
        self.asset_list.clear()
        for entry in self.project.assets:
            if entry.kind == "image":
                self.asset_list.append(entry.filename)

    def active_canvas(self) -> Canvas:
        return self.pane.canvas

    # -- layout ---------------------------------------------------------------

    def resize(self, width: int, height: int) -> None:
        self._layout(width, height)

    # -- actions ---------------------------------------------------------------

    def _on_pick(self, filename) -> None:
        name = str(filename)
        entry = self.project.asset(name)
        if entry is None or entry.kind != "image":
            return
        try:
            canvas = Canvas.load(os.path.join(self.project.assets_dir(), name))
        except OSError as exc:
            self.last_saved = f"Could not open {name!r}: {exc}"
            return
        self.canvas = canvas
        self.pane.canvas = canvas
        self.pane._layout()
        self.last_saved = f"Editing {name}"

    def _on_new(self) -> None:
        try:
            width = max(1, int(self.new_w.value.strip()))
            height = max(1, int(self.new_h.value.strip()))
        except (ValueError, ConfigurationError):
            self.last_saved = "Width/height must be positive integers."
            return
        self.canvas = Canvas(width, height, color=(0, 0, 0, 0))
        self.pane.canvas = self.canvas
        self.pane._layout()
        self._set_tool(TOOL_PENCIL)
        self.pane.color = (255, 255, 255, 255)
        self.last_saved = f"New {width}x{height} sprite"

    def _on_save(self) -> None:
        filename = self._next_sprite_name()
        path = os.path.join(self.project.assets_dir(), filename)
        try:
            self.pane.canvas.save(path)
        except OSError as exc:
            self.last_saved = f"Save failed: {exc}"
            return
        self.project.import_asset(path)
        self.ui._refresh_asset_box()
        self.refresh()
        self.ui.project.dirty = True
        self.last_saved = f"Saved {filename}"

    def _next_sprite_name(self) -> str:
        names = {entry.filename for entry in self.project.assets}
        index = 1
        while f"sprite_{index}.png" in names:
            index += 1
        return f"sprite_{index}.png"

    def _pick_color(self, rgb) -> None:
        self.pane.color = tuple(rgb) + (255,)
        self._color_index = PALETTE.index(rgb)
        self._refresh_swatch_highlight()
        self.last_saved = f"Color RGB{rgb}"

    def _toggle_eraser(self) -> None:
        if self.pane.tool == TOOL_ERASER:
            self._set_tool(TOOL_PENCIL)
        else:
            self._set_tool(TOOL_ERASER)

    def _toggle_fill(self) -> None:
        if self.pane.tool == TOOL_BUCKET:
            self._set_tool(TOOL_PENCIL)
        else:
            self._set_tool(TOOL_BUCKET)

    def _set_tool(self, tool: str) -> None:
        self.pane.tool = tool
        self.tool_button.text = "Pen" if tool == TOOL_ERASER else "Eraser"
        self.tool_button.background = GRAY_SELECTED if tool == TOOL_ERASER else GRAY_SURFACE
        self.fill_button.text = "Back" if tool == TOOL_BUCKET else "Fill"
        self.fill_button.background = GRAY_SELECTED if tool == TOOL_BUCKET else GRAY_SURFACE

    def _on_undo(self) -> None:
        if self.pane.canvas.undo():
            self.last_saved = "Undone"

    def _on_redo(self) -> None:
        if self.pane.canvas.redo():
            self.last_saved = "Redone"

    def _refresh_swatch_highlight(self) -> None:
        for index, swatch in enumerate(self.color_swatches):
            swatch.border = WHITE if index == self._color_index else (220, 220, 220)

    def _on_edited(self) -> None:
        self.last_saved = "Unsaved changes"

    def show(self) -> None:
        self.panel.visible = True
        self.refresh()

    def hide(self) -> None:
        self.panel.visible = False


__all__ = ["SpriteMode"]