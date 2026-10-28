"""Scene system for PYDEX: lightweight scene objects and a scene stack.

A :class:`Scene` is a small, beginner-friendly container for game objects.
It collects objects (sprites, labels, texts, physics bodies, or any custom
object) and forwards ``update``/``draw``/``handle_event`` to them when they
provide those methods.  A :class:`SceneManager` keeps a stack of scenes and
only ever drives the top (current) scene.

Part 9 keeps this deliberately simple: there is no entity-component system,
no scene nesting, and no serialization.
"""

from .manager import SceneManager
from .scene import Scene

__all__ = ["Scene", "SceneManager"]
