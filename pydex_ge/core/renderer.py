"""Frame-presentation facade plus 2D drawing, sprite, and text commands.

The :class:`Renderer` is obtained from ``window.renderer`` (or
``game.renderer``) while a window is open.  It clears and presents the
frame, exposes a :attr:`draw` namespace of 2D drawing primitives, and can
draw :class:`~pydex_ge.graphics.sprite.Sprite` objects and
:class:`~pydex_ge.graphics.text.Text`/:class:`~pydex_ge.graphics.label.Label`
text.  No SDL objects ever reach user code.
"""

from __future__ import annotations

from ..backend.base import BackendRenderer
from ..exceptions import ConfigurationError
from ..graphics.color import normalize_rgb
from ..graphics.drawing import DrawCommands
from ..graphics.image import Image
from ..graphics.material import Material
from ..graphics.mesh import Mesh
from ..graphics.sprite import Sprite
from ..graphics.text import Text
from ..graphics.texture import Texture
from ..transform.transform3d import Transform3D
from .camera3d import Camera3D
from .render3d import build_triangles, clip_line_to_near, fill_triangle

normalize_color = normalize_rgb


class Renderer:
    """A window renderer with frame control, drawing, and sprites.

    Parameters
    ----------
    backend_renderer:
        The backend renderer this facade wraps.
    size:
        Optional ``(width, height)`` of the window in pixels.  Used to
        auto-fill the viewport of a :class:`Camera3D` that has none.
    """

    def __init__(
        self, backend_renderer: BackendRenderer, *, size: object = None
    ) -> None:
        self._renderer = backend_renderer
        self.draw = DrawCommands(backend_renderer)
        # One texture per source (image or pixel sprite) per window session.
        self._texture_cache: dict[int, Texture] = {}
        # One texture per (font, text, color) combination.
        self._text_texture_cache: dict[tuple, Texture] = {}
        # Active cameras (top of stack transforms world-space sprite draws).
        self._camera_stack: list = []
        # Active 3D camera plus queued 3D triangles/lines, flushed by end_3d().
        self._camera3d: Camera3D | None = None
        self._triangles: list = []
        self._lines3d: list = []
        self._active_light = None
        self._size = None
        if size is not None:
            self._set_size(size)
        self._destroyed = False

    def _set_size(self, size: object) -> None:
        if not isinstance(size, (tuple, list)) or len(size) != 2:
            raise ConfigurationError("size must be a (width, height) pair.")
        width, height = size
        if isinstance(width, bool) or not isinstance(width, (int, float)) or width <= 0:
            raise ConfigurationError("size width must be a positive number.")
        if isinstance(height, bool) or not isinstance(height, (int, float)) or height <= 0:
            raise ConfigurationError("size height must be a positive number.")
        self._size = (float(width), float(height))

    def clear(self, color: object = (0, 0, 0)) -> None:
        """Clear the frame to an ``(r, g, b)`` color, each channel 0-255."""
        r, g, b = normalize_color(color)
        self._renderer.clear(r, g, b, 255)

    def present(self) -> None:
        """Present the prepared frame to the screen."""
        self._renderer.present()

    def destroy(self) -> None:
        """Free cached textures and the underlying backend renderer.  Idempotent."""
        if self._destroyed:
            return
        for texture in self._texture_cache.values():
            texture.destroy()
        self._texture_cache.clear()
        for texture in self._text_texture_cache.values():
            texture.destroy()
        self._text_texture_cache.clear()
        self._renderer.destroy()
        self._destroyed = True

    def create_texture(self, image: Image) -> Texture:
        """Resolve an image to a drawable :class:`Texture` (cached).

        Returns the same texture for a given image while this renderer is
        alive, so drawing many sprites from one image is efficient.
        """
        if not isinstance(image, Image):
            raise TypeError("create_texture() requires a pydex_ge.Image.")
        if self._destroyed:
            raise RuntimeError("Cannot create a texture from a destroyed renderer.")
        key = id(image)
        texture = self._texture_cache.get(key)
        if texture is None:
            backend_texture = self._renderer.create_texture_from_image(
                image._backend_image
            )
            texture = Texture(backend_texture)
            self._texture_cache[key] = texture
        return texture

    def draw_sprite(self, sprite: Sprite, *, tint_override: object = None) -> None:
        """Draw a sprite at its world position, scale, transform, and alpha.

        The sprite's texture is created on first use and cached for this
        window session.  When a camera is active (between its ``begin()``
        and ``end()``), the sprite is a **world-space** object: its world
        position is converted to screen coordinates and its size is scaled
        by the camera zoom.  Rotation, origin, flip, and tint are forwarded
        to the backend.  Pixel-art scaling keeps the existing
        nearest-neighbor behavior.

        ``tint_override``, when given, is an RGB color multiply combined
        with the sprite's own effective tint (used by animated sprites so
        a tint/flash on the sprite also colors the animation frame).
        """
        if self._destroyed:
            raise RuntimeError("Cannot draw on a destroyed renderer.")
        if not sprite.visible:
            return
        if sprite._image is not None:
            texture = self.create_texture(sprite._image)
        else:
            width, height, pixels = sprite._pixel_source
            key = id(sprite)
            texture = self._texture_cache.get(key)
            if texture is None:
                backend_texture = self._renderer.create_texture_from_pixels(
                    width, height, pixels
                )
                texture = Texture(backend_texture)
                self._texture_cache[key] = texture
        if sprite._region is not None:
            src = sprite._region
            src_width, src_height = src[2], src[3]
        else:
            src = None
            src_width, src_height = texture.width, texture.height

        world = sprite.world_position
        sprite_scale = sprite.world_scale
        if isinstance(sprite_scale, (tuple, list)):
            scale_x, scale_y = sprite_scale[0], sprite_scale[1]
        else:
            scale_x = scale_y = sprite_scale

        if self._camera_stack:
            camera = self._camera_stack[-1]
            screen = camera.world_to_screen(world)
            sx, sy = round(screen.x), round(screen.y)
            zoom = camera.zoom
            scale_x *= zoom
            scale_y *= zoom
        else:
            sx, sy = round(world.x), round(world.y)

        dst_width = round(src_width * scale_x)
        dst_height = round(src_height * scale_y)
        origin = sprite.origin
        ox = origin[0] * dst_width
        oy = origin[1] * dst_height
        dst = (round(sx - ox), round(sy - oy), dst_width, dst_height)
        angle = sprite.world_rotation
        flip = 0
        if sprite.flip_x:
            flip |= 1
        if sprite.flip_y:
            flip |= 2
        tint = sprite._draw_tint
        if tint_override is not None:
            base = sprite._draw_tint
            tint = tuple(
                max(0, min(255, int(round(base[i] * tint_override[i] / 255))))
                for i in range(3)
            )
        if angle != 0 or flip != 0 or ox != 0 or oy != 0:
            self._renderer.draw_texture(
                texture._backend_texture,
                src,
                dst,
                sprite.alpha,
                angle=angle,
                center=(round(ox), round(oy)),
                flip=flip,
                color_mod=tint,
            )
        elif tint != (255, 255, 255):
            self._renderer.draw_texture(
                texture._backend_texture, src, dst, sprite.alpha, color_mod=tint
            )
        else:
            self._renderer.draw_texture(
                texture._backend_texture, src, dst, sprite.alpha
            )

    def draw_text(self, text: Text) -> None:
        """Draw a :class:`~pydex_ge.graphics.text.Text` (or Label) at its position.

        The text is rendered to a texture on first use and cached per
        (font, text, color) for this window session.
        """
        if self._destroyed:
            raise RuntimeError("Cannot draw on a destroyed renderer.")
        if not text.visible:
            return
        if not text.text:
            return
        font = text.font
        key = (id(font._backend_font), text.text, text.color)
        texture = self._text_texture_cache.get(key)
        if texture is None:
            backend_image = font._backend_font.render_text(text.text, text.color)
            try:
                backend_texture = self._renderer.create_texture_from_image(
                    backend_image
                )
            finally:
                backend_image.destroy()
            texture = Texture(backend_texture)
            self._text_texture_cache[key] = texture
        self._renderer.draw_texture(
            texture._backend_texture,
            None,
            (text.x, text.y, texture.width, texture.height),
            255,
        )

    def draw_label(self, text: Text) -> None:
        """Draw a :class:`~pydex_ge.graphics.label.Label` (or Text)."""
        self.draw_text(text)

    # -- camera support ---------------------------------------------------

    @property
    def active_camera(self):
        """The camera currently between ``begin_camera``/``end_camera`` (or None).

        World-space helpers such as :class:`~pydex_ge.graphics.Parallax`
        layers use this to resolve the active camera without needing the
        camera passed explicitly.
        """
        if self._camera_stack:
            return self._camera_stack[-1]
        return None

    def begin_camera(self, camera) -> None:
        """Activate ``camera`` so world-space sprite draws are transformed.

        Called by ``camera.begin()``; you normally do not call this
        directly.  Labels and text are never transformed.
        """
        if camera is None:
            raise ConfigurationError("begin_camera() requires a Camera.")
        self._camera_stack.append(camera)

    def end_camera(self) -> None:
        """Deactivate the topmost camera.

        Called by ``camera.end()``; raises if no camera is active.
        """
        if not self._camera_stack:
            raise RuntimeError("end_camera() called without a matching begin_camera().")
        self._camera_stack.pop()

    # -- 3D support -------------------------------------------------------

    @property
    def active_camera3d(self) -> Camera3D | None:
        """The camera between ``begin_3d``/``end_3d`` (or None)."""
        return self._camera3d

    @property
    def active_light(self):
        """The light most recently passed to :meth:`begin_3d` (or None)."""
        return self._active_light

    def begin_3d(self, camera: Camera3D, light=None) -> None:
        """Start the 3D draw path through ``camera``.

        Called by ``camera.begin()``.  If the camera has no viewport, the
        window size supplied to this renderer is used to fill it.  No-op when
        the camera is disabled.  ``light``, when given, is a
        :class:`~pydex_ge.graphics.light.DirectionalLight` used to shade meshes
        queued between this call and :meth:`end_3d`; without it meshes are
        drawn unlit (material color plus any emission).
        """
        if not isinstance(camera, Camera3D):
            raise ConfigurationError("begin_3d() requires a Camera3D.")
        if not camera.enabled:
            return
        if camera.width is None or camera.height is None:
            if self._size is None:
                raise ConfigurationError(
                    "Camera3D has no viewport and the renderer does not know the "
                    "window size: set camera.width/height or call set_viewport()."
                )
            camera.set_viewport(int(self._size[0]), int(self._size[1]))
        self._active_light = light
        self._camera3d = camera
        self._triangles = []
        self._lines3d = []

    def draw_mesh(
        self,
        mesh: Mesh,
        transform: Transform3D | None = None,
        material: Material | None = None,
        light=None,
    ) -> None:
        """Queue a mesh for the active 3D camera.

        ``transform`` (a :class:`Transform3D`, or None for identity) places
        the mesh in the world; ``material`` (or a fresh white material)
        describes its surface.  The mesh is projected, lit and depth-sorted
        when :meth:`end_3d` flushes.  ``light`` is a
        :class:`~pydex_ge.graphics.light.DirectionalLight`; when omitted the
        light passed to :meth:`begin_3d` (if any) is used.
        """
        if self._camera3d is None:
            raise ConfigurationError(
                "draw_mesh() requires an active 3D camera: call begin_3d(camera) first."
            )
        if not isinstance(mesh, Mesh):
            raise ConfigurationError("draw_mesh() requires a Mesh.")
        if transform is not None and not isinstance(transform, Transform3D):
            raise ConfigurationError("draw_mesh() transform must be a Transform3D or None.")
        if material is not None and not isinstance(material, Material):
            raise ConfigurationError("draw_mesh() material must be a Material or None.")
        if transform is None:
            transform = Transform3D()
        if material is None:
            material = Material()
        self._triangles.extend(
            build_triangles(
                self._camera3d,
                mesh,
                transform,
                material,
                light if light is not None else self._active_light,
            )
        )

    def draw_line_3d(
        self,
        start: object,
        end: object,
        color: object = (255, 255, 255),
    ) -> None:
        """Queue a 3D line (e.g. for a ground grid) for the active 3D camera.

        Endpoints are world-space points (each a :class:`Vector3` or an
        ``(x, y, z)`` triple).  Lines are drawn on top of meshes when
        :meth:`end_3d` flushes.
        """
        if self._camera3d is None:
            raise ConfigurationError(
                "draw_line_3d() requires an active 3D camera: call begin_3d(camera) first."
            )
        r, g, b = normalize_color(color)
        start_cam = self._camera3d.world_to_camera(start)
        end_cam = self._camera3d.world_to_camera(end)
        clipped = clip_line_to_near(start_cam, end_cam, self._camera3d.near)
        if clipped is None:
            return
        p1 = self._camera3d.project_camera_point(clipped[0])
        p2 = self._camera3d.project_camera_point(clipped[1])
        if p1 is None or p2 is None:
            return
        self._lines3d.append((p1[0], p1[1], p2[0], p2[1], (r, g, b, 255)))

    def end_3d(self) -> None:
        """Flush the queued 3D triangles and lines, then leave the 3D path.

        Draws triangles farthest-first (painter's algorithm), then the queued
        3D lines on top.  Raises if no 3D camera is active.
        """
        if self._camera3d is None:
            raise RuntimeError("end_3d() called without a matching begin_3d().")
        self._triangles.sort(key=lambda record: record[4], reverse=True)
        for triangle in self._triangles:
            fill_triangle(triangle, self._renderer.draw_line)
        for line in self._lines3d:
            self._renderer.draw_line(line[0], line[1], line[2], line[3], line[4])
        self._triangles = []
        self._lines3d = []
        self._camera3d = None


__all__ = ["Renderer", "normalize_color"]