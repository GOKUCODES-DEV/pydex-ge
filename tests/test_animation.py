"""Tests for Animation, Sprite + Animation integration, and SpriteSheet helpers."""

import tempfile
import unittest

from _image_fixtures import bmp_bytes, write_fixture
from _stub_backend import StubBackend, StubRenderer

from pydex_ge import (
    Animation,
    ConfigurationError,
    Image,
    Renderer,
    Sprite,
    SpriteSheet,
    TextureRegion,
)


class AnimationTestBase(unittest.TestCase):
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

    def _cells(self, count: int = 3) -> list[Sprite]:
        return [self.sheet.cell(column, 0) for column in range(count)]

    def _regions(self, count: int = 3) -> list[TextureRegion]:
        return [self.sheet.region(column * 16, 0, 16, 16) for column in range(count)]


class TestAnimationConstruction(AnimationTestBase):
    def test_from_sprite_sheet_cells(self):
        animation = Animation(self._cells(), fps=10)
        self.assertEqual(animation.frame_count, 3)
        self.assertEqual(animation.frame_index, 0)
        self.assertFalse(animation.playing)
        self.assertFalse(animation.finished)
        self.assertTrue(animation.loop)

    def test_frames_keyword_and_loop(self):
        animation = Animation(frames=self._cells(), fps=12, loop=False)
        self.assertEqual(animation.frame_count, 3)
        self.assertFalse(animation.loop)

    def test_from_texture_regions(self):
        animation = Animation(self._regions(), fps=10)
        self.assertEqual(animation.frame_count, 3)
        self.assertIsInstance(animation.current_frame, Sprite)

    def test_explicit_frame_durations(self):
        animation = Animation(
            [(self._sprite(), 0.1), (self._sprite(), 0.2), (self._sprite(), 0.1)],
            loop=True,
        )
        self.assertEqual(animation.frame_count, 3)
        self.assertFalse(animation.playing)

    def test_fps_with_override_duration(self):
        animation = Animation(
            [self._sprite(), (self._sprite(), 0.5), self._sprite()], fps=10
        )
        self.assertEqual(animation.frame_count, 3)

    def test_speed_accepted(self):
        animation = Animation(self._cells(), fps=10, speed=2.0)
        self.assertEqual(animation.speed, 2.0)

    def test_empty_frames_rejected(self):
        for frames in ([], (), iter(())):
            with self.assertRaises(ConfigurationError):
                Animation(frames, fps=10)

    def test_invalid_fps_rejected(self):
        for bad in (0, -1, True, "x"):
            with self.assertRaises(ConfigurationError):
                Animation(self._cells(), fps=bad)

    def test_invalid_speed_rejected(self):
        for bad in (0, -1, True, "x"):
            with self.assertRaises(ConfigurationError):
                Animation(self._cells(), fps=10, speed=bad)

    def test_invalid_duration_rejected(self):
        for bad in (0, -1, True, "x"):
            with self.assertRaises(ConfigurationError):
                Animation([(self._sprite(), bad), (self._sprite(), 0.1)])

    def test_missing_duration_rejected(self):
        with self.assertRaises(ConfigurationError):
            Animation(self._cells())

    def test_filename_frame_rejected(self):
        with self.assertRaises(ConfigurationError):
            Animation(["player.png"], fps=10)

    def test_invalid_frame_source_rejected(self):
        for bad in (123, 4.5, None, object()):
            with self.assertRaises(ConfigurationError):
                Animation([bad], fps=10)

    def test_loop_must_be_bool(self):
        with self.assertRaises(ConfigurationError):
            Animation(self._cells(), fps=10, loop=1)


class TestAnimationTiming(AnimationTestBase):
    def test_frame_progression_at_boundary(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.update(0.1)
        self.assertEqual(animation.frame_index, 1)

    def test_partial_advance(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.update(0.05)
        self.assertEqual(animation.frame_index, 0)
        self.assertAlmostEqual(animation.time, 0.05, places=6)

    def test_large_dt_advances_multiple_frames(self):
        animation = Animation(self._cells(4), fps=10)
        animation.play()
        animation.update(0.25)
        self.assertEqual(animation.frame_index, 2)
        self.assertAlmostEqual(animation.time, 0.05, places=6)

    def test_speed_multiplier(self):
        animation = Animation(self._cells(), fps=10, speed=2.0)
        animation.play()
        animation.update(0.05)
        self.assertEqual(animation.frame_index, 1)

    def test_speed_settable(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.speed = 0.5
        animation.update(0.2)
        self.assertEqual(animation.frame_index, 1)

    def test_negative_dt_rejected(self):
        animation = Animation(self._cells(), fps=10)
        with self.assertRaises(ConfigurationError):
            animation.update(-1)

    def test_non_numeric_dt_rejected(self):
        animation = Animation(self._cells(), fps=10)
        with self.assertRaises(ConfigurationError):
            animation.update(True)

    def test_looping_wraps_to_first_frame(self):
        animation = Animation(self._cells(), fps=2, loop=True)
        animation.play()
        animation.update(1.5)
        self.assertEqual(animation.frame_index, 0)
        self.assertTrue(animation.playing)
        self.assertFalse(animation.finished)

    def test_looping_keeps_wrapping(self):
        animation = Animation(self._cells(), fps=2, loop=True)
        animation.play()
        animation.update(2.0)
        self.assertEqual(animation.frame_index, 1)

    def test_non_looping_finishes_on_last_frame(self):
        animation = Animation(self._cells(), fps=2, loop=False)
        animation.play()
        animation.update(0.5)
        animation.update(0.5)
        self.assertEqual(animation.frame_index, 2)
        animation.update(0.5)
        self.assertEqual(animation.frame_index, 2)
        self.assertTrue(animation.finished)
        self.assertFalse(animation.playing)

    def test_finished_stays_on_last_frame(self):
        animation = Animation(self._cells(), fps=2, loop=False)
        animation.play()
        animation.update(2.0)
        animation.update(1.0)
        self.assertEqual(animation.frame_index, 2)
        self.assertTrue(animation.finished)

    def test_not_playing_does_not_advance(self):
        animation = Animation(self._cells(), fps=10)
        animation.update(0.5)
        self.assertEqual(animation.frame_index, 0)

    def test_paused_does_not_advance(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.update(0.1)
        animation.pause()
        animation.update(0.5)
        self.assertEqual(animation.frame_index, 1)


class TestAnimationControls(AnimationTestBase):
    def test_play_starts(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        self.assertTrue(animation.playing)

    def test_play_restarts_when_finished(self):
        animation = Animation(self._cells(), fps=2, loop=False)
        animation.play()
        animation.update(1.5)
        self.assertTrue(animation.finished)
        animation.play()
        self.assertEqual(animation.frame_index, 0)
        self.assertFalse(animation.finished)
        self.assertTrue(animation.playing)

    def test_stop_rewinds(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.update(0.2)
        animation.stop()
        self.assertEqual(animation.frame_index, 0)
        self.assertFalse(animation.playing)
        self.assertFalse(animation.finished)

    def test_reset_keeps_playing_state(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.update(0.2)
        animation.reset()
        self.assertEqual(animation.frame_index, 0)
        self.assertTrue(animation.playing)

    def test_reset_when_paused_keeps_paused(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.update(0.2)
        animation.pause()
        animation.reset()
        self.assertEqual(animation.frame_index, 0)
        self.assertFalse(animation.playing)

    def test_restart_rewinds_and_plays(self):
        animation = Animation(self._cells(), fps=10)
        animation.update(0.2)
        animation.restart()
        self.assertEqual(animation.frame_index, 0)
        self.assertTrue(animation.playing)

    def test_resume_continues(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.update(0.1)
        animation.pause()
        animation.resume()
        self.assertEqual(animation.frame_index, 1)
        self.assertTrue(animation.playing)

    def test_resume_restarts_when_finished(self):
        animation = Animation(self._cells(), fps=2, loop=False)
        animation.play()
        animation.update(1.5)
        animation.resume()
        self.assertEqual(animation.frame_index, 0)
        self.assertTrue(animation.playing)

    def test_loop_property_settable(self):
        animation = Animation(self._cells(), fps=10)
        animation.loop = False
        self.assertFalse(animation.loop)
        animation.loop = True
        self.assertTrue(animation.loop)

    def test_current_frame_is_sprite(self):
        animation = Animation(self._cells(), fps=10)
        self.assertIsInstance(animation.current_frame, Sprite)

    def test_frame_index_alias(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.update(0.1)
        self.assertEqual(animation.current_index, animation.frame_index)
        self.assertEqual(animation.current_index, 1)

    def test_len(self):
        animation = Animation(self._cells(), fps=10)
        self.assertEqual(len(animation), 3)

    def test_time_starts_zero(self):
        animation = Animation(self._cells(), fps=10)
        self.assertEqual(animation.time, 0.0)


class TestAnimationDrawing(AnimationTestBase):
    def test_draw_sends_region_and_position(self):
        animation = Animation(self._cells(), fps=10)
        animation.draw(self.renderer, (10, 20))
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(src, (0, 0, 16, 16))
        self.assertEqual(dst, (10, 20, 16, 16))
        self.assertEqual(alpha, 255)

    def test_draw_uses_current_frame(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.update(0.1)
        animation.draw(self.renderer, (0, 0))
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(src, (16, 0, 16, 16))

    def test_draw_scale_and_alpha(self):
        animation = Animation(self._cells(), fps=10)
        animation.draw(self.renderer, (0, 0), scale=2.0, alpha=128)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (0, 0, 32, 32))
        self.assertEqual(alpha, 128)

    def test_draw_position_as_vector(self):
        from pydex_ge import Vector2

        animation = Animation(self._cells(), fps=10)
        animation.draw(self.renderer, Vector2(30, 40))
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(dst, (30, 40, 16, 16))

    def test_draw_bad_position_rejected(self):
        animation = Animation(self._cells(), fps=10)
        for bad in (123, (1, 2, 3), "here"):
            with self.assertRaises(ConfigurationError):
                animation.draw(self.renderer, bad)

    def test_paused_animation_still_draws_current_frame(self):
        animation = Animation(self._cells(), fps=10)
        animation.play()
        animation.update(0.1)
        animation.pause()
        animation.draw(self.renderer, (0, 0))
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(src, (16, 0, 16, 16))


class TestSpriteAnimation(AnimationTestBase):
    def test_static_sprite_draws_own_image(self):
        sprite = Sprite(self._image())
        sprite.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertIsNone(src)
        self.assertEqual(dst, (0, 0, 64, 32))

    def test_attached_animation_draws_frame(self):
        sprite = Sprite(self._image())
        sprite.animation = Animation(self._cells(), fps=10)
        sprite.play()
        sprite.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(src, (0, 0, 16, 16))

    def test_sprite_update_advances_animation(self):
        sprite = Sprite(self._image())
        animation = Animation(self._cells(), fps=10)
        sprite.animation = animation
        sprite.play()
        sprite.update(0.1)
        self.assertEqual(animation.frame_index, 1)

    def test_sprite_play_pause_stop_delegate(self):
        sprite = Sprite(self._image())
        animation = Animation(self._cells(), fps=10)
        sprite.animation = animation
        sprite.play()
        self.assertTrue(animation.playing)
        sprite.pause()
        self.assertFalse(animation.playing)
        sprite.play()
        sprite.update(0.2)
        sprite.stop()
        self.assertEqual(animation.frame_index, 0)

    def test_sprite_controls_noop_without_animation(self):
        sprite = Sprite(self._image())
        sprite.play()
        sprite.pause()
        sprite.stop()
        sprite.update(0.5)
        sprite.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertIsNone(src)

    def test_animation_setter_rejects_non_animation(self):
        sprite = Sprite(self._image())
        with self.assertRaises(ConfigurationError):
            sprite.animation = "walk"

    def test_animation_none_restores_static(self):
        sprite = Sprite(self._image())
        sprite.animation = Animation(self._cells(), fps=10)
        sprite.animation = None
        sprite.draw(self.renderer)
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertIsNone(src)

    def test_animations_dict_and_play_animation(self):
        sprite = Sprite(self._image())
        idle = Animation(self._cells(), fps=10)
        walk = Animation(self._cells(), fps=10)
        sprite.animations["idle"] = idle
        sprite.animations["walk"] = walk
        sprite.play_animation("walk")
        self.assertIs(sprite.animation, walk)
        self.assertTrue(walk.playing)

    def test_play_animation_switching_restarts(self):
        sprite = Sprite(self._image())
        idle = Animation(self._cells(), fps=10)
        walk = Animation(self._cells(), fps=10)
        sprite.animations["idle"] = idle
        sprite.animations["walk"] = walk
        sprite.play_animation("idle")
        sprite.update(0.2)
        self.assertEqual(idle.frame_index, 2)
        sprite.play_animation("walk")
        self.assertEqual(walk.frame_index, 0)
        self.assertTrue(walk.playing)

    def test_play_animation_same_name_is_noop(self):
        sprite = Sprite(self._image())
        idle = Animation(self._cells(), fps=10)
        sprite.animations["idle"] = idle
        sprite.play_animation("idle")
        sprite.update(0.2)
        frame = idle.frame_index
        sprite.play_animation("idle")
        self.assertEqual(idle.frame_index, frame)

    def test_play_animation_unknown_raises(self):
        sprite = Sprite(self._image())
        with self.assertRaises(ConfigurationError):
            sprite.play_animation("idle")


class TestSpriteSheetAnimation(AnimationTestBase):
    def test_animation_from_cells(self):
        animation = self.sheet.animation(frames=[(0, 0), (1, 0), (2, 0)], fps=10)
        self.assertIsInstance(animation, Animation)
        self.assertEqual(animation.frame_count, 3)

    def test_animation_with_durations(self):
        animation = self.sheet.animation(frames=[(0, 0, 0.1), (1, 0, 0.2)])
        self.assertEqual(animation.frame_count, 2)

    def test_animation_run_sequential(self):
        animation = self.sheet.animation_run(0, 0, 4, fps=10)
        self.assertEqual(animation.frame_count, 4)
        animation.play()
        animation.update(0.1)
        animation.draw(self.renderer, (0, 0))
        texture, src, dst, alpha = self.renderer._renderer.texture_draws[0]
        self.assertEqual(src, (16, 0, 16, 16))

    def test_animation_run_invalid_count(self):
        for bad in (0, -1, True):
            with self.assertRaises(ConfigurationError):
                self.sheet.animation_run(0, 0, bad)

    def test_animation_invalid_frame_rejected(self):
        with self.assertRaises(ConfigurationError):
            self.sheet.animation(frames=[123])

    def test_animation_out_of_bounds_rejected(self):
        with self.assertRaises(ConfigurationError):
            self.sheet.animation(frames=[(5, 5)], fps=10)

    def test_existing_sheet_apis_unchanged(self):
        self.assertIsInstance(self.sheet.cell(0, 0), Sprite)
        self.assertIsInstance(self.sheet.region(0, 0, 8, 8), TextureRegion)
        self.assertIsInstance(self.sheet.sprite(0, 0, 8, 8), Sprite)


if __name__ == "__main__":
    unittest.main()
