"""Human-readable and JSON rendering for check results and reports.

The format mirrors the design in ``syntax-test.txt``:

::

    ERROR PYDEX001
    main.py:24:13

    Unknown PYDEX name: Camra2D

        player = Camra2D()
                 ^^^^^^^^
    Did you mean: Camera2D?

Source context (the offending line and a caret) is shown when the underlying
file can be read, so a developer can jump straight to the problem.
"""

from __future__ import annotations

from ._models import CATEGORY_SYNTAX, CheckReport, CheckResult

_SEVERITY_LABEL = {"error": "ERROR", "warning": "WARNING", "info": "INFO"}


def _read_source(path: str) -> list[str] | None:
    """The source lines of ``path``, or None when the file is unreadable."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().splitlines()
    except OSError:
        return None


def _caret(line: str, column: int | None, width: int | None) -> str:
    """A caret line under ``line`` pointing at ``column`` (1-based).

    ``width`` lets us underline a whole name (``^^^^``); with no width we draw
    a single ``^``.  The caret never runs past the end of the source line.
    """
    if column is None or column < 1:
        return ""
    count = width or 1
    max_width = max(0, len(line) - (column - 1))
    count = max(1, min(count, max_width + 1 if max_width > 0 else 1))
    return " " * (column - 1) + "^" * count


def _underline_width(result: CheckResult, line: str, column: int) -> int:
    """Best-guess token width at ``column`` for a pretty caret.

    For a syntax error we underline a single character; for a name/import
    error we underline the word running from ``column-1`` onward.
    """
    if result.category == CATEGORY_SYNTAX:
        return 1
    idx = column - 1
    if idx < 0 or idx >= len(line):
        return 1
    if not (line[idx].isalnum() or line[idx] == "_"):
        return 1
    end = idx
    while end < len(line) and (line[end].isalnum() or line[end] == "_"):
        end += 1
    return max(1, end - idx)


def render_result(result: CheckResult) -> str:
    """Format one result with code, location, message, and source context."""
    code = result.code or "GENERIC"
    severity = result.severity
    lines = [f"{_SEVERITY_LABEL.get(severity, severity.upper())} {code}"]

    location = result.path
    if result.lineno is not None:
        location += f":{result.lineno}"
        if result.column is not None:
            location += f":{result.column}"
    lines.append(location)
    lines.append("")

    message = result.message
    hint = None
    if result.code == "PYDEX001" and "Did you mean:" in message:
        body, _, suggestion = message.partition("Did you mean:")
        message = body.strip()
        hint = "Did you mean:" + suggestion
    lines.append(message)

    if result.path and result.lineno is not None:
        source_lines = _read_source(result.path)
        if source_lines and 1 <= result.lineno <= len(source_lines):
            line = source_lines[result.lineno - 1]
            width = _underline_width(result, line, result.column or 1)
            lines.append("")
            lines.append(f"    {line}")
            caret = _caret(line, result.column, width)
            if caret:
                lines.append(f"    {caret}")
    if hint:
        lines.append(hint)
    return "\n".join(lines)


def format_report(report: CheckReport) -> str:
    """Render a full report the way the CLI prints it."""
    parts: list[str] = []

    def section(title: str, items: list[CheckResult]) -> None:
        if not items:
            return
        parts.append(title)
        parts.append("-" * 50)
        for item in items:
            parts.append(render_result(item))
            parts.append("")

    section("ERRORS", report.errors)
    section("WARNINGS", report.warnings)
    section("INFO", report.infos)

    parts.append("SUMMARY")
    parts.append("-" * 50)
    root = report.root or "project"
    parts.append(f"Checked      : {root}")
    parts.append(f"Errors       : {len(report.errors)}")
    parts.append(f"Warnings     : {len(report.warnings)}")
    parts.append(f"Info         : {len(report.infos)}")
    parts.append("")
    if report.ok:
        parts.append("OK - PYDEX check passed (no errors).")
    else:
        parts.append("FAILED - PYDEX check found errors.")
    return "\n".join(parts)


def format_error_from_result(exc) -> str:
    """Best-effort ``file:line:col``-style one-liner for an exception.

    Kept separate from :func:`format_error` so the public API stays stable.
    """
    return f"<unknown>: {type(exc).__name__}: {exc}"


__all__ = ["format_report", "render_result"]