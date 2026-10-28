"""The SDL2 backend, built on the ``pysdl2`` + ``pysdl2-dll`` packages.

PySDL2 is imported lazily, inside the methods that need it, so importing
``pydex_ge`` never requires SDL2 to be installed.  If the library is missing
or cannot be used, a :class:`~pydex_ge.exceptions.BackendError` is raised
with instructions rather than silently failing.
"""

from __future__ import annotations

import ctypes
import math
import os
from typing import Any

from ..exceptions import BackendError, MissingAssetError, missing_asset_message
from .base import (
    Backend,
    BackendEvent,
    BackendFont,
    BackendImage,
    BackendMusic,
    BackendRenderer,
    BackendSound,
    BackendTexture,
    BackendWindow,
)

_INSTALL_HINT = (
    "Install the SDL2 backend with:\n"
    "    pip install pysdl2 pysdl2-dll\n"
)


class SDL2Window(BackendWindow):
    """Adapter around a :class:`sdl2.ext.Window`."""

    def __init__(self, handle: Any) -> None:
        self._handle = handle
        self._closed = False

    def close(self) -> None:
        if not self._closed:
            self._handle.close()
            self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed


def _byteify(path: str) -> bytes:
    try:
        return os.fsencode(path)
    except TypeError:
        return path.encode("utf-8")


def _utf8(text: str) -> bytes:
    return text.encode("utf-8")


_SCANCODE_NAMES = {
    "escape": 41,
    "enter": 40,
    "space": 44,
    "left": 80,
    "right": 79,
    "up": 82,
    "down": 81,
    "backspace": 42,
    "tab": 43,
    "delete": 76,
    "home": 74,
    "end": 77,
    "pageup": 75,
    "pagedown": 78,
    "insert": 73,
    "capslock": 57,
    "shift": 225,
    "control": 224,
    "alt": 226,
    "f1": 58,
    "f2": 59,
    "f3": 60,
    "f4": 61,
    "f5": 62,
    "f6": 63,
    "f7": 64,
    "f8": 65,
    "f9": 66,
    "f10": 67,
    "f11": 68,
    "f12": 69,
    ".": 55,
    ",": 54,
    "/": 56,
    ";": 51,
    "'": 52,
    "[": 47,
    "]": 48,
    "\\": 49,
    "-": 45,
    "=": 46,
    "`": 53,
}


def _key_name(sdl2: Any, scancode: int) -> str | None:
    """Convert an SDL scancode into a friendly, lowercase key name."""
    if 4 <= scancode <= 29:  # SDL_SCANCODE_A .. SDL_SCANCODE_Z
        return chr(ord("a") + scancode - 4)
    if 30 <= scancode <= 38:  # SDL_SCANCODE_1 .. SDL_SCANCODE_9
        return str(scancode - 30 + 1)
    if scancode == 39:  # SDL_SCANCODE_0
        return "0"
    for name, code in _SCANCODE_NAMES.items():
        if code == scancode:
            return name
    return None


def _button_name(button: int) -> str | None:
    """Convert an SDL mouse button id into a friendly name."""
    if button == 1:
        return "left"
    if button == 3:
        return "right"
    if button == 2:
        return "middle"
    return None


class SDL2Image(BackendImage):
    """Adapter around an :class:`SDL_Surface` loaded from an image file."""

    def __init__(self, backend: SDL2Backend, pointer: Any) -> None:
        self._backend = backend
        self._ptr = pointer
        self._destroyed = False

    def _check(self) -> None:
        if self._destroyed or self._ptr is None:
            raise RuntimeError("Cannot use an image after it has been destroyed.")

    @property
    def width(self) -> int:
        self._check()
        return int(self._ptr.contents.w)

    @property
    def height(self) -> int:
        self._check()
        return int(self._ptr.contents.h)

    def destroy(self) -> None:
        if self._destroyed:
            return
        if self._ptr is not None:
            self._backend._sdl2.surface.SDL_FreeSurface(self._ptr)
            self._ptr = None
        self._destroyed = True


class SDL2Font(BackendFont):
    """Adapter around a ``TTF_Font*`` handle opened by SDL_ttf."""

    def __init__(self, backend: SDL2Backend, pointer: Any, size: int) -> None:
        self._backend = backend
        self._ptr = pointer
        self._size = size
        self._destroyed = False

    def _check(self) -> None:
        if self._destroyed or self._ptr is None:
            raise RuntimeError("Cannot use a font after it has been destroyed.")

    @property
    def size(self) -> int:
        self._check()
        return self._size

    def measure_text(self, text: str) -> tuple[int, int]:
        self._check()
        if not isinstance(text, str):
            raise BackendError("Text must be a string.")
        sdl2 = self._backend._sdl2
        ttf = self._backend._ttf
        width = sdl2.Sint32(0)
        height = sdl2.Sint32(0)
        if ttf.TTF_SizeUTF8(self._ptr, _utf8(text), width, height) != 0:
            raise BackendError(f"SDL_ttf could not measure text: {self._backend._error_text(sdl2)}")
        return int(width.value), int(height.value)

    def render_text(self, text: str, color: tuple[int, int, int, int]) -> BackendImage:
        self._check()
        if not isinstance(text, str):
            raise BackendError("Text must be a string.")
        if not isinstance(color, (tuple, list)) or len(color) != 4:
            raise BackendError("Text color must be an RGBA tuple.")
        sdl2 = self._backend._sdl2
        ttf = self._backend._ttf
        sdl_color = sdl2.SDL_Color(*(int(channel) for channel in color))
        pointer = ttf.TTF_RenderUTF8_Blended(self._ptr, _utf8(text), sdl_color)
        if not pointer:
            raise BackendError(
                f"SDL_ttf could not render text {text!r}: {self._backend._error_text(sdl2)}"
            )
        return SDL2Image(self._backend, pointer)

    def destroy(self) -> None:
        if self._destroyed:
            return
        if self._ptr is not None:
            self._backend._ttf.TTF_CloseFont(self._ptr)
            self._ptr = None
        self._backend._fonts = {
            key: font
            for key, font in self._backend._fonts.items()
            if font is not self
        }
        self._destroyed = True


class SDL2Sound(BackendSound):
    """Adapter around an SDL_mixer ``Mix_Chunk*`` sound effect.

    Each sound keeps the channel it is currently playing on so that
    ``stop``/``pause``/``resume`` target exactly this sound, even when many
    sounds overlap.  The chunk address is used to confirm the channel still
    holds this chunk (channels are reused once a sound finishes).
    """

    def __init__(self, backend: SDL2Backend, pointer: Any, path: str) -> None:
        self._backend = backend
        self._ptr = pointer
        self._path = path
        self._channel = -1
        self._volume = 1.0
        self._destroyed = False

    def _check(self) -> None:
        if self._destroyed or self._ptr is None:
            raise RuntimeError("Cannot use a sound after it has been destroyed.")

    def _mixer(self) -> Any:
        return self._backend._mixer

    def _channel_still_mine(self, channel: int) -> bool:
        if channel < 0:
            return False
        current = self._mixer().Mix_GetChunk(channel)
        if not current:
            return False
        return ctypes.cast(current, ctypes.c_void_p).value == ctypes.cast(
            self._ptr, ctypes.c_void_p
        ).value

    def play(self, loop: bool = False) -> None:
        self._check()
        mixer = self._mixer()
        if self._channel_still_mine(self._channel):
            mixer.Mix_HaltChannel(self._channel)
        loops = -1 if loop else 0
        channel = mixer.Mix_PlayChannel(-1, self._ptr, loops)
        if channel == -1:
            raise BackendError(
                f"SDL_mixer could not play sound {self._path!r}: "
                f"{self._backend._mixer_error()}"
            )
        self._channel = int(channel)
        # Global sound volume scales the channel; per-sound volume scales the
        # chunk.  Effective volume is their product (both default to 1.0).
        mixer.Mix_Volume(channel, round(self._backend.sound_volume() * 128))
        mixer.Mix_VolumeChunk(self._ptr, round(self._volume * 128))

    def stop(self) -> None:
        self._check()
        if self._channel_still_mine(self._channel):
            self._mixer().Mix_HaltChannel(self._channel)
        self._channel = -1

    def pause(self) -> None:
        self._check()
        if self._channel_still_mine(self._channel):
            self._mixer().Mix_Pause(self._channel)

    def resume(self) -> None:
        self._check()
        if self._channel_still_mine(self._channel):
            self._mixer().Mix_Resume(self._channel)

    def set_volume(self, volume: float) -> None:
        self._check()
        self._volume = volume
        self._mixer().Mix_VolumeChunk(self._ptr, round(volume * 128))

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def playing(self) -> bool:
        if self._destroyed:
            return False
        return self._channel_still_mine(self._channel) and bool(
            self._mixer().Mix_Playing(self._channel)
        )

    @property
    def paused(self) -> bool:
        if self._destroyed:
            return False
        return self._channel_still_mine(self._channel) and bool(
            self._mixer().Mix_Paused(self._channel)
        )

    def destroy(self) -> None:
        if self._destroyed:
            return
        if self._channel_still_mine(self._channel):
            self._mixer().Mix_HaltChannel(self._channel)
        if self._ptr is not None:
            self._mixer().Mix_FreeChunk(self._ptr)
            self._ptr = None
        self._backend._sounds = [
            sound for sound in self._backend._sounds if sound is not self
        ]
        self._destroyed = True


class SDL2Music(BackendMusic):
    """Adapter around an SDL_mixer ``Mix_Music*`` track.

    SDL_mixer plays at most one music track at a time, so pause/resume/stop
    operate on the shared music channel.
    """

    def __init__(self, backend: SDL2Backend, pointer: Any, path: str) -> None:
        self._backend = backend
        self._ptr = pointer
        self._path = path
        self._volume = 1.0
        self._destroyed = False

    def _check(self) -> None:
        if self._destroyed or self._ptr is None:
            raise RuntimeError("Cannot use music after it has been destroyed.")

    def _mixer(self) -> Any:
        return self._backend._mixer

    def _apply_volume(self) -> None:
        # Effective music-channel volume is the product of the global music
        # volume (backend) and this track's own volume.
        effective = self._backend.music_volume() * self._volume
        self._mixer().Mix_VolumeMusic(round(effective * 128))

    def play(self, loop: bool = True) -> None:
        self._check()
        mixer = self._mixer()
        loops = -1 if loop else 0
        if mixer.Mix_PlayMusic(self._ptr, loops) == -1:
            raise BackendError(
                f"SDL_mixer could not play music {self._path!r}: "
                f"{self._backend._mixer_error()}"
            )
        self._backend._current_music = self
        self._apply_volume()

    def stop(self) -> None:
        self._check()
        self._mixer().Mix_HaltMusic()

    def pause(self) -> None:
        self._check()
        self._mixer().Mix_PauseMusic()

    def resume(self) -> None:
        self._check()
        self._mixer().Mix_ResumeMusic()

    def set_volume(self, volume: float) -> None:
        self._check()
        self._volume = volume
        if self.playing:
            self._apply_volume()

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def playing(self) -> bool:
        if self._destroyed:
            return False
        return bool(self._mixer().Mix_PlayingMusic())

    @property
    def paused(self) -> bool:
        if self._destroyed:
            return False
        return bool(self._mixer().Mix_PausedMusic())

    def destroy(self) -> None:
        if self._destroyed:
            return
        if self._ptr is not None:
            self._mixer().Mix_FreeMusic(self._ptr)
            self._ptr = None
        self._backend._musics = [
            music for music in self._backend._musics if music is not self
        ]
        self._destroyed = True


class SDL2Texture(BackendTexture):
    """Adapter around an :class:`sdl2.ext.Texture`.

    The texture stays owned by its renderer; ``destroy`` frees it while the
    renderer is still alive (a destroyed renderer frees its textures too, so
    the destroy is skipped if the renderer is already gone).
    """

    def __init__(
        self,
        renderer: SDL2Renderer,
        ext_texture: Any,
        width: int,
        height: int,
    ) -> None:
        self._renderer = renderer
        self._texture = ext_texture
        self._width = width
        self._height = height
        self._destroyed = False

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def destroy(self) -> None:
        if self._destroyed:
            return
        if not self._renderer._destroyed:
            self._texture.destroy()
        self._destroyed = True


class SDL2Renderer(BackendRenderer):
    """Adapter around a :class:`sdl2.ext.Renderer`.

    SDL2 has no native circle primitive, so circles are rasterized on the
    CPU: outlined circles use a midpoint algorithm (``SDL_RenderDrawPoint``)
    and filled circles draw horizontal spans (``SDL_RenderDrawLine``).
    """

    def __init__(self, handle: Any, sdl2: Any) -> None:
        self._handle = handle
        self._sdl2 = sdl2
        self._raw = handle.sdlrenderer
        self._destroyed = False

    def clear(self, r: int, g: int, b: int, a: int = 255) -> None:
        self._handle.clear((r, g, b, a))

    def present(self) -> None:
        self._handle.present()

    def destroy(self) -> None:
        if not self._destroyed:
            self._handle.destroy()
            self._destroyed = True

    def draw_pixel(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        self._handle.draw_point((x, y), color)

    def draw_line(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple[int, int, int, int],
    ) -> None:
        self._handle.draw_line([(x1, y1), (x2, y2)], color)

    def draw_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int, int],
        filled: bool = True,
    ) -> None:
        rect = self._sdl2.SDL_Rect(int(x), int(y), int(width), int(height))
        if filled:
            self._handle.fill(rect, color)
        else:
            self._handle.draw_rect(rect, color)

    def draw_circle(
        self,
        cx: int,
        cy: int,
        radius: int,
        color: tuple[int, int, int, int],
        filled: bool = True,
    ) -> None:
        self._sdl2.SDL_SetRenderDrawColor(self._raw, *color)
        if filled:
            self._draw_filled_circle(cx, cy, radius)
        else:
            self._draw_outline_circle(cx, cy, radius)

    def _draw_outline_circle(self, cx: int, cy: int, radius: int) -> None:
        x, y = 0, radius
        decision = 1 - radius
        while x <= y:
            self._plot_symmetry(cx, cy, x, y)
            x += 1
            if decision < 0:
                decision += 2 * x + 1
            else:
                y -= 1
                decision += 2 * (x - y) + 1

    def _plot_symmetry(self, cx: int, cy: int, x: int, y: int) -> None:
        draw_point = self._sdl2.SDL_RenderDrawPoint
        raw = self._raw
        draw_point(raw, cx + x, cy + y)
        draw_point(raw, cx - x, cy + y)
        draw_point(raw, cx + x, cy - y)
        draw_point(raw, cx - x, cy - y)
        draw_point(raw, cx + y, cy + x)
        draw_point(raw, cx - y, cy + x)
        draw_point(raw, cx + y, cy - x)
        draw_point(raw, cx - y, cy - x)

    def _draw_filled_circle(self, cx: int, cy: int, radius: int) -> None:
        draw_line = self._sdl2.SDL_RenderDrawLine
        raw = self._raw
        for y in range(cy - radius, cy + radius + 1):
            dy = y - cy
            dx = int(math.sqrt(radius * radius - dy * dy))
            draw_line(raw, cx - dx, y, cx + dx, y)

    def _error(self) -> str:
        return SDL2Backend._error_text(self._sdl2)

    def _make_sdl_texture(self, surface: Any) -> SDL2Texture:
        try:
            ext_texture = self._sdl2.ext.Texture(self._handle, surface)
        except Exception:
            raise BackendError(f"SDL could not create the texture: {self._error()}")
        try:
            # Alpha blending honors transparency; nearest scaling keeps
            # pixel-art textures crisp.
            self._sdl2.render.SDL_SetTextureBlendMode(
                ext_texture.tx, self._sdl2.blendmode.SDL_BLENDMODE_BLEND
            )
            self._sdl2.render.SDL_SetTextureScaleMode(
                ext_texture.tx, self._sdl2.render.SDL_ScaleModeNearest
            )
        except Exception:
            pass
        width, height = ext_texture.size
        return SDL2Texture(self, ext_texture, int(width), int(height))

    def create_texture_from_pixels(
        self, width: int, height: int, pixels: bytes
    ) -> BackendTexture:
        if not isinstance(pixels, (bytes, bytearray, memoryview)):
            raise BackendError("pixels must be a bytes-like RGBA pixel buffer.")
        if len(pixels) != width * height * 4:
            raise BackendError(
                f"pixel buffer length {len(pixels)} does not match "
                f"{width}x{height}x4 RGBA data."
            )
        # RGBA byte order on little-endian: R is the least-significant byte.
        surface = self._sdl2.surface.SDL_CreateRGBSurfaceFrom(
            bytes(pixels),
            int(width),
            int(height),
            32,
            int(width * 4),
            0x000000FF,
            0x0000FF00,
            0x00FF0000,
            0xFF000000,
        )
        if not surface:
            raise BackendError(f"SDL could not create a surface: {self._error()}")
        try:
            return self._make_sdl_texture(surface)
        finally:
            self._sdl2.surface.SDL_FreeSurface(surface)

    def create_texture_from_image(self, image: BackendImage) -> BackendTexture:
        if not isinstance(image, SDL2Image):
            raise BackendError("SDL2Renderer requires an SDL2 backend image.")
        if image._ptr is None:
            raise RuntimeError("Cannot create a texture from a destroyed image.")
        return self._make_sdl_texture(image._ptr)

    def draw_texture(
        self,
        texture: BackendTexture,
        src_rect: tuple[int, int, int, int] | None,
        dst_rect: tuple[int, int, int, int],
        alpha: int,
        angle: float = 0,
        center: tuple[int, int] | None = None,
        flip: int = 0,
        color_mod: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        if not isinstance(texture, SDL2Texture):
            raise BackendError("SDL2Renderer can only draw SDL2 textures.")
        self._sdl2.render.SDL_SetTextureAlphaMod(texture._texture.tx, int(alpha))
        self._sdl2.render.SDL_SetTextureColorMod(
            texture._texture.tx, int(color_mod[0]), int(color_mod[1]), int(color_mod[2])
        )
        if src_rect is None:
            srcrect = None
        else:
            x, y, w, h = src_rect
            srcrect = self._sdl2.SDL_Rect(int(x), int(y), int(w), int(h))
        dx, dy, dw, dh = dst_rect
        self._handle.copy(
            texture._texture,
            srcrect,
            (int(dx), int(dy), int(dw), int(dh)),
            angle=float(angle),
            center=(
                (int(center[0]), int(center[1])) if center is not None else None
            ),
            flip=int(flip),
        )

    def destroy_texture(self, texture: BackendTexture) -> None:
        if isinstance(texture, SDL2Texture):
            texture.destroy()


class SDL2Backend(Backend):
    """Window creation, rendering, and event polling through SDL2."""

    name = "sdl2"

    def __init__(self) -> None:
        self._sdl2: Any = None
        self._ext: Any = None
        self._ttf: Any = None
        self._mixer: Any = None
        self._initialized = False
        self._fonts: dict[tuple[str, int], BackendFont] = {}
        self._sounds: list[BackendSound] = []
        self._musics: list[BackendMusic] = []
        self._audio_open = False
        self._current_music: SDL2Music | None = None
        self._master_volume = 1.0
        self._sound_volume = 1.0
        self._music_volume = 1.0

    def _import(self) -> tuple[Any, Any]:
        if self._sdl2 is not None:
            return self._sdl2, self._ext
        try:
            import sdl2
            import sdl2.ext
            import sdl2.sdlmixer
            import sdl2.sdlttf
        except (ImportError, OSError) as exc:
            raise BackendError(
                _INSTALL_HINT + f"Underlying error: {exc}"
            ) from exc
        self._sdl2 = sdl2
        self._ext = sdl2.ext
        self._ttf = sdl2.sdlttf
        self._mixer = sdl2.sdlmixer
        return sdl2, sdl2.ext

    def is_available(self) -> bool:
        try:
            self._import()
        except BackendError:
            return False
        return True

    def init(self) -> None:
        if self._initialized:
            return
        sdl2, _ = self._import()
        if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
            error = self._error_text(sdl2)
            raise BackendError(f"SDL2 video initialization failed: {error}")
        ttf = self._ttf
        if ttf.TTF_Init() != 0:
            error = self._error_text(sdl2)
            self._initialized = False
            raise BackendError(f"SDL2_ttf initialization failed: {error}")
        self._initialized = True

    def quit(self) -> None:
        if self._audio_open:
            self.close_audio()
        if self._initialized:
            for font in list(self._fonts.values()):
                font.destroy()
            self._fonts.clear()
            self._ttf.TTF_Quit()
            sdl2, _ = self._import()
            sdl2.SDL_Quit()
            self._initialized = False

    def create_window(self, title: str, width: int, height: int) -> BackendWindow:
        _, ext = self._import()
        if not self._initialized:
            self.init()
        window = ext.Window(title, size=(width, height))
        window.show()
        return SDL2Window(window)

    def create_renderer(self, window: BackendWindow) -> BackendRenderer:
        sdl2, ext = self._import()
        if not isinstance(window, SDL2Window):
            raise BackendError("SDL2Renderer requires an SDL2 backend window.")
        try:
            renderer = ext.Renderer(window._handle)
        except Exception:
            # Fall back to the software renderer when no hardware-accelerated
            # driver is available for this window.
            renderer = ext.Renderer(window._handle, flags=1)
        return SDL2Renderer(renderer, sdl2)

    def load_image(self, path: str) -> BackendImage:
        sdl2, _ = self._import()
        self.init()
        if not isinstance(path, str) or not path.strip():
            raise BackendError("Image path must be a non-empty string.")
        fullpath = os.path.abspath(path)
        if not os.path.isfile(fullpath):
            raise MissingAssetError(missing_asset_message(fullpath), path=fullpath)
        if fullpath.lower().endswith(".bmp"):
            # BMP loading is part of the core SDL2 library.
            pointer = sdl2.surface.SDL_LoadBMP(_byteify(fullpath))
        else:
            # PNG/JPG/etc. go through SDL_image (bundled by pysdl2-dll).
            img = sdl2.sdlimage
            img.IMG_Init(img.IMG_INIT_PNG | img.IMG_INIT_JPG | img.IMG_INIT_TIF | img.IMG_INIT_WEBP)
            pointer = img.IMG_Load(_byteify(fullpath))
        if not pointer:
            error = self._error_text(sdl2)
            sdl2.error.SDL_ClearError()
            raise BackendError(f"Unable to load image {path!r}: {error}")
        return SDL2Image(self, pointer)

    def load_font(self, path: str, size: int) -> BackendFont:
        sdl2, _ = self._import()
        self.init()
        if not isinstance(path, str) or not path.strip():
            raise BackendError("Font path must be a non-empty string.")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise BackendError("Font size must be a positive integer.")
        fullpath = os.path.abspath(path)
        if not os.path.isfile(fullpath):
            raise MissingAssetError(missing_asset_message(fullpath), path=fullpath)
        key = (fullpath, size)
        font = self._fonts.get(key)
        if font is not None:
            return font
        pointer = self._ttf.TTF_OpenFont(_byteify(fullpath), int(size))
        if not pointer:
            error = self._error_text(sdl2)
            sdl2.error.SDL_ClearError()
            raise BackendError(f"Unable to load font {path!r}: {error}")
        font = SDL2Font(self, pointer, int(size))
        self._fonts[key] = font
        return font

    def open_audio(self) -> None:
        if self._audio_open:
            return
        sdl2, _ = self._import()
        if not self._initialized:
            self.init()
        mixer = self._mixer
        # Register decoders (OGG, MP3, etc.) that the bundled SDL_mixer
        # provides; the flags are best-effort and unavailable codecs are
        # simply not registered.
        mixer.Mix_Init(mixer.MIX_INIT_OGG | mixer.MIX_INIT_MP3)
        if mixer.Mix_OpenAudio(44100, mixer.MIX_DEFAULT_FORMAT, 2, 1024) == -1:
            error = self._mixer_error()
            mixer.Mix_Quit()
            raise BackendError(f"SDL_mixer could not open an audio device: {error}")
        self._audio_open = True
        mixer.Mix_VolumeMusic(round(self._music_volume * 128))

    def close_audio(self) -> None:
        if not self._audio_open:
            return
        self.stop_all()
        mixer = self._mixer
        for sound in list(self._sounds):
            sound.destroy()
        self._sounds.clear()
        for music in list(self._musics):
            music.destroy()
        self._musics.clear()
        mixer.Mix_CloseAudio()
        mixer.Mix_Quit()
        self._audio_open = False
        self._current_music = None

    def load_sound(self, path: str) -> BackendSound:
        self.open_audio()
        if not isinstance(path, str) or not path.strip():
            raise BackendError("Sound path must be a non-empty string.")
        fullpath = os.path.abspath(path)
        if not os.path.isfile(fullpath):
            raise MissingAssetError(missing_asset_message(fullpath), path=fullpath)
        pointer = self._mixer.Mix_LoadWAV(_byteify(fullpath))
        if not pointer:
            error = self._mixer_error()
            self._mixer.Mix_ClearError()
            raise BackendError(f"Unable to load sound {path!r}: {error}")
        sound = SDL2Sound(self, pointer, fullpath)
        self._sounds.append(sound)
        return sound

    def load_music(self, path: str) -> BackendMusic:
        self.open_audio()
        if not isinstance(path, str) or not path.strip():
            raise BackendError("Music path must be a non-empty string.")
        fullpath = os.path.abspath(path)
        if not os.path.isfile(fullpath):
            raise MissingAssetError(missing_asset_message(fullpath), path=fullpath)
        pointer = self._mixer.Mix_LoadMUS(_byteify(fullpath))
        if not pointer:
            error = self._mixer_error()
            self._mixer.Mix_ClearError()
            raise BackendError(f"Unable to load music {path!r}: {error}")
        music = SDL2Music(self, pointer, fullpath)
        self._musics.append(music)
        return music

    def set_master_volume(self, volume: float) -> None:
        self._validate_volume(volume, "master")
        self._master_volume = volume
        if self._audio_open:
            self._mixer.Mix_MasterVolume(round(volume * 128))

    def master_volume(self) -> float:
        return self._master_volume

    def set_sound_volume(self, volume: float) -> None:
        self._validate_volume(volume, "sound")
        self._sound_volume = volume
        if self._audio_open:
            self._mixer.Mix_Volume(-1, round(volume * 128))

    def sound_volume(self) -> float:
        return self._sound_volume

    def set_music_volume(self, volume: float) -> None:
        self._validate_volume(volume, "music")
        self._music_volume = volume
        if self._current_music is not None:
            self._current_music._apply_volume()

    def music_volume(self) -> float:
        return self._music_volume

    def pause_all(self) -> None:
        if self._audio_open:
            self._mixer.Mix_Pause(-1)
            self._mixer.Mix_PauseMusic()

    def resume_all(self) -> None:
        if self._audio_open:
            self._mixer.Mix_Resume(-1)
            self._mixer.Mix_ResumeMusic()

    def stop_all(self) -> None:
        if self._audio_open:
            self._mixer.Mix_HaltChannel(-1)
            self._mixer.Mix_HaltMusic()

    @staticmethod
    def _validate_volume(volume: float, which: str) -> None:
        if isinstance(volume, bool) or not isinstance(volume, (int, float)):
            raise BackendError(f"{which} volume must be a number between 0.0 and 1.0.")
        if not 0.0 <= float(volume) <= 1.0:
            raise BackendError(f"{which} volume must be between 0.0 and 1.0.")

    def _mixer_error(self) -> str:
        raw = self._mixer.Mix_GetError()
        if raw is None:
            return "unknown SDL_mixer error"
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace").strip()
        return str(raw).strip()

    def mouse_position(self) -> tuple[int, int]:
        sdl2, _ = self._import()
        x = sdl2.Sint32(0)
        y = sdl2.Sint32(0)
        sdl2.SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))
        return int(x.value), int(y.value)

    def poll_events(self) -> list[BackendEvent]:
        sdl2, _ = self._import()
        events: list[BackendEvent] = []
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            event_type = event.type
            if event_type == sdl2.SDL_QUIT:
                events.append(BackendEvent("quit"))
            elif event_type == sdl2.SDL_WINDOWEVENT:
                if event.window.event == sdl2.SDL_WINDOWEVENT_CLOSE:
                    events.append(BackendEvent("window_close"))
                elif event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED:
                    events.append(
                        BackendEvent(
                            "window_resized",
                            {"width": int(event.window.data1), "height": int(event.window.data2)},
                        )
                    )
            elif event_type == sdl2.SDL_KEYDOWN:
                key = _key_name(sdl2, int(event.key.keysym.scancode))
                if key is not None:
                    events.append(
                        BackendEvent(
                            "key_down",
                            {"key": key, "repeat": bool(event.key.repeat)},
                        )
                    )
            elif event_type == sdl2.SDL_KEYUP:
                key = _key_name(sdl2, int(event.key.keysym.scancode))
                if key is not None:
                    events.append(BackendEvent("key_up", {"key": key}))
            elif event_type == sdl2.SDL_TEXTINPUT:
                raw = bytes(event.text.text)
                text = raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
                if text:
                    events.append(BackendEvent("text_input", {"text": text}))
            elif event_type == sdl2.SDL_MOUSEMOTION:
                events.append(
                    BackendEvent(
                        "mouse_motion",
                        {
                            "x": int(event.motion.x),
                            "y": int(event.motion.y),
                            "dx": int(event.motion.xrel),
                            "dy": int(event.motion.yrel),
                        },
                    )
                )
            elif event_type == sdl2.SDL_MOUSEBUTTONDOWN:
                name = _button_name(int(event.button.button))
                if name is not None:
                    events.append(
                        BackendEvent(
                            "mouse_button_down",
                            {"button": name, "x": int(event.button.x), "y": int(event.button.y)},
                        )
                    )
            elif event_type == sdl2.SDL_MOUSEBUTTONUP:
                name = _button_name(int(event.button.button))
                if name is not None:
                    events.append(
                        BackendEvent(
                            "mouse_button_up",
                            {"button": name, "x": int(event.button.x), "y": int(event.button.y)},
                        )
                    )
        return events

    @staticmethod
    def _error_text(sdl2: Any) -> str:
        raw = sdl2.SDL_GetError()
        if raw is None:
            return "unknown SDL error"
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace").strip()
        return str(raw).strip()