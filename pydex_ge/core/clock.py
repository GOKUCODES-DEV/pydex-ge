"""Timing helpers for PYDEX, built on ``time.perf_counter``."""

from __future__ import annotations

import time


class Clock:
    """Simple, monotonic timing helper.

    Call :meth:`tick` once per frame; pass an FPS cap to make the loop
    pause so it does not run faster than that rate.
    """

    def __init__(self) -> None:
        self._started = time.perf_counter()
        self._previous: float | None = None
        self._last_dt = 0.0

    def tick(self, fps: float | int | None = None) -> float:
        """Advance the clock by one frame.

        Returns the delta time in seconds since the previous call
        (``0.0`` on the first call).  If ``fps`` is given and positive,
        the call sleeps as needed to target that frame rate; the sleep
        time is included in the returned delta.
        """
        now = time.perf_counter()
        if self._previous is None:
            self._previous = now
            self._last_dt = 0.0
            return 0.0

        elapsed = now - self._previous
        if fps and fps > 0:
            target = 1.0 / fps
            if elapsed < target:
                time.sleep(target - elapsed)
                elapsed = target
        self._previous = time.perf_counter()
        self._last_dt = elapsed
        return elapsed

    def get_time(self) -> float:
        """Seconds elapsed since this clock was created."""
        return time.perf_counter() - self._started

    @property
    def fps(self) -> float:
        """Frames per second implied by the most recent :meth:`tick`.

        Returns ``0.0`` before the first tick.
        """
        return 1.0 / self._last_dt if self._last_dt else 0.0


__all__ = ["Clock"]