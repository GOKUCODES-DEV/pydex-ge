"""Code generation: turn a project's manifest into editable Python.

The output is meant to be read and extended by people (hence the heavy
comment markers), not re-parsed.  The editor only writes this file when
it does not exist yet; once created, ``main.py`` belongs to the user.
"""

from __future__ import annotations

import os

from .project import DexProject, SceneEntry, SpriteEntry


def generate_main(project: DexProject) -> str:
    """The full ``main.py`` source for ``project``."""
    parts = [
        f'"""{project.name} --- created with PYDEX dex-editor.',
        "",
        "Edit this file freely: scenes regenerate into the editor section",
        'only when you create a fresh project.  The rest is yours.',
        '"""',
        "",
        "from pydex_ge import Camera2D, Game, Scene, Sprite",
        "",
    ]
    for scene in project.scenes:
        parts.append(generate_scene(project, scene))
        parts.append("")
    game_name = project.name + "Game"
    parts.extend(
        [
            "",
            f"class {game_name}(Game):",
            "    def __init__(self):",
            f"        super().__init__({project.name!r}, 800, 600, fps=60)",
            "",
            "    def setup(self):",
            "        self.background = (16, 16, 24)",
            f"        self.scenes.push({scene_class_name(project.scenes[0])}())"
            if project.scenes
            else "        pass",
            "",
            "",
            'if __name__ == "__main__":',
            f"    {game_name}().run()",
            "",
        ]
    )
    return "\n".join(parts)


def generate_scene(project: DexProject, scene: SceneEntry) -> str:
    """The Python class that recreates ``scene`` when entered."""
    lines = [f"class {scene_class_name(scene)}(Scene):"]
    lines.append(f'    """The {scene.name!r} scene."""')
    lines.append("")
    lines.append(f"    def __init__(self):")
    lines.append(
        f"        super().__init__(camera=Camera2D({_fmt(scene.width)}, {_fmt(scene.height)}))"
    )
    lines.append("")
    lines.append("    def on_enter(self):")
    lines.append("        # -- editor-placed sprites ------------------------------")
    used: set[str] = set()
    for sprite in scene.sprites:
        lines.extend(_emit_sprite(project, sprite, used))
    if not scene.sprites:
        lines.append("        # (no sprites placed yet)")
        lines.append("        pass")
    lines.append("        # -------------------------------------------------------")
    lines.append("")
    lines.append("    def update(self, dt):")
    lines.append("        super().update(dt)")
    lines.append("")
    lines.append("    def draw(self, renderer):")
    lines.append("        super().draw(renderer)")
    return "\n".join(lines)


def scene_class_name(scene: SceneEntry) -> str:
    """``'Main'`` -> ``'MainScene'``, deduplicated against keywords."""
    base = f"{scene.name}Scene"
    return base


def _emit_sprite(project: DexProject, sprite: SpriteEntry, used: set[str]) -> list[str]:
    name = _sprite_variable(sprite.asset, used)
    lines = [f"        {name} = Sprite({_asset_path(sprite.asset)!r})"]
    lines.append(f"        {name}.position = ({_fmt(sprite.x)}, {_fmt(sprite.y)})")
    if sprite.layer:
        lines.append(f"        {name}.z = {sprite.layer}")
    if sprite.scale != 1.0:
        lines.append(f"        {name}.scale = {_format_scale(sprite.scale)}")
    if sprite.flip_h:
        lines.append(f"        {name}.flip_x = True")
    if sprite.flip_v:
        lines.append(f"        {name}.flip_y = True")
    if not sprite.visible:
        lines.append(f"        {name}.visible = False")
    lines.append(f"        self.add({name})")
    return lines


def _sprite_variable(asset: str, used: set[str]) -> str:
    stem = os.path.splitext(os.path.basename(asset))[0]
    cleaned = "".join(
        char if char.isalnum() or char == "_" else "_" for char in stem
    ).lstrip("_")
    if not cleaned or cleaned[0].isdigit():
        cleaned = "sprite"
    candidate = cleaned
    counter = 2
    while candidate in used:
        candidate = f"{cleaned}_{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def _asset_path(asset: str) -> str:
    """Project-relative path to an asset (``main.py`` sits at the root)."""
    return "assets/" + asset.replace("\\", "/")


def _fmt(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return repr(round(float(value), 4))


def _format_scale(scale) -> str:
    if isinstance(scale, tuple):
        return f"({_fmt(scale[0])}, {_fmt(scale[1])})"
    return _fmt(scale)


__all__ = ["generate_main", "generate_scene", "scene_class_name"]