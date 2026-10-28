"""Tests for the dexpen (Sprites) and dexanimator (Animate) features of dex-editor."""

import os
import unittest

from _image_fixtures import png_bytes, write_fixture
from test_editor import _click, _feed, _TempProject

from pydex_ge import Event, EventType
from pydex_ge.dexpen import PALETTE, TOOL_BUCKET, TOOL_ERASER
from pydex_ge.dexpen.canvas import Canvas
from pydex_ge.editor import (
    MODE_ANIM,
    MODE_LEVEL,
    MODE_SPRITE,
    PROPS_WIDTH,
    STATUS_HEIGHT,
    Editor,
)
from pydex_ge.ui import (
    GRAY_SELECTED,
    GRAY_SURFACE,
)
from pydex_ge.ui import (
    WHITE as UI_WHITE,
)
from tests._stub_backend import StubBackend

RED = (255, 0, 0, 255)
WHITE = (255, 255, 255, 255)


class _ModeCase(unittest.TestCase):
    def setUp(self):
        self.temp = _TempProject("Mod")
        self.addCleanup(self.temp.cleanup)
        self.editor = Editor(self.temp.project, backend=StubBackend())
        self.ui = self.editor._ui

    def _draw_on(self, pane, gx, gy):
        rect = pane.cell_rect(gx, gy)
        cx = rect[0] + pane._cell // 2
        cy = rect[1] + pane._cell // 2
        pane.poll(_feed([_click(cx, cy)], pos=(cx, cy)), cx, cy)
        pane.poll(_feed([Event(EventType.MOUSE_BUTTON_UP, {"button": "left", "x": cx, "y": cy})], pos=(cx, cy)), cx, cy)


class TestModeSwitching(_ModeCase):
    def test_switching_toggles_panels(self):
        self.assertEqual(self.ui.mode, MODE_LEVEL)
        self.ui._set_mode(MODE_SPRITE)
        self.assertTrue(self.ui.sprite_mode.panel.visible)
        self.assertFalse(self.ui.sidebar.visible)
        self.assertFalse(self.ui.anim_mode.panel.visible)
        self.ui._set_mode(MODE_ANIM)
        self.assertTrue(self.ui.anim_mode.panel.visible)
        self.assertFalse(self.ui.sprite_mode.panel.visible)
        self.ui._set_mode(MODE_LEVEL)
        self.assertTrue(self.ui.viewport.visible)
        self.assertFalse(self.ui.anim_mode.panel.visible)


class TestEditorLayout(_ModeCase):
    def test_labels_are_positioned_not_stacked(self):
        ui = self.ui
        for widget in (
            ui.scene_title,
            ui.asset_title,
            ui.props_title,
            ui.props_name,
            ui.props_pos,
            ui.status_label,
        ):
            self.assertFalse(
                (widget.x, widget.y) == (0, 0),
                f"{type(widget).__name__} {widget.text!r} left at the origin",
            )
        headings = {
            (ui.scene_title.x, ui.scene_title.y),
            (ui.asset_title.x, ui.asset_title.y),
            (ui.props_title.x, ui.props_title.y),
        }
        self.assertEqual(len(headings), 3)

    def test_props_controls_live_in_props_panel(self):
        ui = self.ui
        for widget in (ui.props_title, ui.snap_button, ui.remove_button):
            self.assertGreaterEqual(widget.x, ui.props.x)
        self.assertLessEqual(
            ui.remove_button.x + ui.remove_button.width,
            self.editor.window.width,
        )

    def test_status_bar_pinned_to_bottom(self):
        ui = self.ui
        self.assertEqual(ui.status_bar.y, self.editor.window.height - STATUS_HEIGHT)
        self.assertGreaterEqual(ui.status_label.y, ui.status_bar.y)

    def test_mode_labels_are_positioned(self):
        for mode in (self.ui.sprite_mode, self.ui.anim_mode):
            for widget in (
                mode.asset_title,
                mode.status_label,
                mode.pane,
            ):
                self.assertFalse(
                    (widget.x, widget.y) == (0, 0),
                    f"{type(widget).__name__} left at the origin",
                )
        for widget in (
            self.ui.sprite_mode.new_title,
            self.ui.anim_mode.fps_label,
            self.ui.anim_mode.expo_label,
        ):
            self.assertNotEqual((widget.x, widget.y), (0, 0))

    def test_resize_repositions_props_panel(self):
        ui = self.ui
        ui.resize(900, 600)
        self.assertEqual(ui.props.x, 900 - PROPS_WIDTH)
        self.assertEqual(ui.status_bar.y, 600 - STATUS_HEIGHT)
        self.assertGreaterEqual(ui.snap_button.x, ui.props.x)


class TestSpriteMode(_ModeCase):
    def test_new_sprite_and_save_registers_asset(self):
        mode = self.ui.sprite_mode
        mode.new_w.value = "4"
        mode.new_h.value = "3"
        mode._on_new()
        self.assertEqual((mode.pane.canvas.width, mode.pane.canvas.height), (4, 3))
        self._draw_on(mode.pane, 1, 1)
        mode._on_save()
        names = [entry.filename for entry in self.temp.project.assets]
        self.assertIn("sprite_1.png", names)
        path = os.path.join(self.temp.project.assets_dir(), "sprite_1.png")
        self.assertTrue(os.path.exists(path))
        loaded = Canvas.load(path)
        self.assertEqual(loaded.get(1, 1), (255, 255, 255, 255))
        self.assertEqual(loaded.get(0, 0), (0, 0, 0, 0))
        names = [label for _, label in self.ui.asset_box._items]
        self.assertIn("sprite_1.png", names)

    def test_new_invalid_dims_reports_status(self):
        mode = self.ui.sprite_mode
        mode.new_w.value = "abc"
        mode._on_new()
        self.assertIn("integers", mode.last_saved)

    def test_open_existing_asset_loads_pixels(self):
        mode = self.ui.sprite_mode
        filename = self.temp.add_image("hero.png", 3, 2)
        mode._on_pick(filename)
        self.assertEqual((mode.pane.canvas.width, mode.pane.canvas.height), (3, 2))

    def test_next_sprite_name_skips_collisions(self):
        mode = self.ui.sprite_mode
        self.assertEqual(mode._next_sprite_name(), "sprite_1.png")
        saved = os.path.join(self.temp.project.assets_dir(), "sprite_1.png")
        Canvas(2, 2).save(saved)
        self.temp.project.import_asset(saved)
        self.assertEqual(mode._next_sprite_name(), "sprite_2.png")


class TestAnimMode(_ModeCase):
    def test_set_source_and_frame_ops(self):
        mode = self.ui.anim_mode
        filename = self.temp.add_image("hero.png", 3, 2)
        mode._on_set_source(filename)
        self.assertEqual(len(mode.frames), 1)
        self.assertEqual(mode.source_name, filename)
        mode._on_add_frame()
        self.assertEqual(len(mode.frames), 2)
        self.assertEqual(mode.frame_index, 1)
        self.assertIs(mode.pane.canvas, mode.frames[1])
        mode._on_del_frame()
        self.assertEqual(len(mode.frames), 1)
        self.assertEqual(mode.frame_index, 0)

    def test_duplicate_frame_copies_pixels(self):
        mode = self.ui.anim_mode
        filename = self.temp.add_image("hero.png", 3, 2)
        mode._on_set_source(filename)
        draw_canvas = mode.frames[0]
        draw_canvas.begin()
        draw_canvas.set(2, 1, RED)
        draw_canvas.commit()
        mode._on_dup_frame()
        self.assertEqual(len(mode.frames), 2)
        self.assertEqual(mode.frames[1].get(2, 1), RED)

    def test_export_sheet_writes_asset(self):
        mode = self.ui.anim_mode
        filename = self.temp.add_image("hero.png", 2, 1)
        mode._on_set_source(filename)
        mode.frames[0].begin()
        mode.frames[0].set(0, 0, RED)
        mode.frames[0].commit()
        mode._on_add_frame()
        mode._on_export()
        path = os.path.join(self.temp.project.assets_dir(), "hero_sheet.png")
        self.assertTrue(os.path.exists(path))
        sheet = Canvas.load(path)
        self.assertEqual(sheet.width, 4)
        self.assertEqual(sheet.height, 1)
        # Frame 2 is a copy of frame 1 (add frame copies the current frame).
        self.assertEqual(sheet.get(0, 0), RED)
        self.assertEqual(sheet.get(1, 0), (0, 0, 0, 0))
        self.assertEqual(sheet.get(2, 0), RED)
        self.assertEqual(sheet.get(3, 0), (0, 0, 0, 0))
        self.assertIn("hero_sheet.png", [a.filename for a in self.temp.project.assets])

    def test_playback_advances_frames(self):
        mode = self.ui.anim_mode
        filename = self.temp.add_image("hero.png", 2, 1)
        mode._on_set_source(filename)
        mode._on_add_frame()
        self.assertEqual(mode.frame_index, 1)
        mode.fps_input.value = "8"
        mode.playing = True
        mode.tick(0.2)
        self.assertEqual(mode.frame_index, 0)
        self.assertIs(mode.pane.canvas, mode.frames[0])
        mode.tick(0.2)
        self.assertIs(mode.pane.canvas, mode.frames[0])

    def test_playback_does_nothing_paused(self):
        mode = self.ui.anim_mode
        filename = self.temp.add_image("hero.png", 2, 1)
        mode._on_set_source(filename)
        mode.playing = False
        mode.tick(5.0)
        self.assertEqual(mode.frame_index, 0)

    def test_add_frame_copies_current_pixels(self):
        mode = self.ui.anim_mode
        filename = self.temp.add_image("hero.png", 3, 2)
        mode._on_set_source(filename)
        frame = mode.frames[0]
        frame.begin()
        frame.set(1, 1, RED)
        frame.commit()
        mode._on_add_frame()
        self.assertEqual(len(mode.frames), 2)
        self.assertEqual(mode.frame_index, 1)
        self.assertEqual(mode.frames[1].get(1, 1), RED)
        self.assertIs(mode.pane.canvas, mode.frames[1])

    def test_export_with_no_frames_reports(self):
        mode = self.ui.anim_mode
        mode._on_export()
        self.assertIn("No frames", mode.last_saved)


class TestAnimHelp(_ModeCase):
    def test_help_overlay_built_and_hidden(self):
        mode = self.ui.anim_mode
        self.assertFalse(mode.help_overlay.visible)
        self.assertGreaterEqual(len(mode.help_steps), 3)
        self.assertGreaterEqual(len(mode.help_buttons), 2)
        for step in mode.help_steps:
            self.assertTrue(step.text.strip())

    def test_help_button_click_toggles_overlay(self):
        ui = self.ui
        ui._set_mode(MODE_ANIM)
        mode = ui.anim_mode
        cx = mode.help_button.x + mode.help_button.width // 2
        cy = mode.help_button.y + mode.help_button.height // 2
        ui.root.handle_input(_feed([_click(cx, cy)], pos=(cx, cy)))
        self.assertTrue(mode.help_overlay.visible)
        ui.root.handle_input(_feed([_click(cx, cy)], pos=(cx, cy)))
        self.assertFalse(mode.help_overlay.visible)

    def test_close_button_hides_overlay(self):
        ui = self.ui
        ui._set_mode(MODE_ANIM)
        mode = ui.anim_mode
        mode._toggle_help()
        self.assertTrue(mode.help_overlay.visible)
        close = mode.help_close
        cx = close.x + close.width // 2
        cy = close.y + close.height // 2
        ui.root.handle_input(_feed([_click(cx, cy)], pos=(cx, cy)))
        self.assertFalse(mode.help_overlay.visible)

    def test_resume_link_hides_overlay_and_gives_hint(self):
        mode = self.ui.anim_mode
        mode.help_overlay.visible = True
        handler = mode._resume_from_state("preview")
        handler()
        self.assertFalse(mode.help_overlay.visible)
        self.assertIsInstance(mode.last_saved, str)
        self.assertTrue(mode.last_saved.strip())


class TestColorSwatches(_ModeCase):
    def _assert_palette(self, mode):
        self.assertEqual(len(mode.color_swatches), len(PALETTE))
        for swatch, rgb in zip(mode.color_swatches, PALETTE):
            self.assertEqual(swatch.background, rgb)
            self.assertNotEqual((swatch.x, swatch.y), (0, 0))
        self.assertNotEqual((mode.color_caption.x, mode.color_caption.y), (0, 0))
        self.assertEqual(mode._color_index, 1)
        self.assertEqual(mode.pane.color, PALETTE[1] + (255,))

    def test_sprite_mode_has_palette_swatches(self):
        self._assert_palette(self.ui.sprite_mode)

    def test_sprite_mode_pick_color_sets_pane(self):
        mode = self.ui.sprite_mode
        mode._pick_color((255, 176, 32))
        self.assertEqual(mode.pane.color, (255, 176, 32, 255))
        self.assertEqual(mode._color_index, PALETTE.index((255, 176, 32)))
        for index, swatch in enumerate(mode.color_swatches):
            expected = UI_WHITE if index == mode._color_index else (220, 220, 220)
            self.assertEqual(swatch.border, expected)
        self.assertIn("Color", mode.last_saved)

    def test_anim_mode_has_palette_swatches(self):
        self._assert_palette(self.ui.anim_mode)

    def test_anim_mode_pick_color_sets_pane(self):
        mode = self.ui.anim_mode
        mode._pick_color((255, 32, 32))
        self.assertEqual(mode.pane.color, (255, 32, 32, 255))
        self.assertEqual(mode._color_index, PALETTE.index((255, 32, 32)))
        self.assertEqual(mode.color_swatches[mode._color_index].border, UI_WHITE)

    def test_anim_hint_tracks_state(self):
        mode = self.ui.anim_mode
        mode._update_hint()
        self.assertIn("source", mode.hint_label.text.lower())
        filename = self.temp.add_image("hero.png", 2, 1)
        mode._on_set_source(filename)
        self.assertIn("1/1", mode.hint_label.text)
        mode._on_add_frame()
        self.assertIn("2/2", mode.hint_label.text)
        mode._on_play()
        self.assertIn("playing", mode.hint_label.text.lower())
        self.assertIn("8 fps", mode.hint_label.text.lower())

    def test_anim_speed_control(self):
        mode = self.ui.anim_mode
        filename = self.temp.add_image("hero.png", 2, 1)
        mode._on_set_source(filename)
        mode._on_add_frame()
        mode.fps_input.value = "2"
        mode._on_play()
        self.assertIn("2 fps", mode.play_button.text)
        self.assertIn("2 fps", mode.hint_label.text.lower())
        mode.tick(0.6)
        self.assertEqual(mode.frame_index, 0)
        mode.tick(0.6)
        self.assertEqual(mode.frame_index, 1)

    def test_eraser_toggle_flips_sprite_tool(self):
        mode = self.ui.sprite_mode
        self.assertEqual(mode.pane.tool, "pencil")
        mode._toggle_eraser()
        self.assertEqual(mode.pane.tool, "eraser")
        self.assertEqual(mode.tool_button.text, "Pen")
        self.assertEqual(mode.tool_button.background, GRAY_SELECTED)
        mode._toggle_eraser()
        self.assertEqual(mode.pane.tool, "pencil")
        self.assertEqual(mode.tool_button.text, "Eraser")
        self.assertEqual(mode.tool_button.background, GRAY_SURFACE)

    def test_eraser_clears_pixels_in_sprite_mode(self):
        mode = self.ui.sprite_mode
        mode.new_w.value = "4"
        mode.new_h.value = "3"
        mode._on_new()
        self._draw_on(mode.pane, 1, 1)
        self.assertEqual(mode.pane.canvas.get(1, 1), (255, 255, 255, 255))
        mode._toggle_eraser()
        self.assertEqual(mode.pane.tool, TOOL_ERASER)
        self._draw_on(mode.pane, 1, 1)
        self.assertEqual(mode.pane.canvas.get(1, 1), (0, 0, 0, 0))

    def test_fill_fills_region_in_sprite_mode(self):
        mode = self.ui.sprite_mode
        mode.new_w.value = "4"
        mode.new_h.value = "3"
        mode._on_new()
        mode._toggle_fill()
        self.assertEqual(mode.pane.tool, TOOL_BUCKET)
        self.assertEqual(mode.fill_button.text, "Back")
        self.assertEqual(mode.fill_button.background, GRAY_SELECTED)
        self._draw_on(mode.pane, 0, 0)
        for y in range(3):
            for x in range(4):
                self.assertEqual(mode.pane.canvas.get(x, y), (255, 255, 255, 255))

    def test_fill_and_eraser_buttons_are_mutually_exclusive(self):
        mode = self.ui.sprite_mode
        mode.new_w.value = "4"
        mode.new_h.value = "3"
        mode._on_new()
        self.assertEqual(mode.pane.tool, "pencil")
        mode._toggle_eraser()
        self.assertEqual(mode.pane.tool, TOOL_ERASER)
        self.assertEqual(mode.fill_button.background, GRAY_SURFACE)
        mode._toggle_fill()
        self.assertEqual(mode.pane.tool, TOOL_BUCKET)
        self.assertEqual(mode.tool_button.text, "Eraser")
        self.assertEqual(mode.tool_button.background, GRAY_SURFACE)
        self.assertEqual(mode.fill_button.background, GRAY_SELECTED)
        mode._toggle_fill()
        self.assertEqual(mode.pane.tool, "pencil")
        self.assertEqual(mode.fill_button.text, "Fill")

    def test_eraser_toggle_flips_anim_tool(self):
        mode = self.ui.anim_mode
        self.assertEqual(mode.pane.tool, "pencil")
        mode._toggle_eraser()
        self.assertEqual(mode.pane.tool, "eraser")
        mode._toggle_eraser()
        self.assertEqual(mode.pane.tool, "pencil")
        self.assertNotEqual((mode.tool_button.x, mode.tool_button.y), (0, 0))

    def test_eraser_clears_pixels_in_anim_mode(self):
        mode = self.ui.anim_mode
        filename = self.temp.add_image("hero.png", 3, 2)
        mode._on_set_source(filename)
        self._draw_on(mode.pane, 1, 1)
        frame = mode.frames[0]
        self.assertEqual(frame.get(1, 1), (255, 255, 255, 255))
        mode._toggle_eraser()
        self.assertEqual(mode.pane.tool, TOOL_ERASER)
        self._draw_on(mode.pane, 1, 1)
        self.assertEqual(frame.get(1, 1), (0, 0, 0, 0))

    def test_fill_fills_region_in_anim_mode(self):
        mode = self.ui.anim_mode
        filename = self.temp.add_image("hero.png", 3, 2)
        mode._on_set_source(filename)
        mode._toggle_fill()
        self.assertEqual(mode.pane.tool, TOOL_BUCKET)
        self.assertEqual(mode.fill_button.text, "Back")
        self.assertEqual(mode.fill_button.background, GRAY_SELECTED)
        self._draw_on(mode.pane, 0, 0)
        frame = mode.frames[0]
        for y in range(2):
            for x in range(3):
                self.assertEqual(frame.get(x, y), (255, 255, 255, 255))
        mode._toggle_fill()
        self.assertEqual(mode.pane.tool, "pencil")

    def test_anim_speed_changes_by_typing_into_field(self):
        ui = self.ui
        ui._set_mode(MODE_ANIM)
        mode = ui.anim_mode
        filename = self.temp.add_image("hero.png", 2, 1)
        mode._on_set_source(filename)
        mode._on_add_frame()
        field = mode.fps_input
        fx, fy = field.x + 8, field.y + 8
        ui.root.handle_input(_feed([_click(fx, fy)], pos=(fx, fy)))
        ui.root.handle_input(
            _feed(
                [
                    Event(EventType.TEXT_INPUT, {"text": "24"}),
                ],
                pos=(fx, fy),
            )
        )
        self.assertEqual(field.value, "24")
        mode._on_play()
        self.assertIn("24 fps", mode.play_button.text)
        self.assertIn("24 fps", mode.hint_label.text.lower())

    def test_undo_redo_buttons_sprite_mode(self):
        mode = self.ui.sprite_mode
        canvas = mode.pane.canvas
        self.assertNotEqual((mode.undo_button.x, mode.redo_button.x), (0, 0))
        self.assertFalse(canvas.undo())
        self._draw_on(mode.pane, 2, 2)
        self.assertNotEqual(canvas.get(2, 2), (0, 0, 0, 0))
        mode._on_undo()
        self.assertEqual(canvas.get(2, 2), (0, 0, 0, 0))
        mode._on_redo()
        self.assertNotEqual(canvas.get(2, 2), (0, 0, 0, 0))

    def test_undo_redo_buttons_anim_mode(self):
        mode = self.ui.anim_mode
        filename = self.temp.add_image("hero.png", 3, 2)
        mode._on_set_source(filename)
        self.assertNotEqual((mode.undo_button.x, mode.redo_button.x), (0, 0))
        self._draw_on(mode.pane, 1, 1)
        frame = mode.frames[0]
        self.assertNotEqual(frame.get(1, 1), (0, 0, 0, 0))
        mode._on_undo()
        self.assertEqual(frame.get(1, 1), (0, 0, 0, 0))
        mode._on_redo()
        self.assertNotEqual(frame.get(1, 1), (0, 0, 0, 0))


class TestRefresh(_ModeCase):
    def test_refresh_syncs_manifest_with_disk(self):
        ui = self.ui
        project = self.temp.project
        assets_dir = project.assets_dir()
        missing = self.temp.add_image("gone.png")
        os.remove(project.asset_path(missing))
        write_fixture(assets_dir, "new.png", png_bytes(4, 4))
        with open(os.path.join(assets_dir, "notes.txt"), "w") as handle:
            handle.write("ignore me")
        ui._on_refresh()
        self.assertIsNone(project.asset(missing))
        self.assertIsNotNone(project.asset("new.png"))
        self.assertIsNone(project.asset("notes.txt"))
        names = [label for _, label in ui.asset_box._items]
        self.assertIn("new.png", names)
        self.assertNotIn(missing, names)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("+1 added", ui.status)
        self.assertIn("-1 removed", ui.status)

    def test_refresh_dedupes_manifest(self):
        ui = self.ui
        project = self.temp.project
        filename = self.temp.add_image("hero.png")
        entry = project.asset(filename)
        project.assets.append(entry)
        ui._on_refresh()
        count = sum(1 for item in project.assets if item.filename == filename)
        self.assertEqual(count, 1)
        names = [label for _, label in ui.asset_box._items]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()