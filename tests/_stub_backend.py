"""Shared, in-memory backend used by the event tests.

Stays out of the ``pydex_ge`` package so tests exercise PYDEX's public
abstraction rather than implementation details.
"""

from __future__ import annotations

import os

from pydex_ge.backend.base import (
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
from pydex_ge.exceptions import BackendError, MissingAssetError, missing_asset_message


class StubSound(BackendSound):
    def __init__(self, backend: StubBackend, path: str) -> None:
        self._backend = backend
        self.path = path
        self._volume = 1.0
        self._playing = False
        self._paused = False
        self._destroyed = False

    def play(self, loop: bool = False) -> None:
        self._playing = True
        self._paused = False

    def stop(self) -> None:
        self._playing = False
        self._paused = False

    def pause(self) -> None:
        if self._playing:
            self._paused = True

    def resume(self) -> None:
        self._paused = False

    def set_volume(self, volume: float) -> None:
        self._volume = float(volume)

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def paused(self) -> bool:
        return self._paused

    def destroy(self) -> None:
        self._backend._sounds = [
            sound for sound in self._backend._sounds if sound is not self
        ]
        self._destroyed = True


class StubMusic(BackendMusic):
    def __init__(self, backend: StubBackend, path: str) -> None:
        self._backend = backend
        self.path = path
        self._volume = 1.0
        self._playing = False
        self._paused = False
        self._destroyed = False

    def play(self, loop: bool = True) -> None:
        self._playing = True
        self._paused = False

    def stop(self) -> None:
        self._playing = False
        self._paused = False

    def pause(self) -> None:
        if self._playing:
            self._paused = True

    def resume(self) -> None:
        self._paused = False

    def set_volume(self, volume: float) -> None:
        self._volume = float(volume)

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def paused(self) -> bool:
        return self._paused

    def destroy(self) -> None:
        self._backend._musics = [
            music for music in self._backend._musics if music is not self
        ]
        self._destroyed = True


class StubImage(BackendImage):
    def __init__(self, path: str, width: int, height: int) -> None:
        self.path = path
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
        self._destroyed = True


class StubTexture(BackendTexture):
    def __init__(self, width: int, height: int, pixels: bytes | None = None) -> None:
        self._width = width
        self._height = height
        self.pixels = bytes(pixels) if pixels is not None else None
        self._destroyed = False

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def destroy(self) -> None:
        self._destroyed = True


class StubFont(BackendFont):
    def __init__(self, backend: StubBackend, size: int) -> None:
        self._backend = backend
        self._size = size
        self._destroyed = False

    @property
    def size(self) -> int:
        return self._size

    def measure_text(self, text: str) -> tuple[int, int]:
        return round(len(text) * self._size * 0.6) if text else 0, self._size

    def render_text(self, text: str, color: tuple[int, int, int, int]) -> BackendImage:
        width, height = self.measure_text(text)
        return StubImage("<text>", max(width, 1), max(height, 1))

    def destroy(self) -> None:
        self._backend._fonts = {
            key: font for key, font in self._backend._fonts.items() if font is not self
        }
        self._destroyed = True


class StubWindow(BackendWindow):
    def __init__(self) -> None:
        self._closed = False

    def close(self) -> None:
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed


class StubRenderer(BackendRenderer):
    def __init__(self) -> None:
        self.clears: list[tuple[int, int, int, int]] = []
        self.presents = 0
        self.pixels: list[tuple[int, int, tuple[int, int, int, int]]] = []
        self.lines: list[tuple[int, int, int, int, tuple[int, int, int, int]]] = []
        self.rects: list[tuple[int, int, int, int, tuple[int, int, int, int], bool]] = []
        self.circles: list[tuple[int, int, int, tuple[int, int, int, int], bool]] = []
        self.textures: list[StubTexture] = []
        self.texture_draws: list[
            tuple[StubTexture, tuple[int, int, int, int] | None, tuple[int, int, int, int], int]
        ] = []
        self.transformed_draws: list[
            tuple[
                StubTexture,
                tuple[int, int, int, int] | None,
                tuple[int, int, int, int],
                int,
                float,
                tuple[int, int] | None,
                int,
                tuple[int, int, int],
            ]
        ] = []
        self._destroyed = False

    def clear(self, r: int, g: int, b: int, a: int = 255) -> None:
        self.clears.append((r, g, b, a))

    def present(self) -> None:
        self.presents += 1

    def destroy(self) -> None:
        self._destroyed = True

    def draw_pixel(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        self.pixels.append((x, y, color))

    def draw_line(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple[int, int, int, int],
    ) -> None:
        self.lines.append((x1, y1, x2, y2, color))

    def draw_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int, int],
        filled: bool = True,
    ) -> None:
        self.rects.append((x, y, width, height, color, filled))

    def draw_circle(
        self,
        x: int,
        y: int,
        radius: int,
        color: tuple[int, int, int, int],
        filled: bool = True,
    ) -> None:
        self.circles.append((x, y, radius, color, filled))

    def create_texture_from_pixels(
        self, width: int, height: int, pixels: bytes
    ) -> BackendTexture:
        texture = StubTexture(width, height, bytes(pixels))
        self.textures.append(texture)
        return texture

    def create_texture_from_image(self, image: BackendImage) -> BackendTexture:
        texture = StubTexture(image.width, image.height)
        self.textures.append(texture)
        return texture

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
        if (
            angle != 0
            or flip != 0
            or center not in (None, (0, 0))
            or color_mod != (255, 255, 255)
        ):
            self.transformed_draws.append(
                (texture, src_rect, dst_rect, alpha, angle, center, flip, color_mod)
            )
        else:
            self.texture_draws.append((texture, src_rect, dst_rect, alpha))

    def destroy_texture(self, texture: BackendTexture) -> None:
        if isinstance(texture, StubTexture):
            texture.destroy()


class StubBackend(Backend):
    """Backend that returns a preset list of events on each poll."""

    name = "stub"

    def __init__(
        self,
        events: list[BackendEvent] | None = None,
        image_sizes: dict[str, tuple[int, int]] | None = None,
    ) -> None:
        self._pending = list(events or [])
        self._initialized = False
        self.windows: list[BackendWindow] = []
        self.renderers: list[StubRenderer] = []
        self.images: list[StubImage] = []
        self.image_sizes = dict(image_sizes or {})
        self._fonts: dict[tuple[str, int], BackendFont] = {}
        self._mouse_position = (0, 0)
        self._sounds: list[BackendSound] = []
        self._musics: list[BackendMusic] = []
        self._audio_open = False
        self._master_volume = 1.0
        self._sound_volume = 1.0
        self._music_volume = 1.0

    def init(self) -> None:
        self._initialized = True

    def quit(self) -> None:
        self.close_audio()
        self._fonts.clear()
        self._initialized = False

    def is_available(self) -> bool:
        return True

    def create_window(self, title: str, width: int, height: int) -> BackendWindow:
        window = StubWindow()
        self.windows.append(window)
        return window

    def create_renderer(self, window: BackendWindow) -> BackendRenderer:
        renderer = StubRenderer()
        self.renderers.append(renderer)
        return renderer

    def load_image(self, path: str) -> BackendImage:
        if not isinstance(path, str) or not path.strip():
            raise BackendError("Image path must be a non-empty string.")
        fullpath = os.path.abspath(path)
        if not os.path.isfile(fullpath):
            raise MissingAssetError(missing_asset_message(fullpath), path=fullpath)
        width, height = self.image_sizes.get(fullpath, (16, 16))
        image = StubImage(fullpath, width, height)
        self.images.append(image)
        return image

    def poll_events(self) -> list[BackendEvent]:
        pending, self._pending = self._pending, []
        return pending
    def load_font(self, path: str, size: int) -> BackendFont:
        if not isinstance(path, str) or not path.strip():
            raise BackendError("Font path must be a non-empty string.")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise BackendError("Font size must be a positive integer.")
        fullpath = os.path.abspath(path)
        if not os.path.isfile(fullpath):
            raise MissingAssetError(missing_asset_message(fullpath), path=fullpath)
        key = (fullpath, int(size))
        font = self._fonts.get(key)
        if font is not None:
            return font
        font = StubFont(self, int(size))
        self._fonts[key] = font
        return font

    def open_audio(self) -> None:
        self._audio_open = True

    def close_audio(self) -> None:
        if not self._audio_open:
            return
        self.stop_all()
        for sound in list(self._sounds):
            sound.destroy()
        self._sounds.clear()
        for music in list(self._musics):
            music.destroy()
        self._musics.clear()
        self._audio_open = False

    def load_sound(self, path: str) -> BackendSound:
        self.open_audio()
        if not isinstance(path, str) or not path.strip():
            raise BackendError("Sound path must be a non-empty string.")
        fullpath = os.path.abspath(path)
        if not os.path.isfile(fullpath):
            raise MissingAssetError(missing_asset_message(fullpath), path=fullpath)
        sound = StubSound(self, fullpath)
        self._sounds.append(sound)
        return sound

    def load_music(self, path: str) -> BackendMusic:
        self.open_audio()
        if not isinstance(path, str) or not path.strip():
            raise BackendError("Music path must be a non-empty string.")
        fullpath = os.path.abspath(path)
        if not os.path.isfile(fullpath):
            raise MissingAssetError(missing_asset_message(fullpath), path=fullpath)
        music = StubMusic(self, fullpath)
        self._musics.append(music)
        return music

    def set_master_volume(self, volume: float) -> None:
        self._master_volume = float(volume)

    def master_volume(self) -> float:
        return self._master_volume

    def set_sound_volume(self, volume: float) -> None:
        self._sound_volume = float(volume)

    def sound_volume(self) -> float:
        return self._sound_volume

    def set_music_volume(self, volume: float) -> None:
        self._music_volume = float(volume)

    def music_volume(self) -> float:
        return self._music_volume

    def pause_all(self) -> None:
        for sound in self._sounds:
            sound.pause()
        for music in self._musics:
            music.pause()

    def resume_all(self) -> None:
        for sound in self._sounds:
            sound.resume()
        for music in self._musics:
            music.resume()

    def stop_all(self) -> None:
        for sound in self._sounds:
            sound.stop()
        for music in self._musics:
            music.stop()

    def mouse_position(self) -> tuple[int, int]:
        return self._mouse_position