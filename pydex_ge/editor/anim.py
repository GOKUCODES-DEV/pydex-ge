"""Animations mode: the dexanimator feature inside dex-editor.

Turns a sprite into a frame strip: add/copy/remove frames, draw each
frame with the dexpen canvas, preview playback, then export a sprite
sheet PNG into the project's ``assets/`` folder.
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
from . import _pixels

_LEFT_WIDTH = 220
_STRIP_WIDTH = 150
_MARGIN = 8

_HELP_OVERLAY_W = 430
_HELP_OVERLAY_H = 330

_STEP_HINTS = {
    "source": "Pick an image in the list, then click 'Use as base'.",
    "frames": "'+ Frame' copies the current frame; trace each next pose.",
    "draw": "Draw each frame on the big canvas (right-drag erases).",
    "preview": "Set Speed, then press Play; press again to stop.",
    "export": "'Export sheet' writes a PNG into assets/.",
}


def _help_text() -> tuple[str, ...]:
    """Step-by-step lines shown in the animator help overlay."""
    return (
        "1. Pick an image asset as the animation source.",
        "2. Click 'Use as base' to load it as frame 1.",
        "3. Press '+ Frame' to add a copy of the current frame.",
        "4. Draw each frame on the big canvas (right-drag erases).",
        "5. Set Speed (FPS) and press Play to preview.",
        "6. Click 'Export sheet' to save assets/<name>_sheet.png.",
    )


def _help_links() -> tuple[tuple[str, str], ...]:
    """Quick-jump buttons: ``(label, step name)`` pairs."""
    return (
        ("Pick source", "source"),
        ("Frame ops", "frames"),
        ("Draw", "draw"),
        ("Preview", "preview"),
        ("Export", "export"),
    )


class AnimMode:
    """The dexanimator feature embedded in the dex-editor window."""

    def __init__(self, ui) -> None:
        self.ui = ui
        self.editor = ui.editor
        self.project = ui.project
        self.frames: list[Canvas] = []
        self.frame_index = 0
        self.source_name: str | None = None
        self.playing = False
        self.fps_value = 8.0
        self._timer = 0.0
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

        self.asset_title = Label("Sources (images)", font=font, color=(220, 220, 220))
        self.asset_list = ListBox(
            on_select=self._on_set_source, font=font, item_height=22
        )
        self.pick_button = Button(
            "Use as base", font=font, on_click=self._on_set_source, width=120, height=28
        )
        self.fps_label = Label(
            "Speed", font=font, color=(200, 200, 200), align="right", valign="middle"
        )
        self.fps_input = TextInput("8", font=font)
        self.play_button = Button(
            "Play", font=font, on_click=self._on_play, width=120, height=28
        )
        self.expo_label = Label("Frames", font=font, color=(200, 200, 200))
        self.add_button = Button("+ Frame", font=font, on_click=self._on_add_frame,
                                 width=88, height=26)
        self.dup_button = Button("Copy", font=font, on_click=self._on_dup_frame,
                                 width=66, height=26)
        self.del_button = Button("- Frame", font=font, on_click=self._on_del_frame,
                                 width=88, height=26)
        self.export_button = Button(
            "Export sheet", font=font, on_click=self._on_export,
            width=150, height=30,
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
        self.hint_label = Label("", font=font, color=(190, 220, 255))
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
        self.help_button = Button(
            "?", font=font, on_click=self._toggle_help, width=28, height=28
        )

        # Help overlay (hidden; shown over the pane while the user is lost).
        self.help_overlay = Panel(
            background=(34, 36, 44),
            border=GRAY_BORDER,
        )
        self.help_title = Label(
            "How to animate", font=font, color=(230, 230, 230)
        )
        self.help_steps = [
            Label(text, font=font, color=(195, 195, 195))
            for text in _help_text()
        ]
        self.help_buttons = [
            Button(text, font=font, on_click=self._resume_from_state(state),
                   width=120, height=28)
            for text, state in _help_links()
        ]
        self.help_close = Button(
            "Close", font=font, on_click=self._toggle_help, width=120, height=28
        )
        self.help_overlay.add(
            self.help_title,
            *self.help_steps,
            *self.help_buttons,
            self.help_close,
        )
        self.help_overlay.visible = False

        self.pane = CanvasPane(
            Canvas(1, 1, color=(0, 0, 0, 0)),
            on_change=self._on_edited,
        )
        self.pane.color = PALETTE[self._color_index] + (255,)
        self._refresh_swatch_highlight()
        self.frame_list = ListBox(
            on_select=self._on_frame_selected, font=font, item_height=26
        )
        self.panel.add(
            self.asset_title,
            self.asset_list,
            self.pick_button,
            self.fps_label,
            self.fps_input,
            self.play_button,
            self.expo_label,
            self.add_button,
            self.dup_button,
            self.del_button,
            self.export_button,
            self.color_caption,
            *self.color_swatches,
            self.hint_label,
            self.tool_button,
            self.fill_button,
            self.undo_button,
            self.redo_button,
            self.pane,
            self.help_button,
            self.frame_list,
            self.status_label,
            self.help_overlay,
        )
        self.ui.root.add(self.panel)
        self.resize(window.width, window.height)

    def _layout(self, width: int, height: int) -> None:
        panel_top = 44
        self.panel.x, self.panel.y = 0, panel_top
        self.panel.width, self.panel.height = width, max(0, height - panel_top)
        self.status_label.x, self.status_label.y = _LEFT_WIDTH + 12, panel_top + 8

        self.asset_title.x, self.asset_title.y = 12, panel_top + 10
        self.asset_list.x, self.asset_list.y = _MARGIN, panel_top + 34
        self.asset_list.width = _LEFT_WIDTH - 16
        self.asset_list.height = 130
        self.pick_button.x, self.pick_button.y = _MARGIN, panel_top + 172
        self.pick_button.width = _LEFT_WIDTH - 16

        self.fps_input.x, self.fps_input.y = _MARGIN + 44, panel_top + 214
        self.fps_input.width, self.fps_input.height = 60, 26
        self.fps_label.x, self.fps_label.y = _MARGIN, panel_top + 214
        self.fps_label.width = self.fps_input.x - _MARGIN - 8
        self.fps_label.height = 26
        self.play_button.x, self.play_button.y = _MARGIN, panel_top + 248
        self.play_button.width = _LEFT_WIDTH - 16

        self.expo_label.x, self.expo_label.y = 12, panel_top + 288
        self.add_button.x, self.add_button.y = _MARGIN, panel_top + 312
        self.dup_button.x, self.dup_button.y = _MARGIN + 94, panel_top + 312
        self.del_button.x, self.del_button.y = _MARGIN, panel_top + 346
        self.export_button.x, self.export_button.y = _MARGIN, panel_top + 382
        self.export_button.width = _LEFT_WIDTH - 16

        # Color swatch strip (2 rows x 5) plus a step-by-step hint.
        self.color_caption.x, self.color_caption.y = 12, panel_top + 420
        for index, swatch in enumerate(self.color_swatches):
            row, col = divmod(index, 5)
            swatch.x = _MARGIN + col * 40
            swatch.y = panel_top + 446 + row * 32
            swatch.width, swatch.height = 34, 26
        self.hint_label.x, self.hint_label.y = _MARGIN, panel_top + 512
        self.hint_label.width = _LEFT_WIDTH - 2 * _MARGIN
        self.hint_label.height = 42
        self.tool_button.x, self.tool_button.y = _MARGIN, panel_top + 560
        self.tool_button.width = 99
        self.fill_button.x, self.fill_button.y = _MARGIN + 105, panel_top + 560
        self.fill_button.width = 99
        self.undo_button.x, self.undo_button.y = _MARGIN, panel_top + 596
        self.undo_button.width = 99
        self.redo_button.x, self.redo_button.y = _MARGIN + 105, panel_top + 596
        self.redo_button.width = 99

        body_top = panel_top + 16
        body_height = max(32, height - body_top - _MARGIN)
        self.pane.x, self.pane.y = _LEFT_WIDTH, body_top
        self.pane.width = max(32, width - _LEFT_WIDTH - _STRIP_WIDTH - 2 * _MARGIN)
        self.pane.height = body_height
        self.pane._layout()
        self.help_button.x, self.help_button.y = self.pane.x + 10, self.pane.y + 10
        self.help_button.width, self.help_button.height = 28, 28
        self.frame_list.x, self.frame_list.y = width - _STRIP_WIDTH - _MARGIN, body_top
        self.frame_list.width = _STRIP_WIDTH
        self.frame_list.height = body_height

        # Help overlay floats above the drawing pane.
        ow, oh = _HELP_OVERLAY_W, _HELP_OVERLAY_H
        self.help_overlay.x = self.pane.x + (self.pane.width - ow) // 2
        self.help_overlay.y = self.pane.y + 24
        self.help_overlay.width, self.help_overlay.height = ow, oh
        self.help_title.x, self.help_title.y = self.help_overlay.x + 20, self.help_overlay.y + 14
        self.help_title.width, self.help_title.height = ow - 40, 22
        step_y = self.help_overlay.y + 50
        for step in self.help_steps:
            step.x, step.y = self.help_overlay.x + 28, step_y
            step.width, step.height = ow - 56, 22
            step_y += 23
        button_y = self.help_overlay.y + 200
        for index, button in enumerate(self.help_buttons):
            row, col = divmod(index, 3)
            button.width, button.height = 126, 28
            button.x = self.help_overlay.x + 28 + col * 134
            button.y = button_y + row * 36
        self.help_close.x = self.help_overlay.x + ow - 148
        self.help_close.y = self.help_overlay.y + oh - 46
        self.help_close.width, self.help_close.height = 120, 28

    # -- lifecycle -------------------------------------------------------------

    def refresh(self) -> None:
        self.asset_list.clear()
        for entry in self.project.assets:
            if entry.kind == "image":
                self.asset_list.append(entry.filename)

    def _bind(self) -> None:
        if not self.frames:
            self._update_hint()
            return
        self.frame_index = min(max(self.frame_index, 0), len(self.frames) - 1)
        canvas = self.frames[self.frame_index]
        self.pane.canvas = canvas
        self.pane._layout()
        self.frame_list.clear()
        for index in range(len(self.frames)):
            self.frame_list.append(str(index + 1))
        self.frame_list.selected = str(self.frame_index + 1)
        self._update_hint()

    # -- layout ---------------------------------------------------------------

    def resize(self, width: int, height: int) -> None:
        self._layout(width, height)

    # -- actions ---------------------------------------------------------------

    def _on_set_source(self, filename=None) -> None:
        name = str(filename) if filename else self.asset_list.selected
        if not name:
            return
        entry = self.project.asset(name)
        if entry is None or entry.kind != "image":
            return
        try:
            canvas = Canvas.load(os.path.join(self.project.assets_dir(), name))
        except OSError as exc:
            self.last_saved = f"Could not open {name!r}: {exc}"
            return
        self.playing = False
        self.play_button.text = "Play"
        self.frames = [canvas]
        self.frame_index = 0
        self.source_name = name
        self._bind()
        self.last_saved = f"Animating {name}"

    def _on_add_frame(self) -> None:
        if not self.frames:
            self.last_saved = "Pick a source image first."
            return
        source = self.frames[self.frame_index]
        clone = Canvas(source.width, source.height, color=(0, 0, 0, 0))
        clone.from_rows(source.width, source.height, source.to_rows())
        self.frames.append(clone)
        self.frame_index = len(self.frames) - 1
        self._bind()
        self.last_saved = f"{len(self.frames)} frames"

    def _on_dup_frame(self) -> None:
        if not self.frames:
            return
        source = self.frames[self.frame_index]
        clone = Canvas(source.width, source.height, color=(0, 0, 0, 0))
        clone.from_rows(source.width, source.height, source.to_rows())
        self.frames.insert(self.frame_index + 1, clone)
        self.frame_index += 1
        self._bind()
        self.last_saved = f"Copied frame {self.frame_index}"

    def _on_del_frame(self) -> None:
        if len(self.frames) <= 1:
            self.last_saved = "Need at least one frame."
            return
        del self.frames[self.frame_index]
        if self.frame_index >= len(self.frames):
            self.frame_index = len(self.frames) - 1
        self._bind()
        self.last_saved = f"{len(self.frames)} frames"

    def _on_frame_selected(self, item) -> None:
        index = int(str(item)) - 1
        if 0 <= index < len(self.frames):
            self.frame_index = index
            self._bind()

    def _on_play(self) -> None:
        if not self.frames:
            return
        self.playing = not self.playing
        self.play_button.text = f"Stop ({self._read_fps():g} fps)" if self.playing else "Play"
        self._timer = 0.0
        self.last_saved = "Playing" if self.playing else "Stopped"
        self._update_hint()

    # -- help overlay -------------------------------------------------------------

    def _toggle_help(self) -> None:
        self.help_overlay.visible = not self.help_overlay.visible

    def _resume_from_state(self, state: str):
        """Return a click callback that closes help and jumps to ``state``."""

        def on_click(*args) -> None:
            self.help_overlay.visible = False
            self.last_saved = _STEP_HINTS.get(state, "")

        return on_click

    def _on_export(self) -> None:
        if not self.frames:
            self.last_saved = "No frames to export."
            return
        source = self.frames[0]
        width, height = source.width, source.height
        rows: list[bytes] = []
        frames = self.frames
        for y in range(height):
            row = b"".join(frame.to_rows()[y] for frame in frames)
            rows.append(row)
        sheet = _pixels.encode_png(width * len(frames), height, rows)
        stem = os.path.splitext(self.source_name or "frame")[0]
        filename = f"{stem}_sheet.png"
        path = os.path.join(self.project.assets_dir(), filename)
        with open(path, "wb") as handle:
            handle.write(sheet)
        self.project.import_asset(path)
        self.ui._refresh_asset_box()
        self.refresh()
        self.ui.project.dirty = True
        self.last_saved = f"Exported {filename}"
        self._update_hint()

    def _on_edited(self) -> None:
        self.last_saved = "Unsaved changes"

    # -- color swatches ---------------------------------------------------------

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

    def _update_hint(self) -> None:
        if not self.frames:
            self.hint_label.text = "1) Pick a source image, then Use as base."
        elif self.playing:
            self.hint_label.text = (
                f"Playing {self.frame_index + 1}/{len(self.frames)} "
                f"at {self._read_fps():g} fps."
            )
        else:
            self.hint_label.text = (
                f"Frame {self.frame_index + 1}/{len(self.frames)} - "
                "trace the next pose, then Play."
            )

    # -- per-frame ---------------------------------------------------------------

    def _read_fps(self) -> float:
        try:
            value = float(self.fps_input.value.strip())
        except ValueError:
            value = 8.0
        return max(0.1, min(120.0, value))

    def tick(self, dt: float) -> None:
        if not self.playing or len(self.frames) < 2:
            return
        self._timer += dt
        step = 1.0 / self._read_fps()
        while self._timer >= step:
            self._timer -= step
            self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.pane.canvas = self.frames[self.frame_index]
        self._update_hint()

    def show(self) -> None:
        self.panel.visible = True
        self.refresh()
        self._update_hint()

    def hide(self) -> None:
        self.panel.visible = False


__all__ = ["AnimMode"]