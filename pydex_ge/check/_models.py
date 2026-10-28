"""Result and report objects for the PYDEX project checker.

``CheckResult`` describes one problem (or one piece of information) found in
a project with a stable error code, category, and severity.  ``CheckReport``
is the human/machine-readable output of a multi-file check: it behaves like
the plain list that older PYDEX versions returned, and additionally exposes
``.errors``, ``.warnings``, ``.infos``, and ``.ok`` for convenient use.
"""

from __future__ import annotations

from dataclasses import dataclass

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

CATEGORY_SYNTAX = "syntax"
CATEGORY_IMPORT = "import"
CATEGORY_NAME = "name"
CATEGORY_ASSET = "asset"
CATEGORY_PYDEX = "pydex_ge"
CATEGORY_CONFIGURATION = "configuration"
CATEGORY_SCENE = "scene"
CATEGORY_PROJECT = "project"


@dataclass(frozen=True)
class CheckResult:
    """A single problem (or hint) found by the project checker.

    ``lineno`` and ``column`` are 1-based, matching Python's own reporting.
    Either may be ``None`` when a location does not apply (for example a
    whole-project issue).  ``code`` is a stable error code such as
    ``"SYNTAX001"``, ``category`` one of the ``CATEGORY_*`` constants, and
    ``severity`` one of ``"error"``, ``"warning"``, or ``"info"``.
    """

    path: str
    lineno: int | None
    column: int | None
    message: str
    severity: str = SEVERITY_ERROR
    code: str | None = None
    category: str | None = None

    def __str__(self) -> str:
        location = self.path
        if self.lineno is not None:
            location += f":{self.lineno}"
            if self.column is not None:
                location += f":{self.column}"
        prefix = f"[{self.code}] " if self.code else ""
        return f"{location}: {prefix}{self.message}"

    def as_dict(self) -> dict:
        """A plain dict form used by the JSON output."""
        return {
            "path": self.path,
            "line": self.lineno,
            "column": self.column,
            "severity": self.severity,
            "category": self.category,
            "code": self.code,
            "message": self.message,
        }


class CheckReport(list):
    """The result of checking a file or a whole project.

    Acts as a list of :class:`CheckResult` (so existing ``for``/``len``/
    indexing code keeps working) and adds convenience views:

    * ``report.errors``     -> only error-severity results
    * ``report.warnings``   -> only warning-severity results
    * ``report.infos``      -> only info-severity results
    * ``report.ok``         -> True when there are no errors
    * ``report.root``       -> the directory (or file) that was checked
    * ``print(report)``     -> a formatted, human-readable report
    * ``report.to_dict()``  -> the JSON-friendly form
    """

    def __init__(self, results=(), *, root: str | None = None) -> None:
        super().__init__(results)
        self.root = root

    @property
    def errors(self) -> list[CheckResult]:
        """Only the error-severity results."""
        return [r for r in self if r.severity == SEVERITY_ERROR]

    @property
    def warnings(self) -> list[CheckResult]:
        """Only the warning-severity results."""
        return [r for r in self if r.severity == SEVERITY_WARNING]

    @property
    def infos(self) -> list[CheckResult]:
        """Only the info-severity results."""
        return [r for r in self if r.severity == SEVERITY_INFO]

    @property
    def ok(self) -> bool:
        """True when no errors were found (warnings/info are allowed)."""
        return not self.errors

    def to_dict(self) -> dict:
        """JSON-friendly report: ``{"ok", "errors", "warnings", "infos"}``."""
        return {
            "ok": self.ok,
            "errors": [r.as_dict() for r in self.errors],
            "warnings": [r.as_dict() for r in self.warnings],
            "infos": [r.as_dict() for r in self.infos],
        }

    def __str__(self) -> str:
        from ._format import format_report

        return format_report(self)


__all__ = [
    "CATEGORY_ASSET",
    "CATEGORY_CONFIGURATION",
    "CATEGORY_IMPORT",
    "CATEGORY_NAME",
    "CATEGORY_PROJECT",
    "CATEGORY_PYDEX",
    "CATEGORY_SCENE",
    "CATEGORY_SYNTAX",
    "CheckReport",
    "CheckResult",
    "SEVERITY_ERROR",
    "SEVERITY_INFO",
    "SEVERITY_WARNING",
]