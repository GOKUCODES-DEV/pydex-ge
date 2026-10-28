"""Keyboard and mouse input for PYDEX.

The :class:`Input` object reads normalized engine events (fed by the game
loop) and exposes friendly, frame-aware state: whether a key or button was
pressed *this frame*, released this frame, or is currently held.  It also
tracks the mouse position and movement.

Key names are lowercase strings like ``"e"``, ``"escape"``, ``"space"``,
``"left"``, or ``"a"``.  The :class:`Keys` constants class provides the
common ones so you never need SDL key codes.
"""

from __future__ import annotations

from ..backend import select_backend
from ..backend.base import Backend
from ..core.events import EventType


class Keys:
    """Friendly, human-readable names for the most common keyboard keys."""

    ESCAPE = "escape"
    ENTER = "enter"
    RETURN = "enter"
    SPACE = "space"
    BACKSPACE = "backspace"
    TAB = "tab"
    DELETE = "delete"
    HOME = "home"
    END = "end"
    PAGE_UP = "pageup"
    PAGE_DOWN = "pagedown"
    INSERT = "insert"
    CAPS_LOCK = "capslock"
    SHIFT = "shift"
    CONTROL = "control"
    ALT = "alt"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"
    H = "h"
    I = "i"
    J = "j"
    K = "k"
    L = "l"
    M = "m"
    N = "n"
    O = "o"
    P = "p"
    Q = "q"
    R = "r"
    S = "s"
    T = "t"
    U = "u"
    V = "v"
    W = "w"
    X = "x"
    Y = "y"
    Z = "z"
    ZERO = "0"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    PERIOD = "."
    COMMA = ","
    SLASH = "/"
    SEMICOLON = ";"
    APOSTROPHE = "'"
    LEFT_BRACKET = "["
    RIGHT_BRACKET = "]"
    BACKSLASH = "\\"
    MINUS = "-"
    EQUALS = "="
    BACKTICK = "`"
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"


def _normalize(name: object) -> str | None:
    """Lowercase and strip a key/button name, returning None for garbage."""
    if not isinstance(name, str):
        return None
    normalized = name.strip().lower()
    return normalized or None


class Input:
    """Frame-aware keyboard and mouse state.

    You normally access this through ``game.input``.  The game loop calls
    :meth:`begin_frame` once per frame and feeds each engine event to
    :meth:`handle_event`; afterwards you query state.

    ``pressed`` means the key/button went down during the current frame.
    ``released`` means it went up during the current frame.  ``down`` (and
    the alias ``held``) means the key/button is currently held.
    """

    def __init__(self, backend: Backend | None = None) -> None:
        self._backend = backend if backend is not None else select_backend()
        self._keys_pressed: set[str] = set()
        self._keys_released: set[str] = set()
        self._keys_down: set[str] = set()
        self._buttons_pressed: set[str] = set()
        self._buttons_released: set[str] = set()
        self._buttons_down: set[str] = set()
        self._mouse_position = (0, 0)
        self._mouse_delta = (0, 0)
        self._text: list[str] = []

    def begin_frame(self) -> None:
        """Reset per-frame state.  Call once at the start of every frame."""
        self._keys_pressed.clear()
        self._keys_released.clear()
        self._buttons_pressed.clear()
        self._buttons_released.clear()
        self._mouse_delta = (0, 0)
        self._text.clear()
        self._mouse_position = self._backend.mouse_position()

    def handle_event(self, event) -> None:
        """Feed a normalized engine event into the input state."""
        if event.type is EventType.KEY_DOWN:
            key = _normalize(event.data.get("key"))
            if key is not None:
                self._keys_down.add(key)
                if not event.data.get("repeat"):
                    self._keys_pressed.add(key)
        elif event.type is EventType.KEY_UP:
            key = _normalize(event.data.get("key"))
            if key is not None:
                self._keys_down.discard(key)
                self._keys_released.add(key)
        elif event.type is EventType.TEXT_INPUT:
            text = event.data.get("text")
            if isinstance(text, str) and text:
                self._text.append(text)
        elif event.type is EventType.MOUSE_MOTION:
            self._mouse_position = (event.data["x"], event.data["y"])
            self._mouse_delta = (event.data.get("dx", 0), event.data.get("dy", 0))
        elif event.type is EventType.MOUSE_BUTTON_DOWN:
            button = _normalize(event.data.get("button"))
            if button is not None:
                self._buttons_down.add(button)
                self._buttons_pressed.add(button)
                self._mouse_position = (event.data.get("x", 0), event.data.get("y", 0))
        elif event.type is EventType.MOUSE_BUTTON_UP:
            button = _normalize(event.data.get("button"))
            if button is not None:
                self._buttons_down.discard(button)
                self._buttons_released.add(button)
                self._mouse_position = (event.data.get("x", 0), event.data.get("y", 0))

    def is_key_pressed(self, key: object) -> bool:
        """True when the key went down during the current frame."""
        normalized = _normalize(key)
        return normalized is not None and normalized in self._keys_pressed

    def is_key_released(self, key: object) -> bool:
        """True when the key went up during the current frame."""
        normalized = _normalize(key)
        return normalized is not None and normalized in self._keys_released

    def is_key_down(self, key: object) -> bool:
        """True while the key is held down."""
        normalized = _normalize(key)
        return normalized is not None and normalized in self._keys_down

    def is_key_held(self, key: object) -> bool:
        """Alias for :meth:`is_key_down`."""
        return self.is_key_down(key)

    def is_button_pressed(self, button: object) -> bool:
        """True when the mouse button went down during the current frame."""
        normalized = _normalize(button)
        return normalized is not None and normalized in self._buttons_pressed

    def is_button_released(self, button: object) -> bool:
        """True when the mouse button went up during the current frame."""
        normalized = _normalize(button)
        return normalized is not None and normalized in self._buttons_released

    def is_button_down(self, button: object) -> bool:
        """True while the mouse button is held down."""
        normalized = _normalize(button)
        return normalized is not None and normalized in self._buttons_down

    @property
    def mouse_position(self) -> tuple[int, int]:
        """The mouse position in window coordinates as ``(x, y)``."""
        return self._mouse_position

    @property
    def mouse_x(self) -> int:
        """The mouse X coordinate in window coordinates."""
        return self._mouse_position[0]

    @property
    def mouse_y(self) -> int:
        """The mouse Y coordinate in window coordinates."""
        return self._mouse_position[1]

    @property
    def mouse_delta(self) -> tuple[int, int]:
        """The mouse movement during the current frame as ``(dx, dy)``."""
        return self._mouse_delta

    @property
    def typed_text(self) -> str:
        """The text typed during the current frame (via ``TEXT_INPUT``).

        Shift and layout are already applied by the OS, so ``'a' + shift``
        arrives as ``'A'``.
        """
        return "".join(self._text)

    @property
    def text_events(self) -> list[str]:
        """The individual text chunks typed during the current frame."""
        return list(self._text)


__all__ = ["Input", "Keys"]
