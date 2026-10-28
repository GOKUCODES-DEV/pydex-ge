"""Tests for the dexpen pixel-art editor (canvas model + app)."""

import os
import tempfile
import unittest

from pydex_ge import Event, EventType, Input
from pydex_ge.dexpen import (
    TOOL_BUCKET,
    TOOL_ERASER,
    TOOL_LINE,
    TOOL_RECT,
    CanvasPane,
    PixelEditor,
)
from pydex_ge.dexpen.canvas import Canvas
from tests._stub_backend import StubBackend

WHITE = (255, 255, 255, 255)
RED = (255, 0, 0, 255)


def _feed(events, pos=(0, 0)):
    backend = StubBackend()
    backend._mouse_position = pos
    backend._pending = list(events)
    inp = Input(backend=backend)
    inp.begin_frame()
    for event in events:
        inp.handle_event(event)
    return inp


def _click(x, y):
    return Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": x, "y": y})


def _up(x, y):
    return Event(EventType.MOUSE_BUTTON_UP, {"button": "left", "x": x, "y": y})


def _rclick(x, y):
    return Event(EventType.MOUSE_BUTTON_DOWN, {"button": "right", "x": x, "y": y})


def _rup(x, y):
    return Event(EventType.MOUSE_BUTTON_UP, {"button": "right", "x": x, "y": y})


def _pane(canvas=None, w=320, h=240):
    canvas = canvas or Canvas(4, 3)
    return CanvasPane(canvas, x=0, y=0, width=w, height=h)


class TestCanvas(unittest.TestCase):
    def test_set_get_and_alpha(self):
        c = Canvas(4, 3, color=(0, 0, 0, 0))
        c.set(1, 1, RED)
        self.assertEqual(c.get(1, 1), RED)
        self.assertEqual(c.get(0, 0), (0, 0, 0, 0))
        c.set(2, 0, (10, 20, 30))
        self.assertEqual(c.get(2, 0), (10, 20, 30, 255))

    def test_out_of_bounds_set_ignored_get_raises(self):
        c = Canvas(4, 3)
        c.set(99, 99, RED)
        self.assertEqual(c.get(0, 0), (0, 0, 0, 255))
        with self.assertRaises(IndexError):
            c.get(-1, 0)

    def test_clear(self):
        c = Canvas(4, 3)
        c.paint([(0, 0), (1, 1), (2, 2)], RED)
        c.clear((0, 0, 0, 0))
        self.assertTrue(all(c.get(x, y) == (0, 0, 0, 0)
                            for x in range(4) for y in range(3)))

    def test_flood_fill_region(self):
        c = Canvas(5, 5, color=(0, 0, 0, 255))
        c.paint([(2, 0), (2, 1), (2, 3)], RED)
        c.flood_fill(4, 4, WHITE)
        filled = sum(1 for y in range(5) for x in range(5)
                     if c.get(x, y) == WHITE)
        self.assertEqual(filled, 22)
        self.assertEqual(c.get(2, 1), RED)
        self.assertEqual(c.get(2, 3), RED)

    def test_flood_fill_same_color_noop(self):
        c = Canvas(4, 3, color=WHITE)
        c.flood_fill(1, 1, WHITE)
        self.assertTrue(c.can_undo is False)

    def test_line_endpoints(self):
        c = Canvas(8, 8)
        c.begin()
        c.line(0, 0, 6, 3, RED)
        c.commit()
        self.assertEqual(c.get(0, 0), RED)
        self.assertEqual(c.get(6, 3), RED)
        self.assertTrue(c.can_undo)

    def test_rect_outline_and_filled(self):
        c = Canvas(6, 5)
        c.begin()
        c.rect(1, 0, 4, 3, RED, filled=False)
        c.commit()
        self.assertEqual(c.get(1, 0), RED)
        self.assertEqual(c.get(4, 3), RED)
        self.assertEqual(c.get(2, 1), (0, 0, 0, 255))
        c.begin()
        c.rect(1, 1, 2, 3, WHITE)
        c.commit()
        self.assertEqual(c.get(1, 2), WHITE)

    def test_undo_redo(self):
        c = Canvas(4, 3)
        c.begin()
        c.set(0, 0, RED)
        c.commit()
        self.assertTrue(c.can_undo)
        c.begin()
        c.set(1, 1, RED)
        c.commit()
        c.undo()
        self.assertEqual(c.get(1, 1), (0, 0, 0, 255))
        c.undo()
        self.assertEqual(c.get(0, 0), (0, 0, 0, 255))
        self.assertFalse(c.can_undo)
        c.redo()
        self.assertEqual(c.get(0, 0), RED)
        self.assertTrue(c.can_undo)

    def test_edit_clears_redo(self):
        c = Canvas(4, 3)
        c.begin()
        c.set(0, 0, RED)
        c.commit()
        c.undo()
        self.assertTrue(c.can_redo)
        c.begin()
        c.set(1, 1, WHITE)
        c.commit()
        self.assertFalse(c.can_redo)

    def test_no_history_for_noop_commit(self):
        c = Canvas(4, 3)
        c.begin()
        c.commit()
        self.assertFalse(c.can_undo)

    def test_save_load_png(self):
        c = Canvas(3, 2, color=(0, 0, 0, 255))
        c.set(0, 0, RED)
        c.set(2, 1, (0, 255, 0, 128))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.png")
            c.save(path)
            loaded = Canvas.load(path)
        self.assertEqual((loaded.width, loaded.height), (3, 2))
        self.assertEqual(loaded.get(0, 0), RED)
        self.assertEqual(loaded.get(2, 1), (0, 255, 0, 128))

    def test_save_load_bmp(self):
        c = Canvas(3, 2, color=(0, 0, 0, 255))
        c.set(1, 0, RED)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.bmp")
            c.save(path)
            loaded = Canvas.load(path)
        self.assertEqual(loaded.get(1, 0), RED)

    def test_dimensions_validation(self):
        with self.assertRaises(Exception):
            Canvas(0, 4)
        with self.assertRaises(Exception):
            Canvas(4, 0)


class TestCanvasPane(unittest.TestCase):
    def test_cell_at_center(self):
        pane = _pane(w=400, h=300)
        pane._cell = 40
        pane._ox = (400 - 4 * 40) // 2
        pane._oy = (300 - 3 * 40) // 2
        self.assertEqual(pane.cell_at(pane._ox + 40, pane._oy + 40), (1, 1))
        self.assertIsNone(pane.cell_at(0, 0))
        self.assertIsNone(pane.cell_at(399, 0))

    def test_cell_rect(self):
        pane = _pane()

        pane._cell = 10
        pane._ox = 5
        pane._oy = 6
        self.assertEqual(pane.cell_rect(0, 0), (5, 6, 10, 10))
        self.assertEqual(pane.cell_rect(2, 1), (25, 16, 10, 10))

    def test_zoom_keeps_cell_in_bounds(self):
        pane = _pane()
        pane.zoom(1000.0)
        self.assertEqual(pane._cell, 128)
        pane.zoom(0.0001)
        self.assertEqual(pane._cell, 1)

    def test_pencil_draws_on_click(self):
        c = Canvas(4, 3)
        pane = _pane(c, w=400, h=300)
        pane._cell = 40
        pane._ox = (400 - 4 * 40) // 2
        pane._oy = (300 - 3 * 40) // 2
        mx = pane._ox + 40 + 20
        my = pane._oy + 40 + 20
        pane.poll(_feed([_click(mx, my)], pos=(mx, my)), mx, my)
        pane.poll(_feed([_up(mx, my)], pos=(mx, my)), mx, my)
        self.assertEqual(c.get(1, 1), (255, 255, 255, 255))
        self.assertTrue(c.can_undo)

    def test_eraser_clears(self):
        c = Canvas(4, 3, color=WHITE)
        pane = _pane(c, w=400, h=300)
        pane._cell = 40
        pane._ox = (400 - 4 * 40) // 2
        pane._oy = (300 - 3 * 40) // 2
        pane.tool = TOOL_ERASER
        mx = pane._ox + 20
        my = pane._oy + 20
        pane.poll(_feed([_click(mx, my)], pos=(mx, my)), mx, my)
        pane.poll(_feed([_up(mx, my)], pos=(mx, my)), mx, my)
        self.assertEqual(c.get(0, 0), (0, 0, 0, 0))

    def test_right_button_erases_with_pencil_tool(self):
        c = Canvas(4, 3, color=WHITE)
        pane = _pane(c, w=400, h=300)
        pane._cell = 40
        pane._ox = (400 - 4 * 40) // 2
        pane._oy = (300 - 3 * 40) // 2
        mx = pane._ox + 20
        my = pane._oy + 20
        pane.poll(_feed([_rclick(mx, my)], pos=(mx, my)), mx, my)
        pane.poll(_feed([_rup(mx, my)], pos=(mx, my)), mx, my)
        self.assertEqual(c.get(0, 0), (0, 0, 0, 0))
        self.assertFalse(pane._preview)
        self.assertIsNone(pane._stroke_from)

    def test_bucket_fills_on_click(self):
        c = Canvas(4, 3, color=(0, 0, 0, 255))
        pane = _pane(c, w=400, h=300)
        pane._cell = 40
        pane._ox = (400 - 4 * 40) // 2
        pane._oy = (300 - 3 * 40) // 2
        pane.tool = TOOL_BUCKET
        mx = pane._ox + 20
        my = pane._oy + 20
        pane.poll(_feed([_click(mx, my)], pos=(mx, my)), mx, my)
        total = sum(1 for y in range(3) for x in range(4)
                    if c.get(x, y) == (255, 255, 255, 255))
        self.assertEqual(total, 12)

    def test_line_released_applies(self):
        c = Canvas(8, 8)
        pane = _pane(c, w=400, h=300)
        pane._cell = 20
        pane._ox = (400 - 8 * 20) // 2
        pane._oy = (300 - 8 * 20) // 2
        pane.tool = TOOL_LINE
        ax = pane._ox + 10
        ay = pane._oy + 10
        bx = pane._ox + 6 * 20 + 10
        by = pane._oy + 10
        pane.poll(_feed([_click(ax, ay)], pos=(ax, ay)), ax, ay)
        self.assertTrue(pane._preview)
        pane.poll(_feed([_up(bx, by)], pos=(bx, by)), bx, by)
        self.assertEqual(c.get(0, 0), (255, 255, 255, 255))
        self.assertEqual(c.get(6, 0), (255, 255, 255, 255))
        self.assertFalse(pane._preview)

    def test_rect_released_applies(self):
        c = Canvas(6, 4)
        pane = _pane(c, w=400, h=300)
        pane._cell = 20
        pane._ox = (400 - 6 * 20) // 2
        pane._oy = (300 - 4 * 20) // 2
        pane.tool = TOOL_RECT
        ax = pane._ox + 2 * 20 + 10
        ay = pane._oy + 10
        bx = pane._ox + 4 * 20 + 10
        by = pane._oy + 2 * 20 + 10
        pane.poll(_feed([_click(ax, ay)], pos=(ax, ay)), ax, ay)
        pane.poll(_feed([_up(bx, by)], pos=(bx, by)), bx, by)
        self.assertEqual(c.get(2, 0), (255, 255, 255, 255))
        self.assertEqual(c.get(4, 2), (255, 255, 255, 255))
        self.assertEqual(c.get(3, 1), (0, 0, 0, 255))


class _LoopBackend(StubBackend):
    """Delivers the queued event batches once per poll."""

    def __init__(self, events=None):
        super().__init__(events=[])
        self._rerun = list(events or [])

    def poll_events(self):
        if self._rerun:
            return [self._rerun.pop(0)]
        return []


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "art.png")

    def _editor(self):
        canvas = Canvas(8, 8, color=(0, 0, 0, 0))
        backend = _LoopBackend()
        editor = PixelEditor(canvas, path=self.path, backend=backend)
        pane = editor._ui.canvas
        rect = pane.cell_rect(2, 3)
        pos = (rect[0] + pane._cell // 2, rect[1] + pane._cell // 2)
        return editor, backend, pos

    def test_draw_and_save_writes_file(self):
        from pydex_ge.backend.base import BackendEvent

        editor, backend, pos = self._editor()
        backend._mouse_position = pos
        backend._rerun = [
            BackendEvent("mouse_button_down", {"button": "left", "x": pos[0], "y": pos[1]}),
            BackendEvent("mouse_button_up", {"button": "left", "x": pos[0], "y": pos[1]}),
            BackendEvent("key_down", {"key": "control"}),
            BackendEvent("key_down", {"key": "s"}),
        ]
        editor.run(max_frames=6)
        self.assertTrue(os.path.exists(self.path))
        loaded = Canvas.load(self.path)
        self.assertEqual(loaded.get(2, 3), (255, 255, 255, 255))
        self.assertEqual(loaded.get(0, 0), (0, 0, 0, 0))

    def test_undo_via_ctrl_z(self):
        from pydex_ge.backend.base import BackendEvent

        editor, backend, pos = self._editor()
        backend._rerun = [
            BackendEvent("mouse_button_down", {"button": "left", "x": pos[0], "y": pos[1]}),
            BackendEvent("mouse_button_up", {"button": "left", "x": pos[0], "y": pos[1]}),
            BackendEvent("key_down", {"key": "control"}),
            BackendEvent("key_down", {"key": "z"}),
        ]
        editor.run(max_frames=6)
        self.assertEqual(editor.canvas.get(2, 3), (0, 0, 0, 0))
        self.assertFalse(editor.canvas.can_undo)


if __name__ == "__main__":
    unittest.main()