"""Event system foundation.

The :class:`EventManager` polls the active backend and converts its
normalized :class:`~pydex_ge.backend.base.BackendEvent` objects into engine
:class:`Event` objects, so core code never depends on SDL details.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..backend import select_backend
from ..backend.base import Backend, BackendEvent


class EventType(Enum):
    """Kinds of events PYDEX currently understands."""

    QUIT = "quit"
    WINDOW_CLOSE = "window_close"
    WINDOW_RESIZED = "window_resized"
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    TEXT_INPUT = "text_input"
    MOUSE_MOTION = "mouse_motion"
    MOUSE_BUTTON_DOWN = "mouse_button_down"
    MOUSE_BUTTON_UP = "mouse_button_up"


_TYPE_MAP: dict[str, EventType] = {
    "quit": EventType.QUIT,
    "window_close": EventType.WINDOW_CLOSE,
    "window_resized": EventType.WINDOW_RESIZED,
    "key_down": EventType.KEY_DOWN,
    "key_up": EventType.KEY_UP,
    "text_input": EventType.TEXT_INPUT,
    "mouse_motion": EventType.MOUSE_MOTION,
    "mouse_button_down": EventType.MOUSE_BUTTON_DOWN,
    "mouse_button_up": EventType.MOUSE_BUTTON_UP,
}


@dataclass(frozen=True)
class Event:
    """A single engine event, independent of the backing OS library."""

    type: EventType
    data: Mapping[str, Any] = field(default_factory=dict)


class EventManager:
    """Buffers OS events as PYDEX :class:`Event` objects.

    Call :meth:`poll` once per frame, then read queued events with
    :meth:`get` or by iterating.  The quit flag can be checked with
    :meth:`has_quit`.
    """

    def __init__(self, backend: Backend | None = None) -> None:
        self._backend = backend if backend is not None else select_backend()
        self._queue: deque[Event] = deque()

    def poll(self) -> None:
        """Pull pending backend events into the internal queue."""
        for raw in self._backend.poll_events():
            translated = self._translate(raw)
            if translated is not None:
                self._queue.append(translated)

    def get(self) -> Event | None:
        """Return the oldest queued event, or ``None`` when empty."""
        return self._queue.popleft() if self._queue else None

    def __iter__(self) -> Iterable[Event]:
        """Iterate over queued events, draining the queue."""
        while self._queue:
            yield self._queue.popleft()

    def clear(self) -> None:
        """Drop all queued events."""
        self._queue.clear()

    def has_quit(self) -> bool:
        """True when a quit event is currently queued."""
        return self.has(EventType.QUIT)

    def has(self, event_type: EventType) -> bool:
        """True when at least one event of the given type is queued."""
        return any(event.type is event_type for event in self._queue)

    @staticmethod
    def _translate(raw: BackendEvent) -> Event | None:
        event_type = _TYPE_MAP.get(raw.type)
        if event_type is None:
            return None
        return Event(type=event_type, data=raw.data)


__all__ = ["Event", "EventManager", "EventType"]