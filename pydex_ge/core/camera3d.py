"""The :class:`Camera3D`: a perspective camera for the 3D Foundation.

A 3D camera describes *where the viewer stands, where they look, and what
they see*: it holds a world-space :class:`~pydex_ge.physics.vector3.Vector3`
position, a :class:`~pydex_ge.math.quaternion.Quaternion` rotation, a vertical
field of view (degrees), near/far clip distances, a zoom factor, and the
viewport size used to turn 3D points into screen coordinates.

The camera looks down its local **-Z** axis.  ``depth`` is the positive
distance in front of the camera, so a point straight ahead at ``z = -5``
has depth ``5``.  :meth:`project` performs the same perspective projection
the renderer uses, which keeps the math headless-testable.
"""

from __future__ import annotations

import math

from ..exceptions import ConfigurationError
from ..math.quaternion import Quaternion
from ..physics.vector3 import Vector3


def _number(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be a number, got {value!r}.")
    number = float(value)
    if positive and number <= 0:
        raise ConfigurationError(f"{name} must be greater than zero, got {value!r}.")
    return number


def _as_vector(value: object, name: str) -> Vector3:
    if isinstance(value, Vector3):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return Vector3(value[0], value[1], value[2])
    raise ConfigurationError(
        f"{name} must be a Vector3 or a 3-element (x, y, z) sequence, got {value!r}."
    )


def _matrix_to_quaternion(m: tuple[tuple[float, float, float], ...]) -> Quaternion:
    """Convert a 3x3 rotation matrix (row-major) to a :class:`Quaternion`."""
    m00, m01, m02 = m[0]
    m10, m11, m12 = m[1]
    m20, m21, m22 = m[2]
    trace = m00 + m11 + m22
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2.0
        return Quaternion(
            0.25 * s,
            (m21 - m12) / s,
            (m02 - m20) / s,
            (m10 - m01) / s,
        )
    if m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        return Quaternion(
            (m21 - m12) / s,
            0.25 * s,
            (m01 + m10) / s,
            (m02 + m20) / s,
        )
    if m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        return Quaternion(
            (m02 - m20) / s,
            (m01 + m10) / s,
            0.25 * s,
            (m12 + m21) / s,
        )
    s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
    return Quaternion(
        (m10 - m01) / s,
        (m02 + m20) / s,
        (m12 + m21) / s,
        0.25 * s,
    )


class Camera3D:
    """A perspective 3D camera.

    Parameters
    ----------
    width, height:
        The viewport size in screen pixels.  May be ``None`` (the default);
        the renderer fills these from the window on :meth:`~Renderer.begin_3d`,
        and you can set them explicitly via :meth:`set_viewport` or assign
        ``camera.width``/``camera.height`` for standalone projection math.
    position:
        The world-space camera position, a :class:`Vector3` or an
        ``(x, y, z)`` triple.  Defaults to ``(0, 0, 0)``.
    rotation:
        The camera rotation as a :class:`Quaternion`.  Defaults to identity
        (looking down -Z).  Use :meth:`look_at` for a convenient target view.
    fov:
        The vertical field of view in degrees.  Must be between 1 and 179.
        Defaults to ``60``.
    near, far:
        The near and far clip distances (positive, ``near < far``).
        Defaults to ``0.1`` and ``1000.0``.
    zoom:
        How magnified the view is (``1.0`` normal).  Must be positive.
    enabled:
        Whether the camera is active.  Defaults to ``True``.
    """

    def __init__(
        self,
        width: object = None,
        height: object = None,
        *,
        position: object = (0, 0, 0),
        rotation: object = None,
        fov: object = 60.0,
        near: object = 0.1,
        far: object = 1000.0,
        zoom: object = 1.0,
        enabled: bool = True,
    ) -> None:
        self._width: float | None = None
        self._height: float | None = None
        self._position = _as_vector(position, "position").copy()
        self._rotation = (
            rotation if isinstance(rotation, Quaternion) else Quaternion.identity()
        )
        self._fov = _number(fov, "fov")
        if not 1.0 <= self._fov <= 179.0:
            raise ConfigurationError(f"fov must be between 1 and 179 degrees, got {fov!r}.")
        self._near = _number(near, "near", positive=True)
        self._far = _number(far, "far", positive=True)
        if self._near >= self._far:
            raise ConfigurationError("near must be less than far.")
        self._zoom = _number(zoom, "zoom", positive=True)
        self._enabled = bool(enabled)
        self._renderer = None
        self._active = False

        if width is not None or height is not None:
            self.set_viewport(width, height)

    # -- viewport ---------------------------------------------------------

    @property
    def width(self) -> float | None:
        """The viewport width in screen pixels (``None`` until set or auto-filled)."""
        return self._width

    @width.setter
    def width(self, value: object) -> None:
        self._width = _number(value, "width", positive=True)

    @property
    def height(self) -> float | None:
        """The viewport height in screen pixels (``None`` until set or auto-filled)."""
        return self._height

    @height.setter
    def height(self, value: object) -> None:
        self._height = _number(value, "height", positive=True)

    @property
    def aspect(self) -> float:
        """The width/height ratio of the viewport (``1.0`` when unknown)."""
        if self._width is None or self._height is None:
            return 1.0
        return self._width / self._height

    def set_viewport(self, width: object, height: object) -> None:
        """Set the viewport size to ``width`` x ``height`` screen pixels."""
        self._width = _number(width, "width", positive=True)
        self._height = _number(height, "height", positive=True)

    def _require_viewport(self) -> tuple[float, float]:
        if self._width is None or self._height is None:
            raise ConfigurationError(
                "Camera3D has no viewport: set camera.width/height, call "
                "camera.set_viewport(w, h), or draw through the renderer so "
                "begin_3d() can fill it from the window."
            )
        return self._width, self._height

    # -- position ---------------------------------------------------------

    @property
    def position(self) -> Vector3:
        """The world-space camera position."""
        return self._position

    @position.setter
    def position(self, value: object) -> None:
        self._position = _as_vector(value, "position").copy()

    @property
    def x(self) -> float:
        """The x component of the camera position."""
        return self._position.x

    @x.setter
    def x(self, value: object) -> None:
        self._position.x = _number(value, "x")

    @property
    def y(self) -> float:
        """The y component of the camera position."""
        return self._position.y

    @y.setter
    def y(self, value: object) -> None:
        self._position.y = _number(value, "y")

    @property
    def z(self) -> float:
        """The z component of the camera position."""
        return self._position.z

    @z.setter
    def z(self, value: object) -> None:
        self._position.z = _number(value, "z")

    def move(self, dx: object, dy: object, dz: object = 0.0) -> None:
        """Move the camera by ``dx``, ``dy``, ``dz`` world units."""
        self._position.x += _number(dx, "dx")
        self._position.y += _number(dy, "dy")
        self._position.z += _number(dz, "dz")

    # -- rotation ---------------------------------------------------------

    @property
    def rotation(self) -> Quaternion:
        """The camera rotation (a copy; assign a new Quaternion to change it)."""
        return self._rotation.copy()

    @rotation.setter
    def rotation(self, value: object) -> None:
        if not isinstance(value, Quaternion):
            raise ConfigurationError("rotation must be a Quaternion.")
        self._rotation = value.copy()

    @property
    def forward(self) -> Vector3:
        """The world-space direction the camera is looking (-Z)."""
        return self._rotation.conjugate().rotate_vector(Vector3(0, 0, -1))

    @property
    def right(self) -> Vector3:
        """The world-space direction to the camera's right (+X)."""
        return self._rotation.conjugate().rotate_vector(Vector3(1, 0, 0))

    @property
    def up(self) -> Vector3:
        """The world-space direction above the camera (+Y)."""
        return self._rotation.conjugate().rotate_vector(Vector3(0, 1, 0))

    def look_at(self, target: object, up: object = (0, 1, 0)) -> None:
        """Point the camera at ``target`` (keeping ``up`` roughly vertical).

        ``target`` is a world-space :class:`Vector3` (or triple).  The camera
        position is unchanged; only the rotation is set so the camera looks
        from its current position toward ``target``.
        """
        target = _as_vector(target, "target")
        up = _as_vector(up, "up")
        forward = (target - self._position).normalized()
        if forward.length < 1e-9:
            raise ConfigurationError("look_at() target must differ from the camera position.")

        up_reference = up.normalized()
        right = forward.cross(up_reference)
        if right.length < 1e-9:
            up_reference = Vector3(0, 0, 1)
            right = forward.cross(up_reference)
            if right.length < 1e-9:
                up_reference = Vector3(0, 1, 0)
                right = forward.cross(up_reference)
        right = right.normalized()
        camera_up = right.cross(forward).normalized()

        matrix = (
            (right.x, right.y, right.z),
            (camera_up.x, camera_up.y, camera_up.z),
            (-forward.x, -forward.y, -forward.z),
        )
        self._rotation = _matrix_to_quaternion(matrix).normalized()

    # -- projection parameters -------------------------------------------

    @property
    def fov(self) -> float:
        """The vertical field of view in degrees."""
        return self._fov

    @fov.setter
    def fov(self, value: object) -> None:
        value = _number(value, "fov")
        if not 1.0 <= value <= 179.0:
            raise ConfigurationError(f"fov must be between 1 and 179 degrees, got {value!r}.")
        self._fov = value

    @property
    def fov_radians(self) -> float:
        """The vertical field of view in radians."""
        return math.radians(self._fov)

    @property
    def near(self) -> float:
        """The near clip distance."""
        return self._near

    @near.setter
    def near(self, value: object) -> None:
        value = _number(value, "near", positive=True)
        if value >= self._far:
            raise ConfigurationError("near must be less than far.")
        self._near = value

    @property
    def far(self) -> float:
        """The far clip distance."""
        return self._far

    @far.setter
    def far(self, value: object) -> None:
        value = _number(value, "far", positive=True)
        if value <= self._near:
            raise ConfigurationError("far must be greater than near.")
        self._far = value

    @property
    def zoom(self) -> float:
        """How magnified the view is (must be positive)."""
        return self._zoom

    @zoom.setter
    def zoom(self, value: object) -> None:
        self._zoom = _number(value, "zoom", positive=True)

    @property
    def enabled(self) -> bool:
        """True when the renderer draws 3D objects through this camera."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: object) -> None:
        if not isinstance(value, bool):
            raise ConfigurationError("enabled must be a bool.")
        self._enabled = value

    # -- coordinate conversion --------------------------------------------

    def world_to_camera(self, point: object) -> Vector3:
        """Convert a world point to camera space (looking down -Z).

        Depth (the distance in front of the camera) is ``-result.z``.
        """
        world = _as_vector(point, "point")
        return self._rotation.rotate_vector(world - self._position)

    def project_camera_point(self, point: object) -> tuple[float, float, float] | None:
        """Project a **camera-space** point to ``(screen_x, screen_y, depth)``.

        Returns ``None`` when the point is outside the near/far clip range or
        behind the camera.  This shares :meth:`project`'s math, so near-plane
        clipped geometry can be projected without a world->camera round trip.
        """
        width, height = self._require_viewport()
        cam = _as_vector(point, "point")
        depth = -cam.z
        if depth < self._near or depth > self._far:
            return None
        focal = (height / 2.0) * self._zoom / math.tan(self.fov_radians / 2.0)
        sx = width / 2.0 + cam.x * focal / depth
        sy = height / 2.0 - cam.y * focal / depth
        return sx, sy, depth

    def project(self, point: object) -> tuple[float, float, float] | None:
        """Project a world point to ``(screen_x, screen_y, depth)``.

        Returns ``None`` when the point is outside the near/far clip range or
        behind the camera.
        """
        cam = self.world_to_camera(point)
        return self.project_camera_point(cam)

    # -- per-frame step ---------------------------------------------------

    def update(self, dt: object) -> None:
        """Per-frame hook.  Validates ``dt``; Camera3D has no follow logic yet."""
        if isinstance(dt, bool) or not isinstance(dt, (int, float)):
            raise ConfigurationError(f"dt must be a number, got {dt!r}.")
        if float(dt) < 0:
            raise ConfigurationError("dt must be non-negative.")

    # -- renderer integration --------------------------------------------

    def attach(self, renderer) -> None:
        """Remember ``renderer`` so :meth:`begin` can be called without an argument."""
        if renderer is None:
            raise ConfigurationError("Camera3D.attach() needs a renderer.")
        self._renderer = renderer

    def begin(self, renderer=None) -> None:
        """Start drawing 3D objects through this camera.

        Equivalent to ``renderer.begin_3d(self)``.  No-op when :attr:`enabled`
        is ``False``.
        """
        if not self._enabled:
            return
        target = renderer if renderer is not None else self._renderer
        if target is None:
            raise ConfigurationError(
                "Camera3D needs a renderer: pass one to begin(renderer) or call attach(renderer)."
            )
        self._renderer = target
        target.begin_3d(self)
        self._active = True

    def end(self) -> None:
        """Undo :meth:`begin` (equivalent to ``renderer.end_3d()``)."""
        if not self._active:
            if self._enabled:
                raise ConfigurationError("Camera3D.end() called without a matching begin().")
            return
        self._renderer.end_3d()
        self._active = False

    # -- protocol ---------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Camera3D(position={self._position!r}, rotation={self._rotation!r}, "
            f"fov={self._fov!r}, near={self._near!r}, far={self._far!r}, "
            f"zoom={self._zoom!r})"
        )


__all__ = ["Camera3D"]
