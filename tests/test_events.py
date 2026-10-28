"""Tests for the event system, using an in-memory stub backend."""

import unittest

from _stub_backend import StubBackend

from pydex_ge import Event, EventManager, EventType
from pydex_ge.backend.base import BackendEvent


class TestEventManager(unittest.TestCase):
    def test_empty_manager_returns_none(self):
        manager = EventManager(backend=StubBackend())
        self.assertIsNone(manager.get())
        self.assertFalse(manager.has_quit())

    def test_quit_event_is_translated(self):
        manager = EventManager(
            backend=StubBackend([BackendEvent("quit", {"reason": "user"})])
        )
        manager.poll()
        self.assertTrue(manager.has_quit())
        event = manager.get()
        self.assertIsInstance(event, Event)
        self.assertIs(event.type, EventType.QUIT)
        self.assertEqual(event.data["reason"], "user")

    def test_unknown_backend_events_are_ignored(self):
        manager = EventManager(
            backend=StubBackend([BackendEvent("unknown_kind"), BackendEvent("mouse_thing")])
        )
        manager.poll()
        self.assertIsNone(manager.get())
        self.assertFalse(manager.has_quit())

    def test_window_close_event_is_translated(self):
        manager = EventManager(backend=StubBackend([BackendEvent("window_close")]))
        manager.poll()
        self.assertTrue(manager.has(EventType.WINDOW_CLOSE))
        self.assertFalse(manager.has_quit())
        self.assertIs(manager.get().type, EventType.WINDOW_CLOSE)

    def test_window_resized_event_carries_new_size(self):
        manager = EventManager(
            backend=StubBackend(
                [BackendEvent("window_resized", {"width": 1024, "height": 768})]
            )
        )
        manager.poll()
        self.assertTrue(manager.has(EventType.WINDOW_RESIZED))
        event = manager.get()
        self.assertIs(event.type, EventType.WINDOW_RESIZED)
        self.assertEqual(event.data["width"], 1024)
        self.assertEqual(event.data["height"], 768)

    def test_has_checks_specific_type(self):
        manager = EventManager(
            backend=StubBackend(
                [BackendEvent("quit"), BackendEvent("window_resized", {"width": 1, "height": 1})]
            )
        )
        manager.poll()
        self.assertTrue(manager.has(EventType.QUIT))
        self.assertTrue(manager.has(EventType.WINDOW_RESIZED))
        self.assertFalse(manager.has(EventType.WINDOW_CLOSE))

    def test_iteration_drains_queue(self):
        events = [BackendEvent("quit") for _ in range(3)]
        manager = EventManager(backend=StubBackend(events))
        manager.poll()
        seen = list(manager)
        self.assertEqual(len(seen), 3)
        self.assertIsNone(manager.get())

    def test_clear_drops_queue(self):
        manager = EventManager(backend=StubBackend([BackendEvent("quit")]))
        manager.poll()
        manager.clear()
        self.assertFalse(manager.has_quit())
        self.assertIsNone(manager.get())

    def test_poll_keeps_unconsumed_events(self):
        manager = EventManager(backend=StubBackend([BackendEvent("quit")]))
        manager.poll()
        manager.poll()
        self.assertTrue(manager.has_quit())

    def test_key_down_event_is_translated(self):
        manager = EventManager(
            backend=StubBackend([BackendEvent("key_down", {"key": "e", "repeat": False})])
        )
        manager.poll()
        event = manager.get()
        self.assertIs(event.type, EventType.KEY_DOWN)
        self.assertEqual(event.data["key"], "e")

    def test_key_up_event_is_translated(self):
        manager = EventManager(
            backend=StubBackend([BackendEvent("key_up", {"key": "escape"})])
        )
        manager.poll()
        self.assertIs(manager.get().type, EventType.KEY_UP)

    def test_mouse_motion_event_is_translated(self):
        manager = EventManager(
            backend=StubBackend([BackendEvent("mouse_motion", {"x": 5, "y": 6, "dx": 1, "dy": 2})])
        )
        manager.poll()
        event = manager.get()
        self.assertIs(event.type, EventType.MOUSE_MOTION)
        self.assertEqual(event.data["x"], 5)

    def test_mouse_button_events_are_translated(self):
        manager = EventManager(
            backend=StubBackend(
                [
                    BackendEvent("mouse_button_down", {"button": "left"}),
                    BackendEvent("mouse_button_up", {"button": "right"}),
                ]
            )
        )
        manager.poll()
        events = list(manager)
        self.assertIs(events[0].type, EventType.MOUSE_BUTTON_DOWN)
        self.assertIs(events[1].type, EventType.MOUSE_BUTTON_UP)


if __name__ == "__main__":
    unittest.main()