"""Tests for the syntax/import/name checks (SYNTAX001, IMPORT001, NAME001).

Covers the plain-Python half of the checker: invalid syntax, bad imports from
``pydex_ge``, and undefined names with PYDEX near-miss suggestions (PYDEX001).
"""

import os
import tempfile
import unittest

import pydex_ge


class _TempDir(unittest.TestCase):
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


class TestSyntax(_TempDir):
    def test_invalid_syntax_error(self):
        path = self._write("bad.py", "def broken(:\n    pass\n")
        results = pydex_ge.check_file(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "SYNTAX001")
        self.assertEqual(results[0].category, "syntax")
        self.assertEqual(results[0].severity, "error")
        self.assertEqual(results[0].lineno, 1)
        self.assertEqual(results[0].column, 12)
        self.assertEqual(results[0].message, "invalid syntax")

    def test_indentation_error_reported_as_syntax(self):
        path = self._write("indent.py", "if True:\npass\n")
        results = pydex_ge.check_file(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "SYNTAX001")
        self.assertEqual(results[0].lineno, 2)

    def test_syntax_error_stops_other_checks(self):
        # A file that is both unparseable and full of bad names only ever
        # reports the syntax error: the rest cannot be analyzed.
        path = self._write("both.py", "import pydex_ge\nx = Spritee(\n")
        results = pydex_ge.check_file(path)
        codes = [r.code for r in results]
        self.assertIn("SYNTAX001", codes)
        self.assertNotIn("IMPORT001", codes)
        self.assertNotIn("NAME001", codes)


class TestImports(_TempDir):
    def test_unknown_name_from_pydex(self):
        path = self._write("imp.py", "from pydex_ge import Spritee\n")
        results = pydex_ge.check_file(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "IMPORT001")
        self.assertEqual(results[0].category, "import")
        self.assertIn("Spritee", results[0].message)
        self.assertIn("Sprite", results[0].message)

    def test_known_name_from_pydex_is_fine(self):
        path = self._write("imp.py", "from pydex_ge import Sprite\nx = Sprite\n")
        self.assertEqual(pydex_ge.check_file(path), [])

    def test_unknown_submodule(self):
        path = self._write("imp.py", "import pydex_ge.notreal\n")
        results = pydex_ge.check_file(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "IMPORT001")

    def test_known_submodule_is_fine(self):
        path = self._write("imp.py", "import pydex_ge.backend.null\nx = 1\n")
        self.assertEqual(pydex_ge.check_file(path), [])

    def test_star_import_not_flagged(self):
        path = self._write("imp.py", "from pydex_ge import *\nx = Sprite()\n")
        self.assertEqual(pydex_ge.check_file(path), [])


class TestNames(_TempDir):
    def test_undefined_name_warning(self):
        path = self._write("names.py", "x = 1\nprint(total)\n")
        results = pydex_ge.check_file(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "NAME001")
        self.assertEqual(results[0].severity, "warning")
        self.assertEqual(results[0].category, "name")
        self.assertIn("total", results[0].message)

    def test_defined_name_is_fine(self):
        path = self._write("names.py", "total = 5\nprint(total)\n")
        self.assertEqual(pydex_ge.check_file(path), [])

    def test_assignment_anywhere_counts_as_defined(self):
        path = self._write("names.py", "value = 0\nif value > 1:\n    value = 1\nprint(value)\n")
        self.assertEqual(pydex_ge.check_file(path), [])

    def test_builtins_are_known(self):
        path = self._write("names.py", "names = sorted([1, 3, 2])\nprint(len(names))\n")
        self.assertEqual(pydex_ge.check_file(path), [])

    def test_pydex_near_miss_produces_pydex001(self):
        path = self._write("names.py", "camera = Camra2D()\n")
        results = pydex_ge.check_file(path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "PYDEX001")
        self.assertEqual(results[0].category, "pydex_ge")
        self.assertEqual(results[0].severity, "error")
        self.assertIn("Camra2D", results[0].message)
        self.assertIn("Camera2D", results[0].message)
        self.assertEqual(results[0].lineno, 1)

    def test_star_import_disables_name_check(self):
        path = self._write("names.py", "from anything import *\nprint(mystery)\n")
        self.assertEqual(pydex_ge.check_file(path), [])


if __name__ == "__main__":
    unittest.main()