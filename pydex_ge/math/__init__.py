"""Math helpers for the 3D Foundation.

This package holds the rotation math used by the CPU-side 3D subsystem.
It currently provides :class:`~pydex_ge.math.quaternion.Quaternion`.
"""

from .quaternion import Quaternion

__all__ = ["Quaternion"]
