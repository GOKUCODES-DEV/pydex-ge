"""The headless backend, for tests and machines without a display.

It manages window/close state in memory only and never produces events.
Select it explicitly with ``PYDEX_BACKEND=null`` or pass a
:class:`NullBackend` instance to the object you are constructing.

Image loading only parses enough of the PNG/JPG/BMP file headers to report
the correct width and height; no pixel data is decoded.  Pixel sprites
created with ``Sprite.from_pixels`` still carry their full RGBA buffers and
render fully in memory for headless tests.
"""

from __future__ import annotations

import os

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


def _validate_volume(volume: float, which: str) -> None:
    if isinstance(volume, bool) or not isinstance(volume, (int, float)):
        raise BackendError(f"{which} volume must be a number between 0.0 and 1.0.")
    if not 0.0 <= float(volume) <= 1.0:
        raise BackendError(f"{which} volume must be between 0.0 and 1.0.")


def _bmp_size(data: bytes) -> tuple[int, int]:
    if len(data) < 26 or data[:2] != b"BM":
        raise ValueError("not a BMP file")
    width = int.from_bytes(data[18:22], "little")
    height = abs(int.from_bytes(data[22:26], "little", signed=True))
    if width <= 0 or height <= 0:
        raise ValueError("BMP has invalid dimensions")
    return width, height


def _png_size(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    if data[12:16] != b"IHDR":
        raise ValueError("PNG is missing its IHDR header")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        raise ValueError("PNG has invalid dimensions")
    return width, height


_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
}


def _jpeg_size(data: bytes) -> tuple[int, int]:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG file")
    i = 2
    size = len(data)
    while i + 4 <= size:
        if data[i] != 0xFF:
            raise ValueError("malformed JPEG marker stream")
        marker = data[i + 1]
        i += 2
        if marker == 0xD9:  # end of image
            break
        # Standalone markers: TEM (0x01) and RST0..RST7 (0xD0-0xD7).
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue
        if i + 2 > size:
            break
        length = int.from_bytes(data[i:i + 2], "big")
        if length < 2:
            raise ValueError("malformed JPEG segment length")
        seg = i + 2
        end = seg + length - 2
        if end > size:
            end = size
        if marker in _SOF_MARKERS:
            if end - seg >= 5:
                height = int.from_bytes(data[seg + 1:seg + 3], "big")
                width = int.from_bytes(data[seg + 3:seg + 5], "big")
                if width > 0 and height > 0:
                    return width, height
            raise ValueError("JPEG SOF segment is malformed")
        i = end
    raise ValueError("no dimensions found in JPEG data")


def _image_dimensions(data: bytes, path: str) -> tuple[int, int]:
    if data[:2] == b"BM":
        return _bmp_size(data)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return _png_size(data)
    if data[:2] == b"\xff\xd8":
        return _jpeg_size(data)
    extension = os.path.splitext(path)[1].lower()
    raise ValueError(f"unsupported image format {extension or 'unknown'!r}")


class NullWindow(BackendWindow):
    """A window handle that does not create anything on screen."""

    def __init__(self) -> None:
        self._closed = False

    def close(self) -> None:
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed


class NullImage(BackendImage):
    """An image whose dimensions are read from the file header only."""

    def __init__(self, path: str, width: int, height: int) -> None:
        self.path = os.path.abspath(path)
        self._width = width
        self._height = height

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def destroy(self) -> None:
        pass  # No decoded pixels are held, so there is nothing to free.


class NullTexture(BackendTexture):
    """An in-memory texture; pixel sprites keep their RGBA buffer."""

    def __init__(
        self, width: int, height: int, pixels: bytes | None = None
    ) -> None:
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


class NullFont(BackendFont):
    """A font that only knows its size; text dimensions are estimated.

    The headless backend never decodes pixels, so rendered text images are
    just dimension boxes and text width is approximated from the character
    count.  Enough for layout logic and tests without a display.
    """

    def __init__(self, backend: NullBackend, size: int) -> None:
        self._backend = backend
        self._size = size
        self._destroyed = False

    @property
    def size(self) -> int:
        return self._size

    def _check(self) -> None:
        if self._destroyed:
            raise RuntimeError("Cannot use a font after it has been destroyed.")

    def measure_text(self, text: str) -> tuple[int, int]:
        self._check()
        if not isinstance(text, str):
            raise BackendError("Text must be a string.")
        width = round(len(text) * self._size * 0.6) if text else 0
        return width, self._size

    def render_text(self, text: str, color: tuple[int, int, int, int]) -> BackendImage:
        self._check()
        if not isinstance(text, str):
            raise BackendError("Text must be a string.")
        width, height = self.measure_text(text)
        return NullImage("<text>", max(width, 1), max(height, 1))

    def destroy(self) -> None:
        self._backend._fonts = {
            key: font
            for key, font in self._backend._fonts.items()
            if font is not self
        }
        self._destroyed = True


class NullSound(BackendSound):
    """An in-memory sound effect that simulates playback state.

    No audio is produced; ``play``/``pause``/``resume``/``stop`` just update
    the tracked state so headless tests can exercise the full audio API.
    """

    def __init__(self, backend: NullBackend, path: str) -> None:
        self._backend = backend
        self._path = path
        self._volume = 1.0
        self._playing = False
        self._paused = False
        self._destroyed = False

    def _check(self) -> None:
        if self._destroyed:
            raise RuntimeError("Cannot use a sound after it has been destroyed.")

    def play(self, loop: bool = False) -> None:
        self._check()
        self._playing = True
        self._paused = False

    def stop(self) -> None:
        self._check()
        self._playing = False
        self._paused = False

    def pause(self) -> None:
        self._check()
        if self._playing:
            self._paused = True

    def resume(self) -> None:
        self._check()
        self._paused = False

    def set_volume(self, volume: float) -> None:
        self._check()
        _validate_volume(volume, "sound")
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


class NullMusic(BackendMusic):
    """An in-memory music track that simulates playback state."""

    def __init__(self, backend: NullBackend, path: str) -> None:
        self._backend = backend
        self._path = path
        self._volume = 1.0
        self._playing = False
        self._paused = False
        self._destroyed = False

    def _check(self) -> None:
        if self._destroyed:
            raise RuntimeError("Cannot use music after it has been destroyed.")

    def play(self, loop: bool = True) -> None:
        self._check()
        self._playing = True
        self._paused = False

    def stop(self) -> None:
        self._check()
        self._playing = False
        self._paused = False

    def pause(self) -> None:
        self._check()
        if self._playing:
            self._paused = True

    def resume(self) -> None:
        self._check()
        self._paused = False

    def set_volume(self, volume: float) -> None:
        self._check()
        _validate_volume(volume, "music")
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


class NullRenderer(BackendRenderer):
    """A renderer that draws nothing; used only for headless runs.

    Texture draws are recorded in :attr:`texture_draws` so headless tests
    can verify sprite sizing, position, and alpha without a display.
    """

    def __init__(self) -> None:
        self.texture_draws: list[
            tuple[BackendTexture, tuple[int, int, int, int] | None, tuple[int, int, int, int], int]
        ] = []
        self.transformed_draws: list[
            tuple[
                BackendTexture,
                tuple[int, int, int, int] | None,
                tuple[int, int, int, int],
                int,
                float,
                tuple[int, int] | None,
                int,
                tuple[int, int, int],
            ]
        ] = []
        self._textures: list[NullTexture] = []

    def clear(self, r: int, g: int, b: int, a: int = 255) -> None:
        pass

    def present(self) -> None:
        pass

    def destroy(self) -> None:
        pass

    def draw_pixel(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        pass

    def draw_line(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple[int, int, int, int],
    ) -> None:
        pass

    def draw_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int, int],
        filled: bool = True,
    ) -> None:
        pass

    def draw_circle(
        self,
        x: int,
        y: int,
        radius: int,
        color: tuple[int, int, int, int],
        filled: bool = True,
    ) -> None:
        pass

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
        texture = NullTexture(width, height, bytes(pixels))
        self._textures.append(texture)
        return texture

    def create_texture_from_image(self, image: BackendImage) -> BackendTexture:
        if not isinstance(image, NullImage):
            raise BackendError("NullRenderer requires a null backend image.")
        texture = NullTexture(image.width, image.height)
        self._textures.append(texture)
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
        if isinstance(texture, NullTexture):
            texture.destroy()


class NullBackend(Backend):
    """A no-op backend useful for headless tests and CI."""

    name = "null"

    def __init__(self) -> None:
        self._initialized = False
        self._fonts: dict[tuple[str, int], BackendFont] = {}
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
        return NullWindow()

    def create_renderer(self, window: BackendWindow) -> BackendRenderer:
        return NullRenderer()

    def load_image(self, path: str) -> BackendImage:
        if not isinstance(path, str) or not path.strip():
            raise BackendError("Image path must be a non-empty string.")
        fullpath = os.path.abspath(path)
        if not os.path.isfile(fullpath):
            raise MissingAssetError(missing_asset_message(fullpath), path=fullpath)
        with open(fullpath, "rb") as handle:
            data = handle.read()
        try:
            width, height = _image_dimensions(data, fullpath)
        except ValueError as exc:
            raise BackendError(f"Unable to parse image {path!r}: {exc}") from exc
        return NullImage(fullpath, width, height)

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
        font = NullFont(self, int(size))
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
        sound = NullSound(self, fullpath)
        self._sounds.append(sound)
        return sound

    def load_music(self, path: str) -> BackendMusic:
        self.open_audio()
        if not isinstance(path, str) or not path.strip():
            raise BackendError("Music path must be a non-empty string.")
        fullpath = os.path.abspath(path)
        if not os.path.isfile(fullpath):
            raise MissingAssetError(missing_asset_message(fullpath), path=fullpath)
        music = NullMusic(self, fullpath)
        self._musics.append(music)
        return music

    def set_master_volume(self, volume: float) -> None:
        _validate_volume(volume, "master")
        self._master_volume = float(volume)

    def master_volume(self) -> float:
        return self._master_volume

    def set_sound_volume(self, volume: float) -> None:
        _validate_volume(volume, "sound")
        self._sound_volume = float(volume)

    def sound_volume(self) -> float:
        return self._sound_volume

    def set_music_volume(self, volume: float) -> None:
        _validate_volume(volume, "music")
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

    def poll_events(self) -> list[BackendEvent]:
        return []

    def mouse_position(self) -> tuple[int, int]:
        return (0, 0)