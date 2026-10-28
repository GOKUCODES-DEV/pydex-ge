"""Tests for the SceneManager: overlay-stack semantics and transitions."""

import unittest

from _stub_backend import StubRenderer

from pydex_ge import ConfigurationError, Renderer, Scene, SceneManager


class TrackingScene(Scene):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.log = []
        self.updates = 0
        self.draws = 0
        self.events = []

    def on_enter(self):
        self.log.append(f"enter:{self.name}")

    def on_exit(self):
        self.log.append(f"exit:{self.name}")

    def update(self, dt):
        self.updates += 1

    def draw(self, renderer):
        self.draws += 1

    def handle_event(self, event):
        self.events.append(event)


class TestSceneManagerBasics(unittest.TestCase):
    def test_empty_manager(self):
        manager = SceneManager()
        self.assertIsNone(manager.current)
        self.assertEqual(len(manager), 0)
        self.assertEqual(list(manager), [])

    def test_current_is_top_of_stack(self):
        manager = SceneManager()
        s1, s2 = Scene(), Scene()
        manager.push(s1)
        self.assertIs(manager.current, s1)
        manager.push(s2)
        self.assertIs(manager.current, s2)

    def test_len_and_iteration(self):
        manager = SceneManager()
        s1, s2, s3 = Scene(), Scene(), Scene()
        manager.push(s1)
        manager.push(s2)
        manager.push(s3)
        self.assertEqual(len(manager), 3)
        self.assertEqual(list(manager), [s1, s2, s3])

    def test_constructor_accepts_initial_scenes(self):
        s1, s2 = Scene(), Scene()
        manager = SceneManager((s1, s2))
        self.assertIs(manager.current, s2)
        self.assertEqual(len(manager), 2)

    def test_invalid_scene_type_rejected(self):
        manager = SceneManager()
        for bad in (None, 42, "scene", object()):
            with self.assertRaises(ConfigurationError):
                manager.push(bad)
        with self.assertRaises(ConfigurationError):
            manager.replace("nope")

    def test_duplicate_scene_rejected(self):
        manager = SceneManager()
        scene = Scene()
        manager.push(scene)
        with self.assertRaises(ConfigurationError):
            manager.push(scene)
        with self.assertRaises(ConfigurationError):
            manager.replace(scene)


class TestSceneManagerTransitions(unittest.TestCase):
    def test_push_enters_new_scene_only(self):
        manager = SceneManager()
        s1, s2 = TrackingScene("s1"), TrackingScene("s2")
        manager.push(s1)
        self.assertEqual(s1.log, ["enter:s1"])
        manager.push(s2)
        self.assertEqual(s2.log, ["enter:s2"])
        self.assertEqual(s1.log, ["enter:s1"])

    def test_pop_exits_popped_scene_and_resumes_without_enter(self):
        manager = SceneManager()
        s1, s2 = TrackingScene("s1"), TrackingScene("s2")
        manager.push(s1)
        manager.push(s2)
        popped = manager.pop()
        self.assertIs(popped, s2)
        self.assertEqual(s2.log, ["enter:s2", "exit:s2"])
        self.assertIs(manager.current, s1)
        self.assertEqual(s1.log, ["enter:s1"])

    def test_pop_empty_returns_none(self):
        manager = SceneManager()
        self.assertIsNone(manager.pop())

    def test_replace_exits_old_and_enters_new(self):
        manager = SceneManager()
        s1, s2 = TrackingScene("s1"), TrackingScene("s2")
        manager.push(s1)
        manager.replace(s2)
        self.assertEqual(s1.log, ["enter:s1", "exit:s1"])
        self.assertEqual(s2.log, ["enter:s2"])
        self.assertIs(manager.current, s2)

    def test_replace_on_empty_behaves_like_push(self):
        manager = SceneManager()
        s1 = TrackingScene("s1")
        manager.replace(s1)
        self.assertEqual(s1.log, ["enter:s1"])
        self.assertIs(manager.current, s1)

    def test_clear_exits_remaining_top_down(self):
        manager = SceneManager()
        s1, s2, s3 = TrackingScene("s1"), TrackingScene("s2"), TrackingScene("s3")
        manager.push(s1)
        manager.push(s2)
        manager.push(s3)
        manager.clear()
        self.assertIsNone(manager.current)
        self.assertEqual(len(manager), 0)
        self.assertEqual(s3.log, ["enter:s3", "exit:s3"])
        self.assertEqual(s2.log, ["enter:s2", "exit:s2"])
        self.assertEqual(s1.log, ["enter:s1", "exit:s1"])

    def test_clear_empty_is_noop(self):
        manager = SceneManager()
        manager.clear()
        self.assertIsNone(manager.current)

    def test_full_transition_sequence(self):
        manager = SceneManager()
        main, game = TrackingScene("main"), TrackingScene("game")
        manager.push(main)
        manager.push(game)
        manager.pop()
        self.assertIs(manager.current, main)
        self.assertEqual(main.log, ["enter:main"])
        self.assertEqual(game.log, ["enter:game", "exit:game"])

    def test_manager_backref_set_and_cleared(self):
        manager = SceneManager()
        scene = Scene()
        manager.push(scene)
        self.assertIs(scene.manager, manager)
        manager.pop()
        self.assertIsNone(scene.manager)

    def test_replaced_scene_backref_cleared(self):
        manager = SceneManager()
        old, new = Scene(), Scene()
        manager.push(old)
        manager.replace(new)
        self.assertIsNone(old.manager)
        self.assertIs(new.manager, manager)


class TestSceneManagerForwarding(unittest.TestCase):
    def setUp(self):
        self.renderer = Renderer(StubRenderer())

    def test_update_only_reaches_current(self):
        manager = SceneManager()
        s1, s2 = TrackingScene("s1"), TrackingScene("s2")
        manager.push(s1)
        manager.push(s2)
        manager.update(0.016)
        self.assertEqual(s2.updates, 1)
        self.assertEqual(s1.updates, 0)

    def test_draw_only_reaches_current(self):
        manager = SceneManager()
        s1, s2 = TrackingScene("s1"), TrackingScene("s2")
        manager.push(s1)
        manager.push(s2)
        manager.draw(self.renderer)
        self.assertEqual(s2.draws, 1)
        self.assertEqual(s1.draws, 0)

    def test_handle_event_only_reaches_current(self):
        manager = SceneManager()
        s1, s2 = TrackingScene("s1"), TrackingScene("s2")
        manager.push(s1)
        manager.push(s2)
        event = object()
        manager.handle_event(event)
        self.assertEqual(s2.events, [event])
        self.assertEqual(s1.events, [])

    def test_covered_scene_resumes_receiving_after_pop(self):
        manager = SceneManager()
        s1, s2 = TrackingScene("s1"), TrackingScene("s2")
        manager.push(s1)
        manager.push(s2)
        manager.pop()
        manager.update(0.016)
        manager.draw(self.renderer)
        self.assertEqual(s1.updates, 1)
        self.assertEqual(s1.draws, 1)
        self.assertEqual(s2.updates, 0)

    def test_empty_manager_forwarding_is_noop(self):
        manager = SceneManager()
        manager.update(0.016)
        manager.draw(self.renderer)
        manager.handle_event(object())


if __name__ == "__main__":
    unittest.main()
