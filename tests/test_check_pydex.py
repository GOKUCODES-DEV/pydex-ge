"""Tests for the PYDEX-specific API checks (PYDEX001/002, CONFIG001, SCENE001).

The spec (``syntax-test.txt``) names this file explicitly.  It covers unknown
PYDEX names (bare and ``pydex_ge.``-prefixed), bad constructor values, unknown
attributes on PYDEX instances, and non-Scene ``SceneManager.push`` calls.
"""

import os
import tempfile
import unittest

import pydex_ge


class _ProjectDir(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._dir = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, name: str, text: str) -> str:
        path = os.path.join(self._dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path


class TestUnknownPydexNames(_ProjectDir):
    def test_bare_typo(self):
        path = self._write("main.py", "camera = Camra2D()\n")
        results = pydex_ge.check_pydex(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "PYDEX001")
        self.assertIn("Camera2D", results[0].message)

    def test_prefixed_typo(self):
        path = self._write("main.py", "camera = pydex_ge.Camra2D()\n")
        results = pydex_ge.check_pydex(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "PYDEX001")
        self.assertIn("Camera2D", results[0].message)

    def test_valid_pydex_names_pass(self):
        path = self._write(
            "main.py",
            "import pydex_ge\n"
            'g = pydex_ge.Game("x", 640, 480)\n'
            "c = pydex_ge.Camera2D()\n"
            "s = pydex_ge.Sprite()\n",
        )
        self.assertEqual(pydex_ge.check_pydex(path), [])


class TestConstructorConfig(_ProjectDir):
    def test_camera_fov_string(self):
        path = self._write("cam.py", "c = pydex_ge.Camera3D(fov='90')\n")
        results = pydex_ge.check_pydex(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "CONFIG001")
        self.assertEqual(results[0].category, "configuration")
        self.assertIn("fov", results[0].message)
        self.assertEqual(results[0].lineno, 1)

    def test_camera_fov_string_via_bare_name(self):
        path = self._write("cam.py", "c = Camera3D(fov='90')\n")
        results = pydex_ge.check_pydex(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "CONFIG001")

    def test_camera_zoom_bad(self):
        path = self._write("cam.py", "c = Camera3D(zoom=-1)\n")
        results = pydex_ge.check_pydex(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "CONFIG001")

    def test_game_fps_string(self):
        path = self._write("game.py", "g = pydex_ge.Game(fps='60')\n")
        results = pydex_ge.check_pydex(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "CONFIG001")
        self.assertIn("fps", results[0].message)

    def test_good_fps_passes(self):
        path = self._write("game.py", "g = pydex_ge.Game(fps=60)\n")
        self.assertEqual(pydex_ge.check_pydex(path), [])

    def test_good_fov_passes(self):
        path = self._write("cam.py", "c = pydex_ge.Camera3D(fov=75)\n")
        self.assertEqual(pydex_ge.check_pydex(path), [])


class TestUnknownAttributes(_ProjectDir):
    def test_bad_attribute_on_sprite_class(self):
        path = self._write("main.py", "Sprite.move(10, 10)\n")
        results = pydex_ge.check_pydex(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "PYDEX002")
        self.assertIn("move", results[0].message)

    def test_known_attribute_passes(self):
        path = self._write("main.py", "s = Sprite()\ns.draw()\n")
        self.assertEqual(pydex_ge.check_pydex(path), [])

    def test_instance_attribute_not_flagged(self):
        # Instances may have attributes set per-object (e.g. self.x in
        # __init__); the checker does not guess at them.
        path = self._write("main.py", "s = Sprite()\ns.x = 5\nprint(s.x)\n")
        self.assertEqual(pydex_ge.check_pydex(path), [])

    def test_unrelated_object_not_checked(self):
        path = self._write("main.py", "thing = object()\nthing.move()\n")
        self.assertEqual(pydex_ge.check_pydex(path), [])


class TestScenePush(_ProjectDir):
    def test_push_string_literal(self):
        path = self._write("main.py", "game = Game()\ngame.scenes.push('Menu')\n")
        results = pydex_ge.check_pydex(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "SCENE001")
        self.assertEqual(results[0].category, "scene")
        self.assertIn("Menu", results[0].message)

    def test_push_scene_instance_passes(self):
        path = self._write("main.py", "game = Game()\ngame.scenes.push(Menu())\n")
        results = pydex_ge.check_pydex(path)
        self.assertNotIn("SCENE001", [r.code for r in results])

    def test_other_push_not_flagged(self):
        path = self._write("main.py", "items = []\nitems.push('x')\n")
        self.assertNotIn("SCENE001", [r.code for r in pydex_ge.check_pydex(path)])


class TestModesAreIndependent(_ProjectDir):
    def test_asset_mode_ignores_api_errors(self):
        self._write("main.py", "c = Camra2D()\n")
        self.assertEqual(pydex_ge.check_assets(self._dir), [])

    def test_python_mode_ignores_asset_errors(self):
        self._write("main.py", 's = Sprite.from_file("gone.png")\n')
        self.assertEqual(pydex_ge.check_python(self._dir), [])


if __name__ == "__main__":
    unittest.main()