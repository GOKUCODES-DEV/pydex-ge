"""Tests for pydex_ge.dexview (static HTML snapshot renderer)."""

from __future__ import annotations

import base64
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydex_ge.dexview import (
    build_html,
    escape,
    image_data_uris,
    main,
    make_server,
    render_project,
)
from pydex_ge.editor.project import DexProject, SpriteEntry
from pydex_ge.pixels import encode_png


def _pixel_hero_png() -> bytes:
    row = bytes.fromhex("FF0000FF 00FF00FF 0000FFFF")
    return encode_png(3, 2, [row, row])


def _make_project(root: str) -> str:
    project = DexProject.create_empty(root=root, name="Demo")
    project.name = "Great Game"
    source = os.path.join(root, "hero.png")
    with open(source, "wb") as handle:
        handle.write(_pixel_hero_png())
    entry = project.import_asset(source)
    scene = project.add_scene("Level 1")
    scene.width, scene.height, scene.grid = 320, 240, 16
    scene.add_sprite(
        SpriteEntry(entry.filename, x=10, y=20, layer=0, scale=2.0)
    )
    scene.add_sprite(
        SpriteEntry(entry.filename, x=-5, y=-8, layer=1, flip_h=True, visible=True)
    )
    project.save()
    return project.manifest_path


class DexViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self) -> None:
        # Windows can briefly hold the files just served by the HTTP server
        # (e.g. antivirus scanning); retry instead of failing on a race.
        for _ in range(50):
            try:
                self._tmp.cleanup()
                return
            except PermissionError:
                time.sleep(0.1)

    def test_render_project_writes_files(self) -> None:
        manifest = _make_project(self.root)
        index = render_project(os.path.dirname(manifest), out_dir=self.root)
        self.assertEqual(index, os.path.join(self.root, "index.html"))
        with open(index, encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("Great_Game", content)
        self.assertIn("Level_1", content)
        self.assertIn("hero.png", content)
        self.assertIn("data:image/png;base64,", content)
        self.assertIn("900", content)

    def test_render_default_out_dir(self) -> None:
        manifest = _make_project(self.root)
        index = render_project(os.path.dirname(manifest))
        self.assertEqual(index, os.path.join(os.path.dirname(manifest), ".dexview", "index.html"))
        self.assertTrue(os.path.isfile(index))

    def test_image_data_uris_rasterizes_assets(self) -> None:
        manifest = _make_project(self.root)
        project = DexProject.load(os.path.dirname(manifest))
        uris = image_data_uris(project)
        self.assertEqual(len(uris), 1)
        uri = uris["hero.png"]
        self.assertTrue(uri.startswith("data:image/png;base64,"))
        raw = base64.b64decode(uri.split(",", 1)[1])
        self.assertTrue(raw.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_escape_prevents_markup_injection(self) -> None:
        self.assertEqual(
            escape("<script>alert('x') & \"y\"</script>"),
            "&lt;script&gt;alert('x') &amp; &quot;y&quot;&lt;/script&gt;",
        )
        manifest = _make_project(self.root)
        project = DexProject.load(os.path.dirname(manifest))
        project.name = "A & B"
        project.save()
        html = build_html(DexProject.load(os.path.dirname(manifest)))
        self.assertIn("A___B", html)
        self.assertNotIn("<script>alert", html)

    def test_empty_project_renders(self) -> None:
        project = DexProject.create_empty(root=self.root, name="Blank")
        project.scenes.clear()
        project.save()
        html = build_html(project)
        self.assertIn("Blank", html)
        self.assertIn("No image assets", html)
        self.assertIn("0 scenes", html)
        self.assertIn("(empty scene)", html)

    def test_cli_main_writes_output(self) -> None:
        manifest = _make_project(self.root)
        out = os.path.join(self.root, "site")
        code = main([os.path.dirname(manifest), "--out", out])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isfile(os.path.join(out, "index.html")))

    def test_make_server_serves_index(self) -> None:
        import http.client
        import threading

        manifest = _make_project(self.root)
        out = os.path.join(self.root, "site")
        render_project(os.path.dirname(manifest), out_dir=out)

        server = make_server(out, 0)
        thread = threading.Thread(target=server.handle_request)
        thread.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            conn.request("GET", "/index.html")
            response = conn.getresponse()
            body = response.read()
            conn.close()
            self.assertEqual(response.status, 200)
            self.assertIn(b"Great_Game", body)
        finally:
            thread.join(5)
            server.server_close()
            self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()