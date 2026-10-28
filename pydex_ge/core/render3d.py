"""Pure CPU-side 3D rendering math for the 3D Foundation.

PYDEX renders 3D entirely on the CPU: no GPU, no textures on meshes.  This
module contains the pure, headless-testable pipeline the renderer uses:

1. transform mesh vertices from local to world space,
2. convert world points to camera space and back-face cull triangles,
3. clip triangles and line segments against the near plane so geometry
   close to the camera is cut, not dropped (no pop-in/pop-out),
4. perspective-project the surviving vertices,
5. apply a single directional diffuse light,
6. painter's-algorithm sort (farthest triangles first),
7. scanline-rasterize each triangle into horizontal spans.

Every step is a plain function so tests can exercise the math without a
window or a backend.
"""

from __future__ import annotations

import math

from ..graphics.material import Material
from ..graphics.mesh import Mesh
from ..physics.vector3 import Vector3


def transform_point_to_world(transform, local: Vector3) -> Vector3:
    """Convert a mesh-local point to world space through a transform.

    The transform's ``origin`` acts as a pivot: the local point is offset by
    the origin *before* scale and rotation, so rotating a transform spins a
    mesh about its origin.
    """
    world_scale = transform.world_scale
    origin = transform.origin
    offset = Vector3(
        (local.x - origin.x) * world_scale.x,
        (local.y - origin.y) * world_scale.y,
        (local.z - origin.z) * world_scale.z,
    )
    rotated = transform.world_rotation.rotate_vector(offset)
    position = transform.world_position
    return Vector3(
        position.x + rotated.x,
        position.y + rotated.y,
        position.z + rotated.z,
    )


def _clip_near(polygon: list[Vector3], near: float) -> list[Vector3]:
    """Clip a camera-space polygon against the near plane.

    ``polygon`` is a sequence of 3 :class:`Vector3` vertices ordered around
    the polygon; the near plane is ``z <= -near`` (the camera looks down -Z).
    Returns the clipped polygon (3 or 4 vertices, winding preserved) or an
    empty list when everything is behind the plane.
    """
    plane = -near

    def inside(point: Vector3) -> bool:
        return point.z <= plane

    def intersect(p1: Vector3, p2: Vector3) -> Vector3:
        t = (plane - p1.z) / (p2.z - p1.z)
        return Vector3(
            p1.x + t * (p2.x - p1.x),
            p1.y + t * (p2.y - p1.y),
            plane,
        )

    clipped = []
    prev = polygon[-1]
    prev_in = inside(prev)
    for current in polygon:
        current_in = inside(current)
        if current_in:
            if not prev_in:
                clipped.append(intersect(prev, current))
            clipped.append(current)
        elif prev_in:
            clipped.append(intersect(prev, current))
        prev, prev_in = current, current_in
    return clipped


def clip_line_to_near(start: Vector3, end: Vector3, near: float):
    """Clip a camera-space line segment against the near plane.

    ``start`` and ``end`` are camera-space :class:`Vector3`; ``near`` is the
    camera's near distance (the plane is ``z <= -near``).  Returns the
    clipped ``(start, end)`` pair in camera space, or ``None`` when the whole
    segment is behind the plane.
    """
    plane = -near

    def inside(point: Vector3) -> bool:
        return point.z <= plane

    start_in, end_in = inside(start), inside(end)
    if start_in and end_in:
        return start, end
    if not start_in and not end_in:
        return None

    def intersect(p1: Vector3, p2: Vector3) -> Vector3:
        t = (plane - p1.z) / (p2.z - p1.z)
        return Vector3(
            p1.x + t * (p2.x - p1.x),
            p1.y + t * (p2.y - p1.y),
            plane,
        )

    hit = intersect(start, end)
    return (start, hit) if start_in else (hit, end)


def shade_color(material: Material, world_normal: Vector3, light) -> tuple[int, int, int]:
    """Compute the RGB color of a lit triangle.

    ``world_normal`` must be unit length.  With no light (or a disabled
    light) the material color is used as-is plus any emission.  With a light,
    the diffuse term is ``max(0, dot(normal, -direction))`` scaled by
    ``intensity`` and the light color, plus an ``ambient`` baseline so faces
    pointing away from the light are dimmed but never pure black, then
    emission is added.
    """
    base_r, base_g, base_b = material.color
    em_r, em_g, em_b = material.emission

    if light is None or not getattr(light, "enabled", True):
        return (
            _clamp_channel(base_r + em_r),
            _clamp_channel(base_g + em_g),
            _clamp_channel(base_b + em_b),
        )

    lr, lg, lb = light.color
    lambert = max(0.0, world_normal.dot(-light.direction))
    scale = float(light.intensity) * lambert + float(getattr(light, "ambient", 0.0))
    return (
        _clamp_channel(base_r * (lr / 255.0) * scale + em_r),
        _clamp_channel(base_g * (lg / 255.0) * scale + em_g),
        _clamp_channel(base_b * (lb / 255.0) * scale + em_b),
    )


def build_triangles(camera, mesh: Mesh, transform, material: Material, light) -> list:
    """Build depth-sorted, lit, projected triangle records for one mesh.

    Returns a list (already sorted farthest-first) of records:
    ``(point_a, point_b, point_c, color, depth)`` where each point is a
    ``(screen_x, screen_y, depth)`` triple and ``color`` is RGB.

    Triangles are clipped against the near plane in camera space before
    projection, so geometry that passes close to the camera is cut instead
    of disappearing.
    """
    world_vertices = [
        transform_point_to_world(transform, vertex) for vertex in mesh.vertices
    ]
    world_rotation = transform.world_rotation
    near = camera.near

    records = []
    for index, triangle in enumerate(mesh.indices):
        a_world = world_vertices[triangle[0]]
        b_world = world_vertices[triangle[1]]
        c_world = world_vertices[triangle[2]]

        cam_a = camera.world_to_camera(a_world)
        cam_b = camera.world_to_camera(b_world)
        cam_c = camera.world_to_camera(c_world)

        normal_cam = (cam_b - cam_a).cross(cam_c - cam_a)
        if normal_cam.z <= 0.0:
            continue

        clipped = _clip_near([cam_a, cam_b, cam_c], near)
        if len(clipped) < 3:
            continue

        world_normal = world_rotation.rotate_vector(mesh.face_normals[index]).normalized()
        color = shade_color(material, world_normal, light)

        if len(clipped) == 3:
            polygons = (clipped,)
        else:
            polygons = (clipped[0:3], (clipped[0], clipped[2], clipped[3]))

        depth = sum(-point.z for point in clipped) / len(clipped)
        for polygon in polygons:
            projected = [camera.project_camera_point(point) for point in polygon]
            if any(point is None for point in projected):
                continue
            proj_a, proj_b, proj_c = projected
            records.append((proj_a, proj_b, proj_c, color, depth))

    records.sort(key=lambda record: record[4], reverse=True)
    return records


def fill_triangle(record, draw_line) -> None:
    """Rasterize one triangle record into horizontal spans.

    ``draw_line`` is a callable ``draw_line(x1, y1, x2, y2, color)``.
    """
    point_a, point_b, point_c, color = record[0], record[1], record[2], record[3]
    ordered = sorted((point_a, point_b, point_c), key=lambda point: point[1])
    (x_top, y_top, _), (x_mid, y_mid, _), (x_bottom, y_bottom, _) = ordered

    y_min = int(math.ceil(y_top))
    y_max = int(math.floor(y_bottom))
    if y_max < y_min:
        _fill_fallback_pixel(point_a, point_b, point_c, color, draw_line)
        return

    rgba = (color[0], color[1], color[2], 255)
    edges = (
        (x_top, y_top, x_mid, y_mid),
        (x_top, y_top, x_bottom, y_bottom),
        (x_mid, y_mid, x_bottom, y_bottom),
    )

    drawn = False
    for y in range(y_min, y_max + 1):
        yf = y + 0.5
        crosses = []
        for ex1, ey1, ex2, ey2 in edges:
            if abs(ey2 - ey1) < 1e-12:
                continue
            t = (yf - ey1) / (ey2 - ey1)
            if 0.0 <= t <= 1.0:
                crosses.append(ex1 + (ex2 - ex1) * t)
        if len(crosses) < 2:
            continue
        left = int(math.ceil(min(crosses)))
        right = int(math.floor(max(crosses)))
        if right < left:
            continue
        draw_line(left, y, right, y, rgba)
        drawn = True

    if not drawn and _has_extent(point_a, point_b, point_c):
        _fill_fallback_pixel(point_a, point_b, point_c, color, draw_line)


def _has_extent(point_a, point_b, point_c) -> bool:
    """True when the projected points are not all identical (degenerate)."""
    return (
        (point_a[0] != point_b[0] or point_a[1] != point_b[1])
        or (point_b[0] != point_c[0] or point_b[1] != point_c[1])
    )


def _fill_fallback_pixel(point_a, point_b, point_c, color, draw_line) -> None:
    """Draw a single pixel at the centroid for sub-pixel triangles.

    Triangles smaller than one pixel (e.g. a cube far from the camera, or a
    face seen almost edge-on) would otherwise vanish entirely.  Drawing one
    centroid pixel keeps distant objects visible.
    """
    cx = (point_a[0] + point_b[0] + point_c[0]) / 3.0
    cy = (point_a[1] + point_b[1] + point_c[1]) / 3.0
    px = int(round(cx))
    py = int(round(cy))
    rgba = (color[0], color[1], color[2], 255)
    draw_line(px, py, px, py, rgba)


def _clamp_channel(value: float) -> int:
    return int(round(max(0.0, min(255.0, value))))


__all__ = [
    "build_triangles",
    "clip_line_to_near",
    "fill_triangle",
    "shade_color",
    "transform_point_to_world",
]
