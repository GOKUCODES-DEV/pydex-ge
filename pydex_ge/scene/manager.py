"""The :class:`SceneManager`: a stack of scenes.

Only the top of the stack (the *current* scene) receives ``update``,
``draw``, and events.  Pushing a scene suspends the scene below it without
exiting it; popping resumes the revealed scene without re-entering it.
Replacing swaps the top of the stack and fully transitions between scenes.

Lifecycle summary::

    push(scene)      -> new scene.on_enter()          (covered scene suspended)
    pop()            -> popped scene.on_exit()        (revealed scene resumes)
    replace(scene)   -> old scene.on_exit(), new scene.on_enter()
    clear()          -> each remaining scene.on_exit() (top-down)

A scene never appears twice in the stack, and removed scenes are dropped so
no destroyed/dangling references are left behind.
"""

from __future__ import annotations

from collections.abc import Iterator

from ..exceptions import ConfigurationError
from .scene import Scene


class SceneManager:
    """A stack of :class:`~pydex_ge.scene.scene.Scene` objects.

    Parameters
    ----------
    scenes:
        Optional initial scenes, pushed bottom-up (the last one becomes the
        current scene).  Duplicates are rejected.
    """

    def __init__(self, scenes=()) -> None:
        self._scenes: list[Scene] = []
        for scene in scenes:
            self.push(scene)

    # -- stack access ----------------------------------------------------

    @property
    def current(self) -> Scene | None:
        """The current (top) scene, or ``None`` when the stack is empty."""
        return self._scenes[-1] if self._scenes else None

    def __len__(self) -> int:
        """The number of scenes in the stack."""
        return len(self._scenes)

    def __iter__(self) -> Iterator[Scene]:
        """Iterate over the stack from bottom to top."""
        return iter(self._scenes)

    # -- transitions -----------------------------------------------------

    def push(self, scene: Scene) -> None:
        """Push ``scene`` on top of the stack and enter it.

        The scene currently below it stays in the stack but is suspended
        (it is not exited and keeps its state).  ``scene`` must be a
        :class:`Scene` and must not already be in the stack.
        """
        self._validate_new_scene(scene)
        self._scenes.append(scene)
        scene.manager = self
        scene.on_enter()

    def pop(self) -> Scene | None:
        """Exit and remove the current scene, revealing the one below it.

        The revealed scene resumes without re-entering.  Returns the popped
        scene, or ``None`` when the stack was already empty.
        """
        if not self._scenes:
            return None
        scene = self._scenes.pop()
        scene.on_exit()
        if scene.manager is self:
            scene.manager = None
        return scene

    def replace(self, scene: Scene) -> None:
        """Swap the current scene for ``scene``.

        Exits the old current scene, then enters the new one.  On an empty
        stack this behaves like :meth:`push`.
        """
        self._validate_new_scene(scene)
        self.pop()
        self._scenes.append(scene)
        scene.manager = self
        scene.on_enter()

    def clear(self) -> None:
        """Exit and remove every scene in the stack, top-down."""
        while self._scenes:
            self.pop()

    # -- per-frame forwarding -------------------------------------------

    def update(self, dt: float) -> None:
        """Forward ``update(dt)`` to the current scene, if any."""
        current = self.current
        if current is not None:
            current.update(dt)

    def draw(self, renderer) -> None:
        """Forward ``draw(renderer)`` to the current scene, if any."""
        current = self.current
        if current is not None:
            current.draw(renderer)

    def handle_event(self, event) -> None:
        """Forward an engine event to the current scene, if any."""
        current = self.current
        if current is not None:
            current.handle_event(event)

    # -- helpers ---------------------------------------------------------

    def _validate_new_scene(self, scene: object) -> None:
        if not isinstance(scene, Scene):
            raise ConfigurationError(
                f"SceneManager needs a pydex_ge.Scene, got {scene!r}."
            )
        if scene in self._scenes:
            raise ConfigurationError("That scene is already in the manager.")


__all__ = ["SceneManager"]
