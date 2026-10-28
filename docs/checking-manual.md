# PYDEX Project Checking System — Developer Manual

This manual explains how the static project checker in `pydex_ge/check/` works,
how to run it, how to read its output, and how to extend it.  It is written
for developers (and future maintainers), not for beginner users.

---

## 1. What it is

`pydex_ge/check/` is a **static, headless, safe, dependency-free** toolkit for
finding problems in a PYDEX project.

- **Static** — it parses and compiles source code only.  It never imports
  project modules and never opens a window.
- **Headless** — no renderer/backend is constructed.
- **Safe** — you can run it over a project *before* running that project.
- **Dependency-free** — only the Python standard library is used.

The behaviour is specified in `syntax-test.txt` ("PYDEX Syntax & Project
Checking System 2.0").

---

## 2. Public API

Everything is exposed both as `pydex_ge.check.<name>` and as `pydex_ge.<name>`
(for the most commonly used functions).

| Function            | What it checks |
|---------------------|----------------|
| `check_file(path)`  | One `.py`/`.pyw` file, every check. Returns a plain `list[CheckResult]`. |
| `check_python(p)`   | Syntax, imports, undefined names. File or folder. |
| `check_assets(p)`   | Missing / dynamic / duplicate asset paths. File or folder. |
| `check_pydex(p)`    | PYDEX API names, configuration values, scene mistakes. File or folder. |
| `check_all(p)`      | Every check. File or folder. |
| `check_project(p)`  | Default entry point; `p=None` means the current directory. Same as `check_all` over a folder. |
| `format_error(e)`   | Renders an exception as one `file:line: ErrorType: message` line. |
| `format_result(r)`  | Renders a single `CheckResult` with source context and a caret. |

### Mode separation

`check_project` defaults to **all** checks.  The narrower entry points let
users (and CI) scan only one family.  Which categories run per mode is
defined by the category constants in `check/__init__.py`:

```
_ALL_CATEGORIES    = syntax import name pydex_ge configuration scene asset project
_PYTHON_CATEGORIES = syntax import name project
_ASSET_CATEGORIES  = asset project
_PYDEX_CATEGORIES  = pydex_ge configuration scene syntax name project
```

A mode may run a *broader* analyzer than its category set (for example
`check_pydex` runs name analysis so it can find PYDEX typos), but the
final results are filtered so only results whose `category` belongs to the
mode are returned.  This keeps modes independent (see
`CheckModesAreIndependent` in `tests/test_check_pydex.py`).

---

## 3. Result and report objects

### `CheckResult`

A frozen dataclass (`pydex_ge/check/_models.py`) with positional fields in a
fixed order to stay backward-compatible with Part 11:

```python
CheckResult(path, lineno, column, message, *, severity, code, category)
```

- `lineno` / `column` are 1-based (matching Python's own reporting) and may
  be `None` when a location does not apply.
- `severity` is `"error"`, `"warning"`, or `"info"`.
- `code` is the stable error code (see §7).
- `category` is one of the `CATEGORY_*` constants.

`str(result)` gives `path:line:column: [CODE] message`.

### `CheckReport`

A `list` subclass with extra convenience views:

- `report.errors` / `report.warnings` / `report.infos` — filtered by severity.
- `report.ok` — `True` when there are no errors (warnings/info allowed).
- `report.root` — the checked directory or file.
- `print(report)` — formatted human-readable report.
- `report.to_dict()` — JSON-friendly `{"ok", "errors", "warnings", "infos"}`.

Being a `list` subclass means old loop/`len`/indexing code keeps working.

---

## 4. How a check is processed

```
target (file or folder)
   │
   v
_resolve_target()          → absolute path, existence check
   │
   ├── single file  → _check_python_file()   (project_root = its directory)
   └── folder       → _walk_dir_with_categories()
                          │
                          └── iter_python_files()  (skips hidden/vendor dirs,
                                                    honours .pydexignore)
                                │
                                v
                         _read_source_bytes()      (UTF-8, BOM aware)
                                │
                                v
                         _analyze_source()          (chooses analyzers by category)
                                │
                                v
                         per-analyzer results → CheckReport
```

`_analyze_source` in `check/__init__.py`:

1. If the mode includes `syntax`, run `check_syntax` first.  A syntax error
   stops everything else (the file is unparseable).
2. Otherwise parse the source with `ast.parse` only as far as the mode
   needs it.
3. Run the category-appropriate analyzers from `check/_analysis.py`:
   - `check_syntax`      → `SYNTAX001`
   - `check_imports`     → `IMPORT001`
   - `check_names`       → `NAME001`, `PYDEX001`
   - `check_pydex_usage` → `PYDEX001`, `PYDEX002`, `CONFIG001`, `SCENE001`
   - `check_asset_paths` → `ASSET001`, `ASSET002`
   - duplicate-asset pass → `ASSET003`
   - unreadable file     → `PROJECT001`

4. Filter results so only results whose `category` is in the mode's category
   set survive (keeps modes independent).

---

## 5. File discovery and `.pydexignore`

`pydex_ge/check/_scan.py` walks folders recursively:

- Python files: `.py` and `.pyw`.
- Asset files: images, fonts, sounds, music, and sprite sheets
  (`png`, `bmp`, `jpg`, `jpeg`, `gif`, `ttf`, `otf`, `wav`, `ogg`, `mp3`,
  ...).
- Skipped directories: hidden directories (leading `.`), `__pycache__`,
  `node_modules`, `venv`, `.venv`, `site-packages`, and other vendor/cache
  folders.
- A `.pydexignore` file next to the project root may list directory names
  (and relative paths) to skip.  This maps to `PROJECT001` in the spec —
  the checker ignores the listed paths rather than failing.

Directories are discovered deterministically with `os.walk` in sorted
order so scan output is stable.

---

## 6. The analyzers in detail

### `check_syntax` — `SYNTAX001`
Compiles the decoded source.  `SyntaxError` reports `lineno`/`offset`
(1-based).  The message is the bare `exc.msg` (a Part 11 test asserts
`message == "invalid syntax"`, so do not decorate it here).  A `ValueError`
(null byte, etc.) is also reported as `SYNTAX001` without a location.

### `check_imports` — `IMPORT001`
Flags `from pydex_ge import <name>` (or `import pydex_ge.<sub>`) where the name
does not exist in the registry.  The registry is built by
`pydex_ge/check/_api.py`:

- top-level names come from `pydex_ge.__all__` (fall back to a hardcoded list);
- submodules are discovered by listing the `pydex_ge` package directory.

Suggestions use `difflib.get_close_matches` (`_nearest`) with a
conservative cutoff, so obvious typos like `Spritee → Sprite` get a
“Did you mean …?” hint.

### `check_names` — `NAME001`, `PYDEX001`
A deliberately **conservative** undefined-name pass.  `_collect_definitions`
walks the AST and records every name that is imported or assigned anywhere
in the file, so branch-local assignments never trigger a false positive.
Only clearly undefined `Load` names are reported, and only when they are
not builtins, not dunder names, and there is no `from x import *` anywhere
(star imports disable this check entirely).

If an undefined name is a near-miss of a real PYDEX API name
(`Camra2D → Camera2D`), it is upgraded from a `NAME001` warning to a
`PYDEX001` error with a suggestion.

### `check_pydex_usage` — `PYDEX001/002`, `CONFIG001`, `SCENE001`
Four static checks:

1. `pydex_ge.<Unknown>()` — a dotted call whose name is not in the public API
   → `PYDEX001` with a suggestion.
2. Class-level attribute calls — an attribute access on a known PYDEX
   *class* name used directly (e.g. `Sprite.move(...)`) where the attribute
   is not a public member → `PYDEX002`.  Per-instance checks are
   deliberately avoided: instance attributes set in `__init__` (like
   `self.x`) and subclass members make them unreliable, and the spec says
   to report nothing when unsure.
3. Constructor arguments — `_check_constructor` validates obvious literal
   mistakes: `Camera3D(fov="90")`, `Camera3D(zoom=-1)`, `Game(fps="high")`
   → `CONFIG001`.  Negative literals are handled because `-1` parses as
   `ast.UnaryOp`, not `ast.Constant`.
4. Scene pushes — `SceneManager.push("Menu")` with a string literal first
   argument → `SCENE001` (a Scene instance is the correct argument).

`_class_members` lazily imports the real `pydex_ge` to learn public members —
an enforced best-effort table so the checker does not drift from the API.

### `check_asset_paths` — `ASSET001`, `ASSET002`
Matches asset-loading call shapes (`_ASSET_CALLS`):

- classes used directly: `Image(...)`, `Sprite(...)`, `SpriteSheet(...)`,
  `Font(...)`, `Sound(...)`, `Music(...)`;
- `Sprite.from_file(...)`, `Assets.image/font/sprite_sheet(...)`,
  `Audio.load_sound/load_music(...)`;
- **both capitalised class names and lowercased instance names**
  (`Assets.image` and `assets.image`) are recognised.

A literal path that can be resolved to an existing file is fine
(`_find_asset` checks the file's directory, the project root, and `cwd`,
with `expanduser`/`expandvars`); a missing literal is `ASSET001`; a
variable path is `ASSET002` (`info` severity — dynamic, cannot be verified).

`ASSET003` (duplicate basename warning) runs over the whole folder.

---

## 7. Error codes

The canonical list lives in `ERROR_CODES` in `check/__init__.py`:

| Code        | Severity  | Category        | Meaning |
|-------------|-----------|-----------------|---------|
| `SYNTAX001` | error     | syntax          | Invalid syntax / indentation / encoding. |
| `IMPORT001` | error     | import          | Import from `pydex_ge` of a name that does not exist. |
| `NAME001`   | warning   | name            | Name is read but looks undefined. |
| `PYDEX001`  | error     | pydex_ge           | Unknown PYDEX name (with a likely typo suggestion). |
| `PYDEX002`  | error     | pydex_ge           | Attribute used directly on a PYDEX class that is not a public member. |
| `CONFIG001` | error     | configuration   | Clearly-invalid PYDEX configuration value. |
| `SCENE001`  | error     | scene           | `SceneManager.push()` given a non-Scene literal. |
| `ASSET001`  | error     | asset           | Literal asset path does not exist. |
| `ASSET002`  | info      | asset           | Dynamic asset path cannot be verified statically. |
| `ASSET003`  | warning   | asset           | Duplicate asset files with the same name. |
| `PROJECT001`| warning   | project         | A project file could not be read. |

---

## 8. Rendering

`pydex_ge/check/_format.py`:

- `render_result` emits the hood-style block the spec asks for:

  ```
  ERROR PYDEX001
  main.py:24:13

  Unknown PYDEX name: Camra2D

      camera = Camra2D()
               ^^^^^^^^
  Did you mean: Camera2D?

  ```
  It reads the source file (when readable) and draws a caret under the
  offending token.  For `PYDEX001`, a trailing “Did you mean …?” is
  pulled out of the message into the finished position.

- `format_report` renders a full report with `ERRORS` / `WARNINGS` / `INFO`
  sections and a summary block.  `CheckReport.__str__` delegates here.

---

## 9. CLI

`pydex_ge/check/__main__.py` runs with `python -m pydex_ge.check`.

```
usage: pydex_ge.check [path] [mode] [output options]

path      file or folder (default: current directory)
modes     --python | --assets | --pydex_ge | --all (default --all)
output    --quiet (summary only) | --warnings | --json
```

- `_build_report` routes to the matching `check_*` function based on the
  selected mode string (keep the mode string and the function name in
  sync here).
- The default mode is `--all`.
- `--json` prints `report.to_dict()` plus a `root` key.
- Exit code: `0` no errors, `1` errors found, `2` bad path.

---

## 10. Extending the checker

1. Add the new analyzer in `pydex_ge/check/_analysis.py` (or a new `_*.py`
   module).  Each analyzer takes `(path, source, tree)` and returns a
   `list[CheckResult]` built via the private `_result(...)` helper so code,
   category, and severity are always set.
2. Register the new error code + meaning in `ERROR_CODES`
   (`check/__init__.py`) and, if it is a new category, add a
   `CATEGORY_*` constant in `_models.py` and put it in the mode sets.
3. Wire it into `_analyze_source` behind the correct category check.
4. Add a `tests/test_check_*.py` file covering good and bad cases.
5. Update the CLI only if the new check deserves a mode flag.

Rules:

- Never execute user code; the checker is static only.
- Never add dependencies; standard library only.
- Keep `check_file`'s contract (a plain `list`, empty = valid) and
  `CheckResult`'s field order stable — Part 11 tests depend on them.
- Be conservative: when you cannot tell, report nothing.
- Keep the `examples/manual_check_test.py --check` demo self-checking so
  manual verification never goes stale.

---

## 11. Testing and verification

```text
python -m unittest discover -s tests -v        # full suite
python -m compileall pydex_ge tests examples      # byte-compile everything
python examples/manual_check_test.py --check   # manual checker demo
python -m pydex_ge.check .                        # scan the PYDEX repo itself
```

The checker tests split into:

- `tests/test_check.py`              — Part 11 legacy contracts (backward compatibility).
- `tests/test_check_syntax_imports.py` — `SYNTAX001` / `IMPORT001` / `NAME001` / `PYDEX001`.
- `tests/test_check_assets.py`       — `ASSET001` / `ASSET002` / `ASSET003`.
- `tests/test_check_pydex.py`        — `PYDEX001/002`, `CONFIG001`, `SCENE001`, mode independence.
- `tests/test_check_report.py`       — `CheckReport`, `to_dict`, rendering, CLI.