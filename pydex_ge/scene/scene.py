"""The :class:`Scene`: a lightweight container for game objects.

A scene holds objects and forwards lifecycle calls to them.  Objects are
plain Python objects; the only requirement is the method you want called:

* objects with an ``update(dt)`` method are updated each frame,
* objects with a ``draw(renderer)`` method are drawn each frame,
* objects with a ``handle_event(event)`` method receive engine events.

Existing PYDEX classes already fit: :class:`~pydex_ge.graphics.sprite.Sprite`
provides ``update`` and ``draw``, :class:`~pydex_ge.graphics.label.Label` and
:class:`~pydex_ge.graphics.text.Text` provide ``draw``, and
:class:`~pydex_ge.physics.body.Body` provides ``update``.  Nothing needs to
inherit from a heavy base class.

A scene can have an active :class:`~pydex_ge.core.camera.Camera`.  When
``camera`` is set, world-space objects (sprites) are drawn through it while
screen-space UI (labels, text) stays on the screen, following the existing
renderer behaviour.  A scene can also carry an optional
:class:`~pydex_ge.core.camera3d.Camera3D`; when ``camera3d`` is set, objects
are drawn through the renderer's 3D path so 3D meshes are projected, lit
and depth-sorted.  A scene uses at most one of the two cameras.
"""

from __future__ import annotations

from collections.abc import Iterator


class Scene:
    """A collection of objects with an optional camera.

    Subclass it and override :meth:`on_enter`, :meth:`on_exit`, :meth:`update`,
    or :meth:`handle_event` to add behaviour.  Call ``super().update(dt)``
    (or ``super().handle_event(event)``) to keep the automatic object
    forwarding.

    Parameters
    ----------
    camera:
        An optional :class:`~pydex_ge.core.camera.Camera` the scene draws
        through.  ``None`` draws objects in raw screen coordinates.
    camera3d:
        An optional :class:`~pydex_ge.core.camera3d.Camera3D` the scene draws
        3D objects through.  When set, object draws happen inside
        ``renderer.begin_3d``/``end_3d`` instead of the 2D camera path.
    light:
        An optional :class:`~pydex_ge.graphics.light.DirectionalLight` used to
        light 3D objects when the scene draws through ``camera3d``.  A scene
        uses at most one of ``camera`` and ``camera3d``; when both are set
        the 2D ``camera`` takes precedence.
    """

    def __init__(self, *, camera=None, camera3d=None, light=None) -> None:
        self.camera = camera
        self.camera3d = camera3d
        self.light = light
        self._objects: list[object] = []
        self.game = None
        self.manager = None

    # -- lifecycle hooks ------------------------------------------------

    def on_enter(self) -> None:
        """Called when the scene becomes the current scene.  Override to set up."""

    def on_exit(self) -> None:
        """Called when the scene stops being current.  Override to clean up."""

    # -- per-frame forwarding -------------------------------------------

    def update(self, dt: float) -> None:
        """Update every object that provides an ``update(dt)`` method."""
        for obj in self._objects:
            update = getattr(obj, "update", None)
            if callable(update):
                update(dt)

    def draw(self, renderer) -> None:
        """Draw every object that provides a ``draw(renderer)`` method.

        When :attr:`camera` is set, objects are drawn between
        ``camera.begin(renderer)`` and ``camera.end()`` so world-space
        sprites are transformed; labels and text stay screen-space.  When
        :attr:`camera3d` is set instead, objects are drawn between
        ``renderer.begin_3d(camera3d)`` and ``renderer.end_3d()`` so 3D
        meshes are projected through the 3D camera.  The 2D ``camera`` takes
        precedence when both are set.
        """
        if self.camera is not None:
            self.camera.begin(renderer)
            try:
                self._draw_objects(renderer)
            finally:
                self.camera.end()
        elif self.camera3d is not None:
            renderer.begin_3d(self.camera3d, self.light)
            try:
                self._draw_objects(renderer)
            finally:
                renderer.end_3d()
        else:
            self._draw_objects(renderer)

    def _draw_objects(self, renderer) -> None:
        # Stable z-order: lower ``z`` objects draw first (behind).  Objects
        # without a ``z`` attribute default to 0, and equal z-values keep
        # their insertion order, so existing scenes render unchanged.
        for obj in sorted(
            self._objects, key=lambda o: getattr(o, "z", 0)
        ):
            draw = getattr(obj, "draw", None)
            if callable(draw):
                draw(renderer)

    def handle_event(self, event) -> None:
        """Forward an engine event to every object with a ``handle_event`` method."""
        for obj in self._objects:
            handler = getattr(obj, "handle_event", None)
            if callable(handler):
                handler(event)

    # -- object management ----------------------------------------------

    def add(self, obj) -> object:
        """Add ``obj`` to the scene and return it (so calls can be chained)."""
        self._objects.append(obj)
        return obj

    def remove(self, obj) -> bool:
        """Remove ``obj`` from the scene.

        Returns ``True`` if it was present, ``False`` if it was not already
        in the scene (removing something twice is harmless).
        """
        try:
            self._objects.remove(obj)
        except ValueError:
            return False
        return True

    def clear(self) -> None:
        """Remove every object from the scene.

        The scene does not destroy or free the objects; it only drops its
        references to them.
        """
        self._objects.clear()

    def __iter__(self) -> Iterator[object]:
        """Iterate over the objects in insertion order."""
        return iter(self._objects)

    def __len__(self) -> int:
        """The number of objects in the scene."""
        return len(self._objects)

    def __contains__(self, obj) -> bool:
        """True when ``obj`` is in the scene."""
        return obj in self._objects

    def __repr__(self) -> str:
        return f"Scene(objects={len(self._objects)})"


__all__ = ["Scene"]
