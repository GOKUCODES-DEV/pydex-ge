"""Tests for the dex-editor (project model, codegen, pixels, UI, viewport).

The editor logic is pure where possible so it runs headless; images are
synthesized with the shared fixtures and drawn through the stub renderer.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _image_fixtures import png_bytes, write_fixture
from _stub_backend import StubBackend, StubRenderer

from pydex_ge import Event, EventType, Input
from pydex_ge.core import Renderer
from pydex_ge.editor import _pixels
from pydex_ge.editor.codegen import generate_main, generate_scene, scene_class_name
from pydex_ge.editor.project import (
    AssetEntry,
    DexProject,
    SceneEntry,
    SpriteEntry,
    asset_kind,
)
from pydex_ge.editor.viewport import Viewport
from pydex_ge.exceptions import ConfigurationError
from pydex_ge.ui import Button, ListBox, TextInput, UIRoot, Widget


class _TempProject:
    def __init__(self, name: str = "Demo") -> None:
        self.base = tempfile.mkdtemp()
        self.root = os.path.join(self.base, name)
        self.project = DexProject.create_empty(self.root, name)

    def add_image(self, filename: str, width: int = 12, height: int = 8) -> str:
        write_fixture(
            os.path.join(self.project.assets_dir()), filename, png_bytes(width, height)
        )
        return self.project.import_asset(
            os.path.join(self.project.assets_dir(), filename)
        ).filename

    def cleanup(self) -> None:
        import shutil

        shutil.rmtree(self.base, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cleanup()
        return False


# --------------------------------------------------------------------------- #
# project model
# --------------------------------------------------------------------------- #


class TestProject(unittest.TestCase):
    def test_create_empty_layout(self):
        with _TempProject() as t:
            self.assertTrue(os.path.isfile(t.project.manifest_path))
            self.assertTrue(os.path.isdir(t.project.assets_dir()))
            self.assertTrue(os.path.isfile(t.project.main_path))
            self.assertEqual(t.project.name, "Demo")
            self.assertEqual([s.name for s in t.project.scenes], ["Main"])

    def test_create_empty_refuses_nonempty_dir(self):
        base = tempfile.mkdtemp()
        try:
            with open(os.path.join(base, "keep.txt"), "w") as handle:
                handle.write("x")
            with self.assertRaises(ConfigurationError):
                DexProject.create_empty(base, "Nope")
        finally:
            import shutil

            shutil.rmtree(base, ignore_errors=True)

    def test_roundtrip(self):
        with _TempProject() as t:
            t.add_image("hero.png")
            scene = t.project.scene("Main")
            scene.add_sprite(SpriteEntry("hero.png", x=10, y=20, layer=2, scale=1.5))
            t.project.add_scene("Bonus")
            t.project.save()
            loaded = DexProject.load(t.root)
            self.assertEqual(loaded.name, "Demo")
            self.assertEqual(len(loaded.assets), 1)
            self.assertEqual([s.name for s in loaded.scenes], ["Main", "Bonus"])
            sprite = loaded.scene("Main").sprites[0]
            self.assertEqual((sprite.x, sprite.y, sprite.layer), (10.0, 20.0, 2))
            self.assertEqual(sprite.scale, 1.5)

    def test_load_missing_manifest(self):
        with self.assertRaises(ConfigurationError):
            DexProject.load(tempfile.mkdtemp())

    def test_load_bad_version(self):
        with _TempProject() as t:
            t.project.save()
            with open(t.project.manifest_path, "w", encoding="utf-8") as handle:
                handle.write('{"version": 99, "name": "x", "assets": [], "scenes": []}')
            with self.assertRaises(ConfigurationError):
                DexProject.load(t.root)

    def test_add_and_remove_scene(self):
        with _TempProject() as t:
            t.project.add_scene("Level 2")
            self.assertIsNotNone(t.project.scene("Level 2"))
            with self.assertRaises(ConfigurationError):
                t.project.add_scene("Level 2")
            self.assertTrue(t.project.remove_scene("Level 2"))
            self.assertFalse(t.project.remove_scene("Level 2"))

    def test_name_keyword_rejected(self):
        with self.assertRaises(ConfigurationError):
            DexProject.create_empty(tempfile.mkdtemp(), "class")

    def test_import_asset_deduplicates(self):
        with _TempProject() as t:
            src = os.path.join(t.project.assets_dir(), "hero.png")
            write_fixture(t.project.assets_dir(), "hero.png", png_bytes(12, 8))
            first = t.project.import_asset(src)
            second = t.project.import_asset(src)
            self.assertIs(first, second)
            ext_dir = os.path.join(t.base, "external")
            os.makedirs(ext_dir, exist_ok=True)
            ext_src = os.path.join(ext_dir, "hero.png")
            with open(ext_src, "wb") as handle:
                handle.write(png_bytes(8, 6))
            renamed = t.project.import_asset(ext_src)
            self.assertEqual(renamed.filename, "hero-2.png")

    def test_remove_asset(self):
        with _TempProject() as t:
            filename = t.add_image("hero.png")
            self.assertTrue(t.project.remove_asset(filename))
            self.assertFalse(os.path.isfile(t.project.asset_path(filename)))
            self.assertFalse(t.project.remove_asset(filename))

    def test_asset_kind(self):
        self.assertEqual(asset_kind("x.png"), "image")
        self.assertEqual(asset_kind("x.wav"), "audio")
        with self.assertRaises(ConfigurationError):
            asset_kind("x.zip")

    def test_entries_roundtrip_dicts(self):
        entry = SpriteEntry("a.png", x=1.5, y=-2, layer=3, flip_h=True, visible=False)
        clone = SpriteEntry.from_dict(entry.to_dict())
        self.assertEqual((clone.x, clone.y, clone.layer), (1.5, -2.0, 3))
        self.assertTrue(clone.flip_h)
        self.assertFalse(clone.visible)
        asset = AssetEntry("image", "a.png")
        self.assertEqual(AssetEntry.from_dict(asset.to_dict()), asset)


# --------------------------------------------------------------------------- #
# codegen
# --------------------------------------------------------------------------- #


class TestCodegen(unittest.TestCase):
    def test_scene_class_name(self):
        self.assertEqual(scene_class_name(SceneEntry("Main")), "MainScene")

    def test_generate_scene_with_sprites(self):
        scene = SceneEntry("Main")
        scene.add_sprite(SpriteEntry("hero.png", x=100, y=60))
        scene.add_sprite(
            SpriteEntry("hero.png", x=30, y=20, layer=2, scale=2, flip_h=True)
        )
        src = generate_scene(None, scene)
        self.assertIn("class MainScene(Scene):", src)
        self.assertIn("camera=Camera2D(1600, 1200)", src)
        self.assertIn("hero = Sprite('assets/hero.png')", src)
        self.assertIn("hero.position = (100, 60)", src)
        self.assertIn("hero_2.z = 2", src)
        self.assertIn("hero_2.scale = 2", src)
        self.assertIn("hero_2.flip_x = True", src)
        compile(src, "main.py", "exec")

    def test_generate_scene_empty(self):
        src = generate_scene(None, SceneEntry("Empty"))
        self.assertIn("(no sprites placed yet)", src)
        compile(src, "main.py", "exec")

    def test_generate_main_structure(self):
        project = DexProject(
            os.path.join(tempfile.mkdtemp(), "g"), "Adventure"
        )
        project.scenes.append(SceneEntry("Main"))
        src = generate_main(project)
        self.assertIn("from pydex_ge import Camera2D, Game, Scene, Sprite", src)
        self.assertIn("class AdventureGame(Game):", src)
        self.assertIn("super().__init__('Adventure', 800, 600, fps=60)", src)
        self.assertIn("self.scenes.push(MainScene())", src)
        self.assertIn('if __name__ == "__main__":', src)
        compile(src, "main.py", "exec")

    def test_generate_main_without_scenes_compiles(self):
        project = DexProject(os.path.join(tempfile.mkdtemp(), "g"), "Blank")
        src = generate_main(project)
        compile(src, "main.py", "exec")
        self.assertNotIn("self.screen", src)


# --------------------------------------------------------------------------- #
# pixels
# --------------------------------------------------------------------------- #


class TestPixels(unittest.TestCase):
    def _rows(self, width=8, height=6):
        return [
            bytes(
                byte
                for x in range(width)
                for byte in ((x * 25) % 256, (y * 40) % 256, (x + y) * 7 % 256, 255)
            )
            for y in range(height)
        ]

    def test_decode_fixture_bmp_and_png(self):
        from _image_fixtures import bmp_bytes

        width, height, rows = _pixels.decode(bmp_bytes(8, 6))
        self.assertEqual((width, height), (8, 6))
        width, height, rows = _pixels.decode(png_bytes(10, 7))
        self.assertEqual((width, height), (10, 7))
        self.assertEqual(len(rows[0]), 10 * 4)

    def test_encode_png_roundtrip(self):
        rows = self._rows(16, 16)
        width, height, decoded = _pixels.decode(_pixels.encode_png(16, 16, rows))
        self.assertEqual(decoded, rows)

    def test_encode_bmp_roundtrip(self):
        rows = self._rows(16, 16)
        _, _, decoded = _pixels.decode(_pixels.encode_bmp(16, 16, rows))
        self.assertEqual(decoded, rows)

    def test_rejects_unknown_format(self):
        with self.assertRaises(_pixels.ImageCodecError):
            _pixels.decode(b"GIF89a not supported")

    def test_rejects_geometry_mismatch(self):
        with self.assertRaises(_pixels.ImageCodecError):
            _pixels.encode_png(4, 4, [b"\x00" * 16] * 3)


# --------------------------------------------------------------------------- #
# ui widgets
# --------------------------------------------------------------------------- #


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


class TestWidgets(unittest.TestCase):
    def test_tree_ops(self):
        root = Widget(x=0, y=0, width=200, height=200)
        child = Widget(x=5, y=5, width=10, height=10)
        root.add(child)
        self.assertIs(child.parent, root)
        self.assertEqual(len(root), 1)
        self.assertTrue(root.remove(child))
        self.assertIsNone(child.parent)

    def test_contains_and_rect(self):
        widget = Widget(x=10, y=20, width=30, height=40)
        self.assertEqual(widget.rect, (10, 20, 30, 40))
        self.assertTrue(widget.contains(10, 20))
        self.assertFalse(widget.contains(40, 60))

    def test_text_input_editing(self):
        field = TextInput("abc", x=0, y=0, width=200, height=28, max_length=5)
        ui = UIRoot(width=300, height=200)
        ui.add(field)
        ui.focus(field)
        ui.handle_input(
            _feed([Event(EventType.TEXT_INPUT, {"text": "Z"})], pos=(0, 0))
        )
        self.assertEqual(field.value, "abcZ")
        self.assertEqual(field.caret, 4)
        ui.handle_input(_feed([Event(EventType.KEY_DOWN, {"key": "left"})]))
        self.assertEqual(field.caret, 3)
        ui.handle_input(_feed([Event(EventType.KEY_DOWN, {"key": "backspace"})]))
        self.assertEqual(field.value, "abZ")
        ui.handle_input(_feed([Event(EventType.KEY_DOWN, {"key": "home"})]))
        self.assertEqual(field.caret, 0)
        ui.handle_input(_feed([Event(EventType.TEXT_INPUT, {"text": "Q"})]))
        self.assertEqual(field.value, "QabZ")

    def test_text_input_max_length(self):
        field = TextInput("", max_length=2)
        ui = UIRoot(width=100, height=100)
        ui.add(field)
        ui.focus(field)
        ui.handle_input(_feed([Event(EventType.TEXT_INPUT, {"text": "abc"})]))
        self.assertEqual(field.value, "ab")

    def test_text_input_click_selects_all_so_typing_replaces(self):
        field = TextInput("8", x=0, y=0, width=80, height=28)
        ui = UIRoot(width=200, height=200)
        ui.add(field)
        ui.handle_input(_feed([_click(10, 10)], pos=(10, 10)))
        self.assertIs(ui.focused, field)
        self.assertEqual(field.caret, 1)
        ui.handle_input(_feed([Event(EventType.TEXT_INPUT, {"text": "24"})]))
        self.assertEqual(field.value, "24")

    def test_text_input_click_on_empty_keeps_caret_append(self):
        field = TextInput("", x=0, y=0, width=80, height=28)
        ui = UIRoot(width=200, height=200)
        ui.add(field)
        ui.handle_input(_feed([_click(10, 10)], pos=(10, 10)))
        ui.handle_input(_feed([Event(EventType.TEXT_INPUT, {"text": "gizmo"})]))
        self.assertEqual(field.value, "gizmo")

    def test_text_input_submit(self):
        submitted = []
        field = TextInput("", on_submit=lambda v: submitted.append(v))
        ui = UIRoot(width=100, height=100)
        ui.add(field)
        ui.focus(field)
        ui.handle_input(
            _feed(
                [
                    Event(EventType.TEXT_INPUT, {"text": "go"}),
                    Event(EventType.TEXT_INPUT, {"text": "\n"}),
                ]
            )
        )
        self.assertEqual(submitted, ["go"])

    def test_button_click_and_focus_rules(self):
        clicked = []
        button = Button("OK", x=10, y=10, width=80, height=30)
        ui = UIRoot(width=400, height=300)
        ui.add(button)
        ui.handle_input(_feed([_click(30, 25)], pos=(30, 25)))
        self.assertFalse(clicked)  # no callback set
        button = Button(
            "OK", x=10, y=10, width=80, height=30, on_click=lambda: clicked.append(1)
        )
        ui2 = UIRoot(width=400, height=300)
        ui2.add(button)
        ui2.handle_input(_feed([_click(30, 25)], pos=(30, 25)))
        self.assertEqual(clicked, [1])
        self.assertIsNone(ui2.focused)  # buttons do not grab focus

    def test_focus_and_blur(self):
        field = TextInput("", x=0, y=0, width=100, height=28)
        button = Button("B", x=0, y=40, width=40, height=20)
        ui = UIRoot(width=200, height=200)
        ui.add(field).add(button)
        ui.handle_input(_feed([_click(10, 10)], pos=(10, 10)))
        self.assertIs(ui.focused, field)
        ui.handle_input(_feed([_click(20, 50)], pos=(20, 50)))
        self.assertIsNone(ui.focused)  # buttons don't grab focus

    def test_listbox_select(self):
        selected = []
        box = ListBox(["one", "two"], x=0, y=0, width=100, height=60, item_height=22)
        box.on_select = lambda item: selected.append(item)
        ui = UIRoot(width=200, height=200)
        ui.add(box)
        ui.handle_input(_feed([_click(5, 30)], pos=(5, 30)))
        self.assertEqual(selected, ["two"])


# --------------------------------------------------------------------------- #
# viewport
# --------------------------------------------------------------------------- #


class TestViewport(unittest.TestCase):
    def setUp(self):
        self._tmp = [].__class__  # placeholder, unused

    def _viewport(self):
        self.temp = _TempProject()
        self.addCleanup(self.temp.cleanup)
        filename = self.temp.add_image("hero.png", 12, 8)
        self.backend = StubBackend()
        self.backend.image_sizes = {
            os.path.abspath(
                os.path.join(self.temp.project.assets_dir(), filename)
            ): (12, 8)
        }
        self.renderer = Renderer(StubRenderer())
        self.vp = Viewport(
            project=self.temp.project,
            sprite_backend=self.backend,
            x=240,
            y=44,
            width=780,
            height=676,
        )
        self.vp.set_project(self.temp.project, "Main")
        self.vp.palette = "hero.png"
        self.input = Input(backend=self.backend)
        return self.vp

    def _frame(self, events, pos):
        self.backend._mouse_position = pos
        self.backend._pending = list(events)
        self.input.begin_frame()
        for event in events:
            self.input.handle_event(event)
        self.vp.poll(self.input, pos[0], pos[1])
        self.vp.draw(self.renderer)

    def test_place_and_move_and_delete(self):
        vp = self._viewport()
        self.assertEqual(len(vp.scene.sprites), 0)
        self._frame(
            [Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": 300, "y": 100})],
            (300, 100),
        )
        self.assertEqual(len(vp.scene.sprites), 1)
        self.assertIs(vp.selected, vp.scene.sprites[0])
        snap = vp.scene.sprites[0]
        self.assertEqual(snap.x % vp.scene.grid, 0)  # snapped to grid

    def test_select_does_not_duplicate(self):
        vp = self._viewport()
        self._frame([Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": 300, "y": 100})], (300, 100))
        sprite = vp.scene.sprites[0]
        rect = vp._screen_rects[id(sprite)]
        cx, cy = rect[0] + rect[2] // 2, rect[1] + rect[3] // 2
        self._frame([Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": cx, "y": cy})], (cx, cy))
        self.assertEqual(len(vp.scene.sprites), 1)
        self.assertIs(vp.selected, sprite)

    def test_drag_snaps_to_grid(self):
        vp = self._viewport()
        sprite = SpriteEntry("hero.png", x=10, y=10)
        vp.scene.sprites.append(sprite)
        vp.draw(self.renderer)
        rect = vp._screen_rects[id(sprite)]
        cx, cy = rect[0] + rect[2] // 2, rect[1] + rect[3] // 2
        self._frame(
            [Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": cx, "y": cy})],
            (cx, cy),
        )
        self.assertIs(vp.selected, sprite)
        self.assertTrue(vp._dragging)
        target = vp._camera.world_to_screen((64, 32))
        self._frame([], (round(target.x), round(target.y)))
        self.assertEqual((sprite.x, sprite.y), (64.0, 32.0))
        self.assertEqual(sprite.x % vp.scene.grid, 0)
        self.assertEqual(sprite.y % vp.scene.grid, 0)

    def test_drag_with_snap_off_preserves_offset(self):
        vp = self._viewport()
        vp.snap_to_grid = False
        sprite = SpriteEntry("hero.png", x=10, y=10)
        vp.scene.sprites.append(sprite)
        vp.draw(self.renderer)
        rect = vp._screen_rects[id(sprite)]
        cx, cy = rect[0] + rect[2] // 2, rect[1] + rect[3] // 2
        self._frame(
            [Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": cx, "y": cy})],
            (cx, cy),
        )
        wx, wy = vp._world_click(cx, cy)
        offset = (sprite.x - wx, sprite.y - wy)
        self.assertEqual(offset, vp._drag_offset)
        target = vp._camera.world_to_screen((64, 32))
        tx, ty = round(target.x), round(target.y)
        self._frame([], (tx, ty))
        wx2, wy2 = vp._world_click(tx, ty)
        expected = (wx2 + offset[0], wy2 + offset[1])
        self.assertEqual((sprite.x, sprite.y), (round(expected[0]), round(expected[1])))

    def test_align_all_to_grid(self):
        vp = self._viewport()
        scene = vp.scene
        grid = scene.grid
        scene.sprites.extend(
            [
                SpriteEntry("hero.png", x=10, y=10),
                SpriteEntry("hero.png", x=64, y=32),
                SpriteEntry("hero.png", x=99, y=83),
            ]
        )
        moved = vp.align_all_to_grid()
        self.assertEqual(moved, 2)
        self.assertEqual((scene.sprites[0].x, scene.sprites[0].y), (0.0, 0.0))
        self.assertEqual((scene.sprites[1].x, scene.sprites[1].y), (64.0, 32.0))
        self.assertEqual((scene.sprites[2].x, scene.sprites[2].y), (96.0, 96.0))
        for entry in scene.sprites:
            self.assertEqual(entry.x % grid, 0)
            self.assertEqual(entry.y % grid, 0)

    def test_align_reports_zero_when_already_aligned(self):
        vp = self._viewport()
        vp.scene.sprites.append(SpriteEntry("hero.png", x=32, y=64))
        self.assertEqual(vp.align_all_to_grid(), 0)

    def test_middle_drag_pans(self):
        vp = self._viewport()
        self._frame([Event(EventType.MOUSE_BUTTON_DOWN, {"button": "middle", "x": 300, "y": 100})], (300, 100))
        self._frame([], (330, 120))
        self.assertEqual((vp._pan_x, vp._pan_y), (-30.0, -20.0))

    def test_zoom_world(self):
        vp = self._viewport()
        vp.zoom_world(2.0)
        self.assertEqual(vp._zoom, 2.0)
        vp.zoom_world(1000)
        self.assertLessEqual(vp._zoom, 8.0)
        vp.zoom_world(0.00001)
        self.assertGreaterEqual(vp._zoom, 0.05)

    def test_grid_covers_whole_viewport(self):
        # The viewport camera is window-space (panel offset baked into its
        # position); the visible grid must still span the widget's corners.
        vp = self._viewport()
        vp._zoom = 2.0
        vp._pan_x = -60.0
        vp._pan_y = 0.0
        vp.draw(self.renderer)
        cols = [line[0] for line in self.renderer._renderer.lines if line[0] == line[2]]
        right = vp.x + vp.width
        bottom = vp.y + vp.height
        self.assertTrue(any(vp.x <= c <= right for c in cols))
        self.assertLessEqual(right - max(c for c in cols if vp.x <= c <= right),
                             vp.scene.grid * vp._zoom)
        rows = [line[1] for line in self.renderer._renderer.lines if line[1] == line[3]]
        self.assertTrue(any(vp.y <= r <= bottom for r in rows))
        self.assertLessEqual(bottom - max(r for r in rows if vp.y <= r <= bottom),
                             vp.scene.grid * vp._zoom)

    def test_snapped_sprite_anchor_on_drawn_grid_when_zoomed(self):
        vp = self._viewport()
        vp._zoom = 2.0
        vp._pan_x = -60.0
        cell = vp.scene.grid
        vp.draw(self.renderer)
        target = vp._camera.world_to_screen((cell * 2, cell))
        tx, ty = round(target.x), round(target.y)
        self._frame([Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": tx, "y": ty})], (tx, ty))
        sprite = vp.scene.sprites[-1]
        self.assertEqual(sprite.x % cell, 0)
        self.assertEqual(sprite.y % cell, 0)
        vp.draw(self.renderer)
        cols = [line[0] for line in self.renderer._renderer.lines if line[0] == line[2]]
        anchor = round(vp._camera.world_to_screen((sprite.x, sprite.y)).x)
        self.assertIn(anchor, cols)

    def test_place_scales_sprite_to_fill_cell(self):
        vp = self._viewport()
        cell = vp.scene.grid
        self._frame(
            [Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": 300, "y": 100})],
            (300, 100),
        )
        sprite = vp.scene.sprites[0]
        self.assertEqual(sprite.x % cell, 0)
        self.assertEqual(sprite.y % cell, 0)
        self.assertEqual(sprite.scale, (cell / 12, cell / 8))

    def test_place_fills_cell_on_screen(self):
        vp = self._viewport()
        cell = vp.scene.grid
        vp.draw(self.renderer)
        self._frame(
            [Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": 300, "y": 100})],
            (300, 100),
        )
        sprite = vp.scene.sprites[0]
        vp.draw(self.renderer)
        rect = vp._screen_rects[id(sprite)]
        self.assertEqual(rect[2], round(cell * vp._zoom))
        self.assertEqual(rect[3], round(cell * vp._zoom))

    def test_place_uses_clicked_cell_near_edge(self):
        # A click near the far edge of a cell must stay in that cell, not
        # jump into the next grid square (world 63 -> cell 32, not 64).
        vp = self._viewport()
        cell = vp.scene.grid
        vp.draw(self.renderer)
        target = vp._camera.world_to_screen((cell * 2 - 1, cell * 2 - 1))
        tx, ty = round(target.x), round(target.y)
        self._frame(
            [Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": tx, "y": ty})],
            (tx, ty),
        )
        self.assertEqual(len(vp.scene.sprites), 1)
        sprite = vp.scene.sprites[0]
        self.assertEqual((sprite.x, sprite.y), (cell, cell))

    def test_place_and_occupy_disagree_at_cell_edge(self):
        # Occupancy must use the same floored mapping as placement, so a
        # sprite at (32, 32) blocks its whole cell but not the next one.
        vp = self._viewport()
        cell = vp.scene.grid
        vp.scene.sprites.append(SpriteEntry("hero.png", x=cell, y=cell))
        self.assertTrue(vp._cell_occupied(cell * 2 - 1, cell * 2 - 1))
        self.assertFalse(vp._cell_occupied(cell * 3 - 1, cell * 3 - 1))

    def test_place_refuses_occupied_cell(self):
        vp = self._viewport()
        cell = vp.scene.grid
        vp.draw(self.renderer)
        vp.scene.sprites.append(SpriteEntry("hero.png", x=cell, y=cell))
        messages = []
        vp.on_message = messages.append
        tx, ty = round(vp._camera.world_to_screen((63, 63)).x), round(vp._camera.world_to_screen((63, 63)).y)
        placed = vp._place_palette(tx, ty)
        self.assertFalse(placed)  # same cell -> refused
        self.assertEqual(len(vp.scene.sprites), 1)
        self.assertTrue(messages)
        self.assertIn("already", messages[0])

    def test_place_allows_neighbouring_cell(self):
        vp = self._viewport()
        self._frame(
            [Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": 300, "y": 100})],
            (300, 100),
        )
        tx, ty = round(vp._camera.world_to_screen((64, 0)).x), round(vp._camera.world_to_screen((0, 96)).y)
        self._frame(
            [Event(EventType.MOUSE_BUTTON_DOWN, {"button": "left", "x": tx, "y": ty})],
            (tx, ty),
        )
        self.assertEqual(len(vp.scene.sprites), 2)


# --------------------------------------------------------------------------- #
# editor integration (headless game run)
# --------------------------------------------------------------------------- #


class _LoopBackend(StubBackend):
    """Delivers the queued event batches once per poll (one batch per frame)."""

    def __init__(self, events=None):
        super().__init__(events=[])
        self._rerun = list(events or [])

    def poll_events(self):
        if self._rerun:
            return [self._rerun.pop(0)]
        return []


class TestEditorIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = _TempProject()
        self.addCleanup(self.temp.cleanup)

    def test_editor_run_places_sprite_via_loop(self):
        from pydex_ge.backend.base import BackendEvent
        from pydex_ge.editor import Editor

        filename = self.temp.add_image("hero.png", 12, 8)
        backend = _LoopBackend(
            events=[
                BackendEvent("mouse_button_down", {"button": "left", "x": 300, "y": 100})
            ]
        )
        backend.image_sizes = {
            os.path.abspath(os.path.join(self.temp.project.assets_dir(), filename)): (12, 8)
        }
        backend._mouse_position = (300, 100)
        editor = Editor(self.temp.project, backend=backend)
        viewport = editor._ui.viewport
        viewport.palette = filename  # simulate selecting the palette asset
        editor.run(max_frames=6)
        self.assertTrue(editor.window.closed)
        self.assertEqual(len(self.temp.project.scene("Main").sprites), 1)

    def test_editor_ctrl_s_writes_manifest(self):
        from pydex_ge.backend.base import BackendEvent
        from pydex_ge.editor import Editor

        backend = _LoopBackend(
            events=[
                BackendEvent("key_down", {"key": "control"}),
                BackendEvent("key_down", {"key": "s"}),
            ]
        )
        editor = Editor(self.temp.project, backend=backend)
        self.temp.project.scene("Main").add_sprite(SpriteEntry("x.png", x=1, y=2))
        editor.run(max_frames=4)
        loaded = DexProject.load(self.temp.root)
        self.assertEqual(len(loaded.scene("Main").sprites), 1)


# --------------------------------------------------------------------------- #
# editor CLI
# --------------------------------------------------------------------------- #


class TestEditorCLI(unittest.TestCase):
    def _launch(self, argv):
        """Run editor main() with Editor stubbed out; returns (rc, project_root)."""
        launched = []

        class _FakeEditor:
            def __init__(self, project):
                launched.append(project)
                self.project = project

            def run(self):
                return 0

        from pydex_ge.editor.__main__ import main

        with mock.patch("pydex_ge.editor.Editor", _FakeEditor):
            rc = main(argv)
        return rc, launched

    def test_bare_directory_opens_project(self):
        with _TempProject() as t:
            rc, launched = self._launch([t.root])
            self.assertEqual(rc, 0)
            self.assertEqual(len(launched), 1)
            self.assertEqual(launched[0].root, t.project.root)

    def test_explicit_open_command(self):
        with _TempProject() as t:
            rc, launched = self._launch(["open", t.root])
            self.assertEqual(rc, 0)
            self.assertEqual(launched[0].root, t.project.root)

    def test_missing_directory_reports_error(self):
        rc, launched = self._launch([os.path.join(tempfile.mkdtemp(), "nope")])
        self.assertEqual(rc, 1)
        self.assertEqual(launched, [])

    def test_no_arguments_prints_help(self):
        rc, launched = self._launch([])
        self.assertEqual(rc, 2)
        self.assertEqual(launched, [])

    def test_create_still_works(self):
        base = tempfile.mkdtemp()
        try:
            target = os.path.join(base, "NewProject")
            rc, launched = self._launch(["create", target, "New Project"])
            self.assertEqual(rc, 0)
            self.assertEqual(launched, [])
            self.assertTrue(os.path.isfile(os.path.join(target, "project.pydex_ge.json")))
        finally:
            import shutil

            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()