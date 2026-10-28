"""Backend selection for PYDEX.

The selection rules:

* ``PYDEX_BACKEND`` environment variable explicitly picks a backend
  (currently ``sdl2`` or ``null``).  Useful for headless tests/CI.
* Otherwise the SDL2 backend is the **default** for graphical
  applications.  If SDL2 is unavailable it raises a
  :class:`~pydex_ge.exceptions.BackendError` with install instructions —
  it never silently falls back to a backend that renders nothing.
"""

from __future__ import annotations

import os

from ..exceptions import BackendError
from .base import Backend
from .null import NullBackend


def _create_backend(name: str) -> Backend:
    lowered = name.strip().lower()
    if lowered == "null":
        return NullBackend()
    if lowered == "sdl2":
        from .sdl2 import SDL2Backend  # lazy import keeps `import pydex_ge` backend-free

        return SDL2Backend()
    raise BackendError(
        f"Unknown backend {name!r}. Supported backends: 'sdl2', 'null'."
    )


def select_backend(name: str | None = None) -> Backend:
    """Resolve and validate the backend to use.

    Parameters
    ----------
    name:
        Explicit backend name.  Falls back to the ``PYDEX_BACKEND``
        environment variable, then to the SDL2 default.
    """
    if name is None:
        name = os.environ.get("PYDEX_BACKEND") or None
    if name is not None:
        backend = _create_backend(name)
    else:
        backend = _create_backend("sdl2")
    if not backend.is_available():
        raise BackendError(
            f"The {backend.name!r} backend could not be initialized.\n"
            "For SDL2 you can usually fix this with:\n"
            "    pip install pysdl2 pysdl2-dll\n"
            "For headless environments, run with PYDEX_BACKEND=null."
        )
    return backend


__all__ = [
    "Backend",
    "BackendEvent",
    "BackendMusic",
    "BackendRenderer",
    "BackendSound",
    "BackendWindow",
    "NullBackend",
    "select_backend",
]