"""dexpen: the PYDEX pixel-art editor (a ``pydex_ge.Game`` app).

Usage::

    python -m pydex_ge.dexpen hero.png
    python -m pydex_ge.dexpen --width 64 --height 64 art.png

A normal PYDEX game, so it runs anywhere the engine runs.  New sprite is
a transparent RGBA canvas; Ctrl+S saves (PNG/BMP by extension).
"""

from __future__ import annotations

from ..core import Game
from ..exceptions import ConfigurationError
from ..graphics import Font
from ..ui import (
    GRAY_BORDER,
    GRAY_SELECTED,
    GRAY_SURFACE,
    WHITE,
    Button,
    Label,
    Panel,
    UIRoot,
)
from .canvas import Canvas

TOOLBAR_HEIGHT = 44
STATUS_HEIGHT = 26
MARGIN = 8

TOOL_PENCIL = "pencil"
TOOL_ERASER = "eraser"
TOOL_BUCKET = "bucket"
TOOL_LINE = "line"
TOOL_RECT = "rect"
TOOLS = (TOOL_PENCIL, TOOL_ERASER, TOOL_BUCKET, TOOL_LINE, TOOL_RECT)

PALETTE = [
    (0, 0, 0),
    (255, 255, 255),
    (255, 32, 32),
    (255, 176, 32),
    (255, 240, 64),
    (64, 224, 96),
    (48, 128, 255),
    (160, 64, 255),
    (255, 96, 192),
    (120, 88, 56),
]

STATUS_IDLE = ""
STATUS_SAVED = "Saved."
STATUS_OPENED = "Opened."
STATUS_UNDONE = "Undone."
STATUS_REDONE = "Redone."
STATUS_CLEARED = "Canvas cleared."

HELP_TEXT = (
    "left-drag: draw   +/-: zoom   Ctrl+S: save   "
    "Ctrl+Z: undo   Ctrl+Y: redo   tools: P/E/B/L/R"
)


def _label(tool: str) -> str:
    return {"pencil": "Pencil", "eraser": "Eraser", "bucket": "Bucket",
            "line": "Line", "rect": "Rect"}[tool]


class CanvasPane(Panel):
    """The pixel grid: draws pixels, detects cell hits, edits the canvas."""

    def __init__(
        self,
        canvas: Canvas,
        *,
        on_change=None,
        x: int = 0,
        y: int = TOOLBAR_HEIGHT,
        width: int = 320,
        height: int = 240,
        **kwargs,
    ) -> None:
        kwargs.setdefault("background", (18, 18, 24))
        kwargs.setdefault("border", GRAY_BORDER)
        super().__init__(x=x, y=y, width=width, height=height, **kwargs)
        self.canvas = canvas
        self.on_change = on_change
        self.tool = TOOL_PENCIL
        self.color = PALETTE[1] + (255,)
        self.eraser_color = (0, 0, 0, 0)
        self._stroke_from = None
        self._last_cell = None
        self._stroke_erase = False
        self._preview: list[tuple[int, int]] = []
        self._cell = 1
        self._ox = 0
        self._oy = 0
        self._layout()

    # -- layout / mapping -----------------------------------------------------

    def _layout(self) -> None:
        cw, ch = self.canvas.width, self.canvas.height
        if cw < 1 or ch < 1:
            self._cell = 1
            self._ox = self._oy = 0
            return
        self._cell = max(1, min(self.width // cw, self.height // ch))
        self._ox = (self.width - cw * self._cell) // 2
        self._oy = (self.height - ch * self._cell) // 2

    def zoom(self, factor: float) -> None:
        self._cell = max(1, min(128, round(self._cell * factor)))
        self._ox = (self.width - self.canvas.width * self._cell) // 2
        self._oy = (self.height - self.canvas.height * self._cell) // 2

    def cell_at(self, mx: int, my: int) -> tuple[int, int] | None:
        gx = (mx - self.x - self._ox) // self._cell
        gy = (my - self.y - self._oy) // self._cell
        if 0 <= gx < self.canvas.width and 0 <= gy < self.canvas.height:
            return (int(gx), int(gy))
        return None

    def cell_rect(self, gx: int, gy: int) -> tuple[int, int, int, int]:
        x = self.x + self._ox + gx * self._cell
        y = self.y + self._oy + gy * self._cell
        return (x, y, self._cell, self._cell)

    # -- editing ----------------------------------------------------------------

    def _cells_for(self, tool: str, a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
        if tool == TOOL_LINE:
            return Canvas.line_cells(a[0], a[1], b[0], b[1])
        if tool == TOOL_RECT:
            return Canvas.rect_cells(a[0], a[1], b[0], b[1])
        return [b]

    def _apply(self, cells, *, eraser: bool = False) -> None:
        color = self.eraser_color if (eraser or self.tool == TOOL_ERASER) else self.color
        self.canvas.paint(cells, color)

    def poll(self, input, mx: int, my: int) -> None:
        cell = self.cell_at(mx, my)
        erase_pressed = input.is_button_pressed("right")
        if erase_pressed or input.is_button_pressed("left"):
            if cell is None:
                return
            self.canvas.begin()
            self._stroke_from = cell
            self._last_cell = cell
            self._stroke_erase = erase_pressed
            if self._stroke_erase:
                self._apply([cell], eraser=True)
            elif self.tool == TOOL_BUCKET:
                self.canvas.flood_fill(cell[0], cell[1], self.color)
                self.canvas.commit()
                self._stroke_from = None
                self._notify()
            elif self.tool in (TOOL_PENCIL, TOOL_ERASER):
                self._apply([cell])
            else:
                self._preview = [cell]
            return
        if self._stroke_from is None:
            return
        if self._stroke_erase:
            if not input.is_button_down("right"):
                self._finish_stroke()
                return
        elif not input.is_button_down("left"):
            # Released: apply a staged line/rect, or just finish a stroke.
            if cell is not None and self.tool in (TOOL_LINE, TOOL_RECT):
                self._apply(self._cells_for(self.tool, self._stroke_from, cell))
            self._finish_stroke()
            return
        if cell is None or cell == self._last_cell:
            return
        if self._stroke_erase:
            cells = Canvas.line_cells(self._last_cell[0], self._last_cell[1], cell[0], cell[1])
            self._apply(cells, eraser=True)
            self._last_cell = cell
        elif self.tool in (TOOL_PENCIL, TOOL_ERASER):
            cells = Canvas.line_cells(self._last_cell[0], self._last_cell[1], cell[0], cell[1])
            self._apply(cells)
            self._last_cell = cell
        else:
            self._preview = self._cells_for(self.tool, self._stroke_from, cell)
            self._last_cell = cell

    def _finish_stroke(self) -> None:
        self._preview = []
        self._stroke_from = None
        self._last_cell = None
        self._stroke_erase = False
        self.canvas.commit()
        self._notify()

    def _notify(self) -> None:
        if self.on_change is not None:
            self.on_change()

    # -- drawing ---------------------------------------------------------------

    def draw(self, renderer) -> None:
        super().draw(renderer)
        canvas = self.canvas
        cell = self._cell
        light = (28, 28, 34)
        dark = (22, 22, 27)
        # Checkerboard for transparency.
        for gy in range(canvas.height):
            for gx in range(canvas.width):
                self._draw_cell(
                    renderer, gx, gy, light if (gx + gy) % 2 else dark
                )
        # Pixels on top.
        for gy in range(canvas.height):
            for gx in range(canvas.width):
                r, g, b, a = canvas.get(gx, gy)
                if a:
                    self._draw_cell(renderer, gx, gy, (r, g, b))
        # Staged line/rect preview.
        for gx, gy in self._preview:
            self._draw_cell(renderer, gx, gy, self.color, outline=True)
        # Grid lines.
        if cell >= 6:
            base_x = self.x + self._ox
            base_y = self.y + self._oy
            for gx in range(canvas.width + 1):
                x = base_x + gx * cell
                renderer.draw.line(x, base_y, x, base_y + canvas.height * cell, GRAY_BORDER)
            for gy in range(canvas.height + 1):
                y = base_y + gy * cell
                renderer.draw.line(base_x, y, base_x + canvas.width * cell, y, GRAY_BORDER)
        # Frame.
        x, y, w, h = self.cell_rect(0, 0)
        renderer.draw.rect(x - 1, y - 1, self.canvas.width * cell + 2,
                           self.canvas.height * cell + 2, WHITE, filled=False)

    def _draw_cell(self, renderer, gx: int, gy: int, color, *, outline: bool = False) -> None:
        rect = self.cell_rect(gx, gy)
        renderer.draw.rect(rect[0], rect[1], rect[2], rect[3], color, filled=not outline)


class _DexPenUI:
    def __init__(self, editor: PixelEditor) -> None:
        self.editor = editor
        self.status = STATUS_IDLE
        self._build()

    def _build(self) -> None:
        editor = self.editor
        font = editor.font
        window = editor.window

        self.root = UIRoot()
        self.toolbar = Panel(
            background=(30, 30, 36),
            border=GRAY_BORDER,
            width=window.width,
            height=TOOLBAR_HEIGHT,
        )
        self.status_label = Label("", font=font, color=(200, 200, 200))

        self.tool_buttons: dict[str, Button] = {}
        x = 12
        for tool in TOOLS:
            button = Button(
                _label(tool), font=font, on_click=self._make_tool_callback(tool),
                x=x, y=7, width=74, height=30,
            )
            self.tool_buttons[tool] = button
            self.toolbar.add(button)
            x += 80

        self.undo_button = Button("Undo", font=font, on_click=self._on_undo, x=x, y=7, width=64, height=30)
        self.redo_button = Button("Redo", font=font, on_click=self._on_redo, x=x + 70, y=7, width=64, height=30)
        self.clear_button = Button("Clear", font=font, on_click=self._on_clear, x=x + 140, y=7, width=64, height=30)
        self.save_button = Button("Save", font=font, on_click=self._on_save, x=x + 210, y=7, width=64, height=30)
        self.toolbar.add(self.undo_button, self.redo_button, self.clear_button, self.save_button)

        # Color swatches (a strip below the toolbar, above the canvas).
        swatch_w = 34
        for index, rgb in enumerate(PALETTE):
            swatch = Button(
                "", on_click=self._make_color_callback(rgb),
                background=rgb, hover=rgb, border=(220, 220, 220),
                x=12 + index * (swatch_w + 6),
                y=TOOLBAR_HEIGHT + 8,
                width=swatch_w,
                height=28,
            )
            self.root.add(swatch)

        self.canvas = CanvasPane(
            editor.canvas,
            on_change=self._on_changed,
            x=MARGIN,
            y=TOOLBAR_HEIGHT + 44,
            width=window.width - 2 * MARGIN,
            height=window.height - TOOLBAR_HEIGHT - 44 - MARGIN - STATUS_HEIGHT,
        )
        self.root.add(self.toolbar, self.canvas, self.status_label)
        self._select_tool(TOOL_PENCIL)
        self.resize(window.width, window.height)

    def _make_tool_callback(self, tool: str):
        def switch():
            self._select_tool(tool)
        return switch

    def _make_color_callback(self, rgb):
        def pick():
            self.canvas.color = tuple(rgb) + (255,)
        return pick

    def _select_tool(self, tool: str) -> None:
        self.canvas.tool = tool
        for name, button in self.tool_buttons.items():
            button.background = GRAY_SELECTED if name == tool else GRAY_SURFACE
        self.status = STATUS_IDLE

    def resize(self, width: int, height: int) -> None:
        self.root.width, self.root.height = width, height
        self.toolbar.width = width
        self.canvas.width = width - 2 * MARGIN
        self.canvas.height = max(
            0, height - TOOLBAR_HEIGHT - 44 - MARGIN - STATUS_HEIGHT
        )
        self.canvas._layout()
        self.status_label.x = 12
        self.status_label.y = height - STATUS_HEIGHT + 5

    # -- actions ---------------------------------------------------------------

    def _on_save(self) -> None:
        self.editor.save()
        self.status = STATUS_SAVED

    def _on_undo(self) -> None:
        if self.canvas.canvas.undo():
            self.status = STATUS_UNDONE

    def _on_redo(self) -> None:
        if self.canvas.canvas.redo():
            self.status = STATUS_REDONE

    def _on_clear(self) -> None:
        canvas = self.canvas.canvas
        canvas.begin()
        canvas.clear(self.canvas.eraser_color)
        canvas.commit()
        self.status = STATUS_CLEARED

    def _on_changed(self) -> None:
        self.status = STATUS_IDLE

    def update_status(self) -> None:
        self.status_label.text = self.status or HELP_TEXT


class PixelEditor(Game):
    """The dexpen application."""

    def __init__(
        self,
        canvas: Canvas,
        *,
        path: str | None = None,
        width: int = 1024,
        height: int = 640,
        backend=None,
    ) -> None:
        self.canvas = canvas
        self.path = path or "sprite.png"
        self.font: Font | None = None
        self._ui: _DexPenUI | None = None
        super().__init__(
            title=f"dexpen - {self.path}",
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
        self._ui = _DexPenUI(self)

    def save(self) -> None:
        self.canvas.save(self.path)

    def _shortcuts(self) -> None:
        ui = self._ui
        if ui is None:
            return
        pane = ui.canvas
        if self.input.is_key_pressed("s") and (
            self.input.is_key_down("control") or self.input.is_key_down("ctrl")
        ):
            ui._on_save()
            return
        if self.input.is_key_down("control") or self.input.is_key_down("ctrl"):
            if self.input.is_key_pressed("z"):
                ui._on_undo()
            elif self.input.is_key_pressed("y"):
                ui._on_redo()
            return
        if self.input.is_key_pressed("p"):
            ui._select_tool(TOOL_PENCIL)
        elif self.input.is_key_pressed("e"):
            ui._select_tool(TOOL_ERASER)
        elif self.input.is_key_pressed("b"):
            ui._select_tool(TOOL_BUCKET)
        elif self.input.is_key_pressed("l"):
            ui._select_tool(TOOL_LINE)
        elif self.input.is_key_pressed("r"):
            ui._select_tool(TOOL_RECT)
        elif self.input.is_key_pressed("="):
            pane.zoom(2.0)
        elif self.input.is_key_pressed("-"):
            pane.zoom(0.5)

    def update(self, dt: float) -> None:
        ui = self._ui
        if ui is None:
            return
        width, height = self.window.width, self.window.height
        if (width, height) != (ui.root.width, ui.root.height):
            ui.resize(width, height)
        self._shortcuts()
        ui.root.handle_input(self.input)
        ui.update_status()

    def draw(self) -> None:
        ui = self._ui
        if ui is None:
            return
        ui.root.draw(self.window.renderer)


__all__ = [
    "PixelEditor",
    "Canvas",
    "CanvasPane",
    "TOOL_PENCIL",
    "TOOL_ERASER",
    "TOOL_BUCKET",
    "TOOL_LINE",
    "TOOL_RECT",
    "PALETTE",
]