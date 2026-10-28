"""The :class:`Object3D`: a drawable 3D object with a transform and material.

An object combines a :class:`~pydex_ge.transform.Transform3D`, an optional
:class:`Mesh` and an optional :class:`Material`.  It follows the same
duck-typed interface as the rest of PYDEX: the scene calls ``update(dt)``
and ``draw(renderer)``, and :meth:`draw` hands the mesh to the renderer's
3D path.  This lets 3D objects live inside a normal
:class:`~pydex_ge.scene.Scene` next to 2D sprites without any separate scene
architecture.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from ..math.quaternion import Quaternion
from ..physics.vector3 import Vector3
from ..transform.transform3d import Transform3D
from .material import Material
from .mesh import Mesh


class Object3D:
    """A transform, mesh and material combined into one 3D scene object.

    Parameters
    ----------
    mesh:
        An optional :class:`Mesh` to draw.  Defaults to ``None``.
    material:
        An optional :class:`Material` describing the surface.  Defaults to a
        white opaque material.
    transform:
        An optional :class:`Transform3D`.  A fresh one is created otherwise.
    visible:
        Whether the mesh is drawn.  Defaults to ``True``.
    enabled:
        Whether the object participates in updates.  Defaults to ``True``.
    z:
        An optional depth hint used by the scene to order objects
        (larger z draws later/on top).  Defaults to ``0``.

    Example
    -------
    ::

        cube = pydex_ge.Object3D(
            mesh=pydex_ge.Mesh.cube(),
            material=pydex_ge.Material(color=(200, 80, 40)),
            transform=pydex_ge.Transform3D(position=(0, 0, -5)),
        )
        cube.rotation = pydex_ge.Quaternion.from_euler(0, 45, 0)
    """

    def __init__(
        self,
        mesh: Mesh | None = None,
        material: Material | None = None,
        transform: Transform3D | None = None,
        visible: bool = True,
        enabled: bool = True,
        z: object = 0,
    ) -> None:
        self._mesh = None
        self._material = None
        if mesh is not None:
            self.mesh = mesh
        if material is not None:
            self.material = material
        self._transform = transform if transform is not None else Transform3D()
        self.visible = bool(visible)
        self.enabled = bool(enabled)
        self.z = _z_number(z)

    # -- data -------------------------------------------------------------

    @property
    def mesh(self) -> Mesh | None:
        """The :class:`Mesh` to draw, or ``None``."""
        return self._mesh

    @mesh.setter
    def mesh(self, value: object) -> None:
        if value is not None and not isinstance(value, Mesh):
            raise ConfigurationError("mesh must be a Mesh or None.")
        self._mesh = value

    @property
    def material(self) -> Material:
        """The :class:`Material` describing the surface."""
        if self._material is None:
            self._material = Material()
        return self._material

    @material.setter
    def material(self, value: object) -> None:
        if value is not None and not isinstance(value, Material):
            raise ConfigurationError("material must be a Material or None.")
        self._material = value

    @property
    def transform(self) -> Transform3D:
        """The :class:`Transform3D` holding position/rotation/scale."""
        return self._transform

    @transform.setter
    def transform(self, value: object) -> None:
        if not isinstance(value, Transform3D):
            raise ConfigurationError("transform must be a Transform3D.")
        self._transform = value

    # -- transform convenience -------------------------------------------

    @property
    def position(self) -> Vector3:
        """The world-space position of the object's transform."""
        return self._transform.world_position

    @position.setter
    def position(self, value: object) -> None:
        self._transform.position = value

    @property
    def rotation(self) -> Quaternion:
        """The local rotation of the object's transform."""
        return self._transform.rotation

    @rotation.setter
    def rotation(self, value: object) -> None:
        self._transform.rotation = value

    @property
    def rotation_euler(self) -> tuple[float, float, float]:
        """The local rotation as ``(yaw, pitch, roll)`` degrees."""
        return self._transform.rotation_euler

    @rotation_euler.setter
    def rotation_euler(self, value: object) -> None:
        self._transform.rotation_euler = value

    def move(self, dx: object, dy: object, dz: object = 0.0) -> None:
        """Move the object's transform by ``dx``, ``dy``, ``dz`` world units."""
        self._transform.move(dx, dy, dz)

    # -- lifecycle --------------------------------------------------------

    def update(self, dt: float) -> None:
        """Update hook.  Override in subclasses; does nothing by default."""

    def draw(self, renderer) -> None:
        """Draw the mesh through the renderer's 3D path (no-op when not visible).

        Skips silently when no 3D camera is active (e.g. the object lives in
        a 2D scene), so a 3D object never breaks a 2D scene.
        """
        if not self.visible or not self.enabled or self._mesh is None:
            return
        if getattr(renderer, "active_camera3d", None) is None:
            return
        renderer.draw_mesh(self._mesh, self._transform, self._material)

    def __repr__(self) -> str:
        return (
            f"Object3D(mesh={self._mesh!r}, material={self._material!r}, "
            f"transform={self._transform!r}, visible={self.visible!r})"
        )


def _z_number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"z must be a number, got {value!r}.")
    return float(value)


__all__ = ["Object3D"]
