"""Tests for the PYDEX input system, using engine events fed by a stub backend."""

import unittest

from _stub_backend import StubBackend

from pydex_ge import Event, EventType, Input, Keys
from pydex_ge.backend.null import NullBackend


class TestKeyboard(unittest.TestCase):
    def _feed(self, *events):
        backend = StubBackend()
        inp = Input(backend=backend)
        inp.begin_frame()
        for event in events:
            inp.handle_event(event)
        return inp

    def test_pressed(self):
        inp = self._feed(Event(EventType.KEY_DOWN, {"key": "e"}))
        self.assertTrue(inp.is_key_pressed("e"))
        self.assertTrue(inp.is_key_pressed("E"))  # case-insensitive
        self.assertTrue(inp.is_key_pressed(Keys.E))

    def test_released(self):
        backend = StubBackend()
        inp = Input(backend=backend)
        inp.begin_frame()
        inp.handle_event(Event(EventType.KEY_DOWN, {"key": "e"}))
        inp.begin_frame()  # new frame: down state carries, pressed clears
        inp.handle_event(Event(EventType.KEY_UP, {"key": "e"}))
        self.assertTrue(inp.is_key_released("e"))
        self.assertFalse(inp.is_key_pressed("e"))
        self.assertFalse(inp.is_key_down("e"))

    def test_held(self):
        inp = self._feed(Event(EventType.KEY_DOWN, {"key": "space"}))
        self.assertTrue(inp.is_key_down("space"))
        self.assertTrue(inp.is_key_held("space"))

    def test_not_held_after_release(self):
        inp = self._feed(
            Event(EventType.KEY_DOWN, {"key": "space"}),
            Event(EventType.KEY_UP, {"key": "space"}),
        )
        self.assertFalse(inp.is_key_down("space"))

    def test_multiple_keys(self):
        inp = self._feed(
            Event(EventType.KEY_DOWN, {"key": "a"}),
            Event(EventType.KEY_DOWN, {"key": "b"}),
        )
        self.assertTrue(inp.is_key_down("a"))
        self.assertTrue(inp.is_key_down("b"))
        self.assertFalse(inp.is_key_down("c"))

    def test_unknown_key_never_crashes(self):
        inp = self._feed(Event(EventType.KEY_DOWN, {"key": None}))
        self.assertFalse(inp.is_key_pressed(None))
        self.assertFalse(inp.is_key_down(123))
        self.assertFalse(inp.is_key_down("no_such_key"))

    def test_pressed_clears_next_frame(self):
        backend = StubBackend()
        inp = Input(backend=backend)
        inp.begin_frame()
        inp.handle_event(Event(EventType.KEY_DOWN, {"key": "e"}))
        self.assertTrue(inp.is_key_pressed("e"))
        inp.begin_frame()  # next frame
        self.assertFalse(inp.is_key_pressed("e"))
        self.assertTrue(inp.is_key_down("e"))  # still held

    def test_repeat_press_is_not_a_new_press(self):
        inp = self._feed(
            Event(EventType.KEY_DOWN, {"key": "e", "repeat": False}),
            Event(EventType.KEY_DOWN, {"key": "e", "repeat": True}),
        )
        self.assertTrue(inp.is_key_pressed("e"))
        self.assertTrue(inp.is_key_down("e"))

    def test_repeat_only_is_not_pressed(self):
        inp = self._feed(Event(EventType.KEY_DOWN, {"key": "e", "repeat": True}))
        self.assertFalse(inp.is_key_pressed("e"))
        self.assertTrue(inp.is_key_down("e"))


class TestMouse(unittest.TestCase):
    def test_position(self):
        backend = StubBackend()
        backend._mouse_position = (30, 40)
        inp = Input(backend=backend)
        inp.begin_frame()
        self.assertEqual(inp.mouse_position, (30, 40))
        self.assertEqual(inp.mouse_x, 30)
        self.assertEqual(inp.mouse_y, 40)

    def test_motion_updates_position_and_delta(self):
        backend = StubBackend()
        inp = Input(backend=backend)
        inp.begin_frame()
        inp.handle_event(Event(EventType.MOUSE_MOTION, {"x": 50, "y": 60, "dx": 4, "dy": -2}))
        self.assertEqual(inp.mouse_position, (50, 60))
        self.assertEqual(inp.mouse_delta, (4, -2))

    def test_delta_clears_next_frame(self):
        backend = StubBackend()
        inp = Input(backend=backend)
        inp.begin_frame()
        inp.handle_event(Event(EventType.MOUSE_MOTION, {"x": 5, "y": 5, "dx": 2, "dy": 3}))
        self.assertEqual(inp.mouse_delta, (2, 3))
        inp.begin_frame()
        self.assertEqual(inp.mouse_delta, (0, 0))

    def test_button_pressed_released_down(self):
        backend = StubBackend()
        inp = Input(backend=backend)
        inp.begin_frame()
        inp.handle_event(Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": 10, "y": 12}))
        self.assertTrue(inp.is_button_pressed("left"))
        self.assertTrue(inp.is_button_down("left"))
        self.assertFalse(inp.is_button_down("right"))
        inp.handle_event(Event(EventType.MOUSE_BUTTON_UP, {"button": "left"}))
        self.assertTrue(inp.is_button_released("left"))
        self.assertFalse(inp.is_button_down("left"))

    def test_unknown_button_never_crashes(self):
        backend = StubBackend()
        inp = Input(backend=backend)
        inp.begin_frame()
        inp.handle_event(Event(EventType.MOUSE_BUTTON_DOWN, {"button": "side"}))
        self.assertTrue(inp.is_button_down("side"))  # any name is accepted
        self.assertFalse(inp.is_button_down("left"))
        self.assertFalse(inp.is_button_pressed(None))
        self.assertFalse(inp.is_button_down(123))


class TestHeadlessInput(unittest.TestCase):
    def test_null_backend_produces_no_input(self):
        inp = Input(backend=NullBackend())
        inp.begin_frame()
        self.assertFalse(inp.is_key_pressed("e"))
        self.assertFalse(inp.is_key_down("e"))
        self.assertFalse(inp.is_key_released("e"))
        self.assertFalse(inp.is_button_down("left"))
        self.assertEqual(inp.mouse_position, (0, 0))
        self.assertEqual(inp.mouse_delta, (0, 0))


if __name__ == "__main__":
    unittest.main()
