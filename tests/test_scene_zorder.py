"""Tests for the Part 12 Scene stable z-order drawing."""

import unittest

from _stub_backend import StubRenderer

from pydex_ge import Renderer, Scene


class _Drawable:
    def __init__(self, name, z=0):
        self.name = name
        self.z = z
        self.draws = []

    def draw(self, renderer):
        self.draws.append(self.name)


class _NoZ:
    def __init__(self, name):
        self.name = name
        self.draws = []

    def draw(self, renderer):
        self.draws.append(self.name)


class TestSceneZOrder(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = Renderer(StubRenderer())

    def test_lower_z_draws_first(self):
        scene = Scene()
        order = []

        class _Tracker(_Drawable):
            def draw(self, renderer):
                order.append(self.name)

        back = _Tracker("back", z=-5)
        mid = _Tracker("mid", z=0)
        front = _Tracker("front", z=10)
        for obj in (front, mid, back):
            scene.add(obj)
        scene.draw(self.renderer)
        self.assertEqual(order, ["back", "mid", "front"])

    def test_same_z_keeps_insertion_order(self):
        scene = Scene()
        first = _Drawable("first", z=0)
        second = _Drawable("second", z=0)
        third = _Drawable("third", z=0)
        scene.add(third)
        scene.add(first)
        scene.add(second)
        scene.draw(self.renderer)
        self.assertEqual(first.draws, ["first"])
        self.assertEqual(second.draws, ["second"])
        self.assertEqual(third.draws, ["third"])

    def test_mixed_z_and_plain_objects(self):
        scene = Scene()
        plain = _NoZ("plain")  # z defaults to 0
        behind = _Drawable("behind", z=-1)
        ahead = _Drawable("ahead", z=1)
        scene.add(plain)
        scene.add(ahead)
        scene.add(behind)
        scene.draw(self.renderer)
        self.assertEqual(behind.draws, ["behind"])
        self.assertEqual(plain.draws, ["plain"])
        self.assertEqual(ahead.draws, ["ahead"])

    def test_update_order_unchanged(self):
        scene = Scene()
        updates = []

        class _Updater(_Drawable):
            def update(self, dt):
                updates.append(self.name)

        a = _Updater("a", z=5)
        b = _Updater("b", z=-5)
        scene.add(a)
        scene.add(b)
        scene.update(1 / 60)
        self.assertEqual(updates, ["a", "b"])


if __name__ == "__main__":
    unittest.main()
