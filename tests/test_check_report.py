"""Tests for the report object, JSON output, rendering, and CLI.

Covers :class:`CheckReport` behaviour (list-like, ``.errors``/``.warnings``/
``.infos``/``.ok``, ``print()``), ``to_dict()``, mode entry points, and the
``python -m pydex_ge.check`` command line.
"""

import json
import os
import subprocess
import sys
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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path


class TestCheckReport(_ProjectDir):
    def test_report_acts_like_a_list(self):
        report = pydex_ge.check_all(self._dir)
        self.assertIsInstance(report, pydex_ge.CheckReport)
        self.assertIsInstance(report, list)
        self.assertEqual(len(report), len(list(report)))

    def test_severity_views(self):
        self._write("err.py", "def broken(:\n    pass\n")
        self._write("warn.py", "print(total)\n")
        report = pydex_ge.check_all(self._dir)
        self.assertTrue(report.errors)
        self.assertTrue(report.warnings)
        for item in report.errors:
            self.assertEqual(item.severity, "error")
        for item in report.warnings:
            self.assertEqual(item.severity, "warning")

    def test_ok_false_when_errors(self):
        self._write("bad.py", "def broken(:\n    pass\n")
        self.assertFalse(pydex_ge.check_all(self._dir).ok)

    def test_ok_true_when_only_warnings(self):
        self._write("warn.py", "print(total)\n")
        self.assertTrue(pydex_ge.check_all(self._dir).ok)

    def test_ok_true_when_clean(self):
        self._write("good.py", "x = 1\n")
        self.assertTrue(pydex_ge.check_all(self._dir).ok)

    def test_print_report_includes_summary(self):
        self._write("bad.py", "def broken(:\n    pass\n")
        rendered = str(pydex_ge.check_project(self._dir))
        self.assertIn("SUMMARY", rendered)
        self.assertIn("FAILED", rendered)

    def test_to_dict_structure(self):
        self._write("bad.py", "def broken(:\n    pass\n")
        payload = pydex_ge.check_all(self._dir).to_dict()
        self.assertIsInstance(payload["errors"], list)
        self.assertIsInstance(payload["warnings"], list)
        self.assertEqual(len(payload["errors"]), 1)
        item = payload["errors"][0]
        for key in ("path", "line", "column", "severity", "category", "code",
                    "message"):
            self.assertIn(key, item)

    def test_single_file_report_root(self):
        path = self._write("bad.py", "def broken(:\n    pass\n")
        report = pydex_ge.check_all(path)
        self.assertEqual(report.root, os.path.abspath(path))


class TestModeEntryPoints(_ProjectDir):
    def test_check_python_and_check_all(self):
        self._write("sub/a.py", "def broken(:\n    pass\n")
        self._write("sub/b.py", "x = 1\n")
        self.assertEqual(len(pydex_ge.check_python(self._dir)), 1)
        self.assertEqual(len(pydex_ge.check_all(self._dir)), 1)

    def test_clean_project_reports_empty(self):
        self._write("main.py", "x = 1\n")
        self.assertEqual(pydex_ge.check_project(self._dir), [])

    def test_check_file_still_returns_list(self):
        path = self._write("bad.py", "def broken(:\n    pass\n")
        results = pydex_ge.check_file(path)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)


class TestFormatResult(_ProjectDir):
    def test_format_result_renders_code_and_location(self):
        path = self._write("bad.py", "def broken(:\n    pass\n")
        result = pydex_ge.check_file(path)[0]
        rendered = pydex_ge.format_result(result)
        self.assertIn("SYNTAX001", rendered)
        self.assertIn(os.path.abspath(path), rendered)
        self.assertIn("invalid syntax", rendered)


class TestCli(unittest.TestCase):
    def test_cli_json_exit_code(self):
        dirname = tempfile.mkdtemp()
        self.addCleanup(lambda: os.path.exists(dirname) or None)
        with open(os.path.join(dirname, "main.py"), "w", encoding="utf-8") as f:
            f.write("import pydex_ge\nx = Spritee()\n")
        env = dict(os.environ, PYDEX_BACKEND="null")
        result = subprocess.run(
            [sys.executable, "-m", "pydex_ge.check", "--json", dirname],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
            env=env,
            timeout=120,
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "PYDEX001")

    def test_cli_clean_exit_zero(self):
        dirname = tempfile.mkdtemp()
        self.addCleanup(lambda: os.path.exists(dirname) or None)
        with open(os.path.join(dirname, "main.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        env = dict(os.environ, PYDEX_BACKEND="null")
        result = subprocess.run(
            [sys.executable, "-m", "pydex_ge.check", dirname],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
            env=env,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK", result.stdout)

    def test_cli_missing_path_exit_two(self):
        env = dict(os.environ, PYDEX_BACKEND="null")
        result = subprocess.run(
            [sys.executable, "-m", "pydex_ge.check", "does-not-exist-xyz"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
            env=env,
            timeout=120,
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()