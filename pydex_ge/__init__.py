"""PYDEX - a beginner-friendly Python game-development framework.

Public API surface (Parts 1-6).  Only real, working functionality is
exposed here; future subsystems will be added as they are implemented.
"""

from .assets import Assets
from .audio import Audio, Music, Sound
from .check import (
    CheckReport,
    CheckResult,
    check_all,
    check_assets,
    check_file,
    check_project,
    check_pydex,
    check_python,
    format_error,
    format_result,
)
from .core import (
    Camera,
    Camera2D,
    Camera3D,
    Clock,
    Event,
    EventManager,
    EventType,
    Game,
    Renderer,
    Window,
)
from .exceptions import BackendError, ConfigurationError, MissingAssetError, PydexError
from .graphics import (
    Animation,
    DirectionalLight,
    Font,
    Image,
    Label,
    Material,
    Mesh,
    Object3D,
    Parallax,
    Sprite,
    SpriteSheet,
    Text,
    Texture,
    TextureRegion,
)
from .input import Input, Keys
from .loading import SplashScreen
from .math import Quaternion
from .physics import Body, Rect, Vector2, Vector3, World
from .scene import Scene, SceneManager
from .tilemap import TileMap
from .transform import Transform2D, Transform3D

__version__ = "1.0.0"

__all__ = [
    "Animation",
    "Assets",
    "Audio",
    "BackendError",
    "Body",
    "Camera",
    "Camera2D",
    "Camera3D",
    "CheckReport",
    "CheckResult",
    "check_all",
    "check_assets",
    "check_file",
    "check_project",
    "check_pydex",
    "check_python",
    "Clock",
    "ConfigurationError",
    "DirectionalLight",
    "Event",
    "EventManager",
    "EventType",
    "Font",
    "format_error",
    "format_result",
    "Game",
    "Image",
    "Input",
    "Keys",
    "Label",
    "Material",
    "Mesh",
    "MissingAssetError",
    "Music",
    "Object3D",
    "Parallax",
    "PydexError",
    "Quaternion",
    "Rect",
    "Renderer",
    "Scene",
    "SceneManager",
    "Sound",
    "Sprite",
    "SpriteSheet",
    "SplashScreen",
    "Text",
    "Texture",
    "TextureRegion",
    "TileMap",
    "Transform2D",
    "Transform3D",
    "Vector2",
    "Vector3",
    "Window",
    "World",
    "__version__",
]