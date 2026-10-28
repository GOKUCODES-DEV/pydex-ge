"""The :class:`Mesh`: a raw collection of 3D triangles.

A mesh stores a list of :class:`~pydex_ge.physics.vector3.Vector3` vertices, a
list of triangles (each an index triple into the vertex list), optional
per-triangle face normals (computed automatically when missing) and
optional per-vertex UVs.  PYDEX renders meshes entirely on the CPU: the
renderer projects each triangle, lights it, depth-sorts it and fills it.

Convenience constructors build the most common primitives:
:meth:`Mesh.triangle`, :meth:`Mesh.quad` and :meth:`Mesh.cube`.
"""

from __future__ import annotations

from ..exceptions import ConfigurationError
from ..physics.vector3 import Vector3


def _as_vertex(value: object) -> Vector3:
    if isinstance(value, Vector3):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return Vector3(value[0], value[1], value[2])
    raise ConfigurationError(
        f"A mesh vertex must be a Vector3 or a 3-element (x, y, z) sequence, got {value!r}."
    )


class Mesh:
    """A list of vertices, triangles, face normals and optional UVs.

    Parameters
    ----------
    vertices:
        An iterable of :class:`Vector3` (or 3-element sequences).
    indices:
        An iterable of ``(a, b, c)`` index triples into ``vertices``.
    normals:
        Optional iterable of per-triangle face normals (aligned with
        ``indices``).  When omitted, face normals are computed from each
        triangle's edge cross product.
    uvs:
        Optional iterable of per-vertex ``(u, v)`` texture coordinates.
    """

    __slots__ = ("_vertices", "_indices", "_face_normals", "_uvs")

    def __init__(
        self,
        vertices: object = (),
        indices: object = (),
        normals: object = None,
        uvs: object = None,
    ) -> None:
        vertex_list = [_as_vertex(v) for v in vertices]
        index_list = [tuple(triangle) for triangle in indices]

        if not vertex_list:
            raise ConfigurationError("A mesh needs at least one vertex.")
        if not index_list:
            raise ConfigurationError("A mesh needs at least one triangle.")

        max_index = len(vertex_list) - 1
        for triangle in index_list:
            if len(triangle) != 3:
                raise ConfigurationError(
                    f"Each mesh triangle needs exactly 3 vertex indices, got {triangle!r}."
                )
            for index in triangle:
                if isinstance(index, bool) or not isinstance(index, int):
                    raise ConfigurationError(
                        f"Mesh vertex indices must be ints, got {index!r}."
                    )
                if not 0 <= index <= max_index:
                    raise ConfigurationError(
                        f"Mesh vertex index {index!r} out of range 0-{max_index}."
                    )

        if normals is not None:
            normal_list = [_as_vertex(n).normalized() for n in normals]
            if len(normal_list) != len(index_list):
                raise ConfigurationError(
                    "The number of mesh normals must match the number of triangles "
                    f"({len(index_list)}), got {len(normal_list)}."
                )
        else:
            normal_list = [self._compute_face_normal(vertex_list, triangle) for triangle in index_list]

        uv_list = None
        if uvs is not None:
            uv_list = [self._as_uv(uv) for uv in uvs]
            if len(uv_list) != len(vertex_list):
                raise ConfigurationError(
                    "The number of mesh UVs must match the number of vertices "
                    f"({len(vertex_list)}), got {len(uv_list)}."
                )

        self._vertices = tuple(vertex_list)
        self._indices = tuple(index_list)
        self._face_normals = tuple(normal_list)
        self._uvs = tuple(uv_list) if uv_list is not None else None

    # -- construction -----------------------------------------------------

    @classmethod
    def triangle(cls, a: object, b: object, c: object) -> Mesh:
        """Build a single triangle from three vertices."""
        va, vb, vc = _as_vertex(a), _as_vertex(b), _as_vertex(c)
        return cls([va, vb, vc], [(0, 1, 2)])

    @classmethod
    def quad(cls, a: object, b: object, c: object, d: object) -> Mesh:
        """Build a quad (two triangles) from four corner vertices.

        The corners should be ordered around the quad so that ``(a, b, c)``
        and ``(a, c, d)`` face the same direction.
        """
        va, vb, vc, vd = _as_vertex(a), _as_vertex(b), _as_vertex(c), _as_vertex(d)
        return cls([va, vb, vc, vd], [(0, 1, 2), (0, 2, 3)])

    @classmethod
    def cube(cls, size: object = 1.0) -> Mesh:
        """Build a cube of the given ``size`` centered on the origin.

        The cube is made from 8 vertices and 36 indices (12 triangles), with
        flat per-face normals so each face shades uniformly.
        """
        if isinstance(size, bool) or not isinstance(size, (int, float)):
            raise ConfigurationError(f"size must be a number, got {size!r}.")
        if float(size) <= 0:
            raise ConfigurationError("size must be greater than zero.")
        half = float(size) / 2.0
        vertices = [
            Vector3(-half, -half, -half),  # 0
            Vector3(half, -half, -half),   # 1
            Vector3(half, half, -half),    # 2
            Vector3(-half, half, -half),   # 3
            Vector3(half, -half, half),    # 4
            Vector3(-half, -half, half),   # 5
            Vector3(-half, half, half),    # 6
            Vector3(half, half, half),     # 7
        ]
        front = (0, 1, 2, 3)
        back = (5, 6, 7, 4)
        right = (1, 4, 7, 2)
        left = (5, 0, 3, 6)
        top = (3, 2, 7, 6)
        bottom = (4, 1, 0, 5)
        indices = [
            (front[0], front[2], front[1]), (front[0], front[3], front[2]),
            (back[0], back[2], back[1]), (back[0], back[3], back[2]),
            (right[0], right[2], right[1]), (right[0], right[3], right[2]),
            (left[0], left[2], left[1]), (left[0], left[3], left[2]),
            (top[0], top[2], top[1]), (top[0], top[3], top[2]),
            (bottom[0], bottom[2], bottom[1]), (bottom[0], bottom[3], bottom[2]),
        ]
        normals = [
            Vector3(0, 0, -1), Vector3(0, 0, -1),
            Vector3(0, 0, 1), Vector3(0, 0, 1),
            Vector3(1, 0, 0), Vector3(1, 0, 0),
            Vector3(-1, 0, 0), Vector3(-1, 0, 0),
            Vector3(0, 1, 0), Vector3(0, 1, 0),
            Vector3(0, -1, 0), Vector3(0, -1, 0),
        ]
        return cls(vertices, indices, normals=normals)

    # -- accessors --------------------------------------------------------

    @property
    def vertices(self) -> tuple[Vector3, ...]:
        """The vertex list as a tuple of :class:`Vector3`."""
        return self._vertices

    @property
    def indices(self) -> tuple[tuple[int, int, int], ...]:
        """The triangle index triples."""
        return self._indices

    @property
    def face_normals(self) -> tuple[Vector3, ...]:
        """The per-triangle face normals (unit length), aligned with :attr:`indices`."""
        return self._face_normals

    @property
    def uvs(self) -> tuple[tuple[float, float], ...] | None:
        """The per-vertex ``(u, v)`` texture coordinates, or ``None``."""
        return self._uvs

    @property
    def vertex_count(self) -> int:
        """The number of vertices."""
        return len(self._vertices)

    @property
    def triangle_count(self) -> int:
        """The number of triangles."""
        return len(self._indices)

    @property
    def bounding_radius(self) -> float:
        """The distance from the origin to the farthest vertex."""
        return max((v.length for v in self._vertices), default=0.0)

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _as_uv(value: object) -> tuple[float, float]:
        if isinstance(value, (tuple, list)) and len(value) == 2:
            u, v = value[0], value[1]
        else:
            raise ConfigurationError(
                f"Each mesh UV must be an (u, v) pair, got {value!r}."
            )
        for component, name in ((u, "u"), (v, "v")):
            if isinstance(component, bool) or not isinstance(component, (int, float)):
                raise ConfigurationError(f"Mesh UV {name} must be a number, got {component!r}.")
        return float(u), float(v)

    @staticmethod
    def _compute_face_normal(vertices: list[Vector3], triangle: tuple[int, int, int]) -> Vector3:
        a, b, c = (vertices[i] for i in triangle)
        edge1 = b - a
        edge2 = c - a
        return edge1.cross(edge2).normalized()

    # -- protocol ---------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Mesh(vertices={len(self._vertices)}, "
            f"triangles={len(self._indices)}, "
            f"normals={len(self._face_normals)})"
        )


__all__ = ["Mesh"]
