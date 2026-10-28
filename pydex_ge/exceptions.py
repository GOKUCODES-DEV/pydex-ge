"""Exception hierarchy for PYDEX."""

import os


class PydexError(Exception):
    """Base class for all errors raised by PYDEX."""


class ConfigurationError(PydexError):
    """Raised when a game, window, clock, or engine is configured wrongly."""


class BackendError(PydexError):
    """Raised when the active backend cannot be initialized or operated."""


def missing_asset_message(resolved_path: str) -> str:
    """The standard ``Missing asset: ...`` message for a resolved file path."""
    return f"Missing asset: {os.path.basename(resolved_path)} (looked for {resolved_path!r})"


class MissingAssetError(BackendError):
    """Raised when a requested asset file does not exist.

    The message clearly says ``Missing asset: <filename>``.  The
    ``requested_by`` attribute, when set, names the ``file:line`` of the
    code that asked for the asset, so a beginner can jump straight to the
    failing call.
    """

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.path = path
        self.requested_by: str | None = None