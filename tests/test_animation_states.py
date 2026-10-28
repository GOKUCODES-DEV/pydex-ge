"""Tests for the Part 12 animation state machine on Sprite: named animations,
switching, completion callbacks, and stop."""

import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture
from _stub_backend import StubBackend, StubRenderer

from pydex_ge import Animation, ConfigurationError, Image, Renderer, Sprite, SpriteSheet


class AnimationStateTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._path = write_fixture(self._tmp.name, "sheet.bmp", bmp_bytes(64, 32))
        self.backend = StubBackend(image_sizes={self._path: (64, 32)})
        self.renderer = Renderer(StubRenderer())
        self.sheet = SpriteSheet(self._image(), 16, 16)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _image(self) -> Image:
        return Image(self._path, backend=self.backend)

    def _sprite(self) -> Sprite:
        return Sprite(self._image())

    def _animation(self, loop: bool = True) -> Animation:
        frames = [self.sheet.cell(column, 0) for column in range(3)]
        return Animation(frames, fps=10, loop=loop)


class TestAddAnimation(AnimationStateTestBase):
    def test_add_animation_registers(self):
        sprite = self._sprite()
        animation = self._animation()
        sprite.add_animation("idle", animation)
        self.assertEqual(sprite.animation_names, ["idle"])
        self.assertIn("idle", sprite.animations)

    def test_animation_names_empty_by_default(self):
        self.assertEqual(self._sprite().animation_names, [])

    def test_add_animation_validation(self):
        sprite = self._sprite()
        with self.assertRaises(ConfigurationError):
            sprite.add_animation("", self._animation())
        with self.assertRaises(ConfigurationError):
            sprite.add_animation("idle", "not an animation")
        with self.assertRaises(ConfigurationError):
            sprite.add_animation(123, self._animation())


class TestPlayAnimation(AnimationStateTestBase):
    def test_play_sets_current_animation(self):
        sprite = self._sprite()
        idle = self._animation()
        sprite.add_animation("idle", idle)
        sprite.play_animation("idle")
        self.assertEqual(sprite.current_animation, "idle")
        self.assertIs(sprite.animation, idle)

    def test_switch_restarts_new_animation(self):
        sprite = self._sprite()
        idle = self._animation()
        walk = self._animation()
        sprite.add_animation("idle", idle)
        sprite.add_animation("walk", walk)
        sprite.play_animation("idle")
        sprite.update(0.2)
        self.assertEqual(idle.frame_index, 2)
        sprite.play_animation("walk")
        self.assertEqual(walk.frame_index, 0)
        self.assertEqual(sprite.current_animation, "walk")

    def test_unknown_name_raises(self):
        sprite = self._sprite()
        with self.assertRaises(ConfigurationError):
            sprite.play_animation("missing")

    def test_stop_animation_returns_to_static(self):
        sprite = self._sprite()
        sprite.add_animation("idle", self._animation())
        sprite.play_animation("idle")
        sprite.update(0.2)
        sprite.stop_animation()
        self.assertIsNone(sprite.animation)
        self.assertIsNone(sprite.current_animation)
        sprite.draw(self.renderer)
        self.assertEqual(len(self.renderer._renderer.texture_draws), 1)

    def test_stop_animation_then_replay(self):
        sprite = self._sprite()
        idle = self._animation()
        sprite.add_animation("idle", idle)
        sprite.play_animation("idle")
        sprite.stop_animation()
        sprite.play_animation("idle")
        self.assertIs(sprite.animation, idle)
        self.assertEqual(idle.frame_index, 0)

    def test_play_pause_stop_delegate(self):
        sprite = self._sprite()
        idle = self._animation()
        sprite.add_animation("idle", idle)
        sprite.play_animation("idle")
        sprite.pause()
        self.assertFalse(idle.playing)
        sprite.play()
        self.assertTrue(idle.playing)
        sprite.stop()
        self.assertEqual(idle.frame_index, 0)


class TestAnimationCallbacks(AnimationStateTestBase):
    def test_on_finish_fires_once(self):
        sprite = self._sprite()
        animation = self._animation(loop=False)
        sprite.add_animation("attack", animation)
        calls = []
        sprite.play_animation("attack", on_finish=lambda: calls.append("done"))
        sprite.update(0.5)  # 3 frames at 10 fps
        self.assertEqual(calls, ["done"])
        sprite.update(0.1)
        self.assertEqual(calls, ["done"])

    def test_on_finish_can_switch_animation(self):
        sprite = self._sprite()
        attack = self._animation(loop=False)
        idle = self._animation(loop=True)
        sprite.add_animation("attack", attack)
        sprite.add_animation("idle", idle)

        def back_to_idle():
            sprite.play_animation("idle")

        sprite.play_animation("attack", on_finish=back_to_idle)
        sprite.update(0.5)
        self.assertEqual(sprite.current_animation, "idle")

    def test_on_finish_must_be_callable(self):
        sprite = self._sprite()
        sprite.add_animation("attack", self._animation(loop=False))
        with self.assertRaises(ConfigurationError):
            sprite.play_animation("attack", on_finish="done")

    def test_loop_animation_never_finishes(self):
        sprite = self._sprite()
        animation = self._animation(loop=True)
        sprite.add_animation("walk", animation)
        calls = []
        sprite.play_animation("walk", on_finish=lambda: calls.append("done"))
        sprite.update(1.0)
        sprite.update(1.0)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
