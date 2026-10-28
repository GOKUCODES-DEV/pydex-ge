"""Loading / splash-screen subsystem for PYDEX.

:class:`SplashScreen` is a :class:`~pydex_ge.scene.scene.Scene` that shows a
logo and loading progress while game resources are silently checked and
loaded, then auto-transitions to the next scene.
"""

from .splash import SplashScreen

__all__ = ["SplashScreen"]
