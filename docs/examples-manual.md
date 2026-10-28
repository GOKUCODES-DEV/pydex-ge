# PYDEX Example Games

A set of complete, runnable example programs.  Each one builds on the
previous ones, so by the end you will have seen every major subsystem work
together: the loop, drawing, input, fonts/labels, sprites, animation,
cameras, scenes, assets, physics, parallax, effects, audio, 3D, the splash
screen, the static checker, and headless testing.

Every program below is real, working PYDEX code.  You can run each one
directly:

```text
python examples/your_file.py
```

(Or copy a program into your own project and run it there.)

---

## 1. Hello window — the absolute minimum

A `pydex_ge.Game` opens a window, clears it to a background color every
frame, and presents it.  That is the whole engine loop.

```python
import pydex_ge

game = pydex_ge.Game("My First Game", 800, 600, fps=60)
game.background = (20, 20, 30)   # RGB clear colour

game.run(max_frames=120)         # run for 120 frames, then close
```

* `pydex_ge.Game(title, width, height, *, fps=60)` — build the game.
* `game.background = (r, g, b)` — the colour the frame is cleared to.
* `game.run(max_frames=N)` — run the loop for `N` frames (omit it to run
  until the window is closed).
* `game.close()` — stop the loop from inside code.

---

## 2. Subclassing Game — update, draw, and input

Override `update(dt)` (called every frame, `dt` = seconds since the last
frame) and `draw()` (called after update).  Inside `draw` use
`self.renderer` to paint the frame.

```python
import pydex_ge


class MovingSquare(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Moving Square", 640, 480, fps=60)
        self.background = (20, 20, 30)
        self.x = 300
        self.y = 220

    def update(self, dt: float) -> None:
        speed = 200.0
        if self.input.is_key_down("left"):
            self.x -= int(speed * dt)
        if self.input.is_key_down("right"):
            self.x += int(speed * dt)
        if self.input.is_key_down("up"):
            self.y -= int(speed * dt)
        if self.input.is_key_down("down"):
            self.y += int(speed * dt)

    def draw(self) -> None:
        self.renderer.draw.rect(self.x, self.y, 40, 40,
                                color=(120, 220, 255), filled=True)
        self.renderer.draw.circle(100, 100, 30,
                                  color=(255, 80, 80), filled=False)


if __name__ == "__main__":
    MovingSquare().run()
```

Notes:

* `game.input.is_key_down(name)` is true while a key is held.  `pressed`
  means "just pressed this frame", `released` means "just let go".
* The 2D drawing commands live on `renderer.draw`:
  `rect`, `circle`, `line`, `pixel`.  `color` accepts RGB or RGBA tuples
  and `filled=` draws an outline instead of a filled shape.
* `Game.draw()` takes **no** renderer argument — use `self.renderer`.
  (Only a *Scene's* `draw(renderer)` receives the renderer; see §6.)

---

## 3. Fonts, labels, and score text

`Font` supplies a typeface; `Label` is text that you can update in place.

```python
import pydex_ge


class ScoreGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Score", 640, 240, fps=60)
        self.background = (20, 20, 30)
        self.score = 0

        font = pydex_ge.Font(size=24)                 # built-in default font
        self.label = pydex_ge.Label("Score: 0", font=font,
                                 position=(12, 12), color=(255, 220, 120))

    def update(self, dt: float) -> None:
        if self.input.is_key_pressed("space"):
            self.score += 1
            self.label.text = f"Score: {self.score}"   # update in place
        if self.input.is_key_pressed("escape"):
            self.close()

    def draw(self) -> None:
        self.renderer.draw_label(self.label)       # or self.label.draw(renderer)


if __name__ == "__main__":
    ScoreGame().run()
```

* `pydex_ge.Font(size=int)` uses a framework font; `pydex_ge.Font("assets/font.ttf",
  size=24)` loads a real TTF file (missing files raise
  `pydex_ge.MissingAssetError`).
* `pydex_ge.Label(text, font=..., position=(x, y), color=(r, g, b))`.
  `label.text` is plain Python — reassign it whenever the value changes.
* `pydex_ge.Text` is an alias of `pydex_ge.Label`.

---

## 4. Sprites and pixel sprites

A `Sprite` is an image you can move, scale, flip, and tint.  If you have no
art yet, `Sprite.from_pixels` builds one from raw RGBA bytes — perfect for
placeholder boxes.

```python
import pydex_ge


def solid_bytes(width: int, height: int, color) -> bytes:
    row = bytes((*color, 255)) * width
    return row * height


class SpriteGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Sprites", 640, 480, fps=60)
        self.background = (30, 34, 44)

        self.player = pydex_ge.Sprite.from_pixels(40, 40, solid_bytes(40, 40, (120, 220, 255)))
        self.player.position = (300, 220)
        self.player.scale = 2            # or (2, 1) for per-axis scale
        self.player.alpha = 200          # opacity 0..255

    def update(self, dt: float) -> None:
        self.player.flip_x = self.input.is_key_down("left")
        if self.input.is_key_pressed("r"):
            self.player.tint = (255, 90, 90)     # colour tint
        if self.input.is_key_pressed("f"):
            self.player.flash(0.3, (255, 255, 255))  # flash (duration, colour)

    def draw(self) -> None:
        self.renderer.draw_sprite(self.player)   # or self.player.draw(renderer)


if __name__ == "__main__":
    SpriteGame().run()
```

The `Sprite` attrs you will use most: `position`/`x`/`y`, `scale`,
`rotation`, `origin` (0..1 pivot), `flip_x`, `flip_y`, `alpha`, `tint`,
`visible`, and `z` (draw order).

---

## 5. Physics — a body that falls and lands

`World` steps `Body` objects under gravity and resolves them against a list
of static `Rect`s.  This is the classic "box that falls onto a floor".

```python
import pydex_ge
from pydex_ge.physics import Body, Rect, World


def solid_bytes(width: int, height: int, color) -> bytes:
    row = bytes((*color, 255)) * width
    return row * height


class FallingGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Falling Box", 640, 480, fps=60)
        self.background = (18, 18, 24)

        self.floor = Rect(0, 440, 640, 40)
        self.world = World(gravity=(0, 700), static_rects=(self.floor,))
        self.body = Body(position=(300, 40), size=(40, 40), velocity=(80, 0))
        self.world.add_body(self.body)

        self.box = pydex_ge.Sprite.from_pixels(40, 40, solid_bytes(40, 40, (120, 220, 255)))

        self.info = pydex_ge.Label("grounded: no", font=pydex_ge.Font(size=16),
                                position=(20, 20), color=(120, 255, 120))
        self.hint = pydex_ge.Label("R: drop again   Space: hop   ESC: quit",
                                font=pydex_ge.Font(size=13),
                                position=(20, 44), color=(120, 130, 150))

    def update(self, dt: float) -> None:
        if self.input.is_key_pressed("r"):
            self.body.position = (300, 40)
            self.body.velocity = (80, 0)
        if self.input.is_key_pressed("space"):
            self.body.apply_impulse((0, -260))       # an upwards nudge

        self.world.update(dt)                        # integrate all bodies

        grounded = self.body.collides_with(self.floor) and self.body.velocity.y == 0
        self.info.text = f"grounded: {'yes' if grounded else 'no'}"

        self.box.position = (int(self.body.position.x), int(self.body.position.y))

        if self.input.is_key_pressed("escape"):
            self.close()

    def draw(self) -> None:
        self.renderer.draw.rect(int(self.floor.x), int(self.floor.y),
                                int(self.floor.width), int(self.floor.height),
                                color=(90, 110, 150, 255))
        self.renderer.draw_sprite(self.box)
        self.renderer.draw_label(self.info)
        self.renderer.draw_label(self.hint)


if __name__ == "__main__":
    FallingGame().run()
```

Key ideas:

* `World(gravity=(0, 700), static_rects=(floor, ...))` creates the world
  with its colliders baked in.  Add more any time with
  `world.static_rects.append(rect)`.
* `Body(position=..., size=..., velocity=...)` is a box that falls.
  `body.apply_impulse((dx, dy))` changes velocity instantly.
* The world **owns** the simulation: call `world.update(dt)` once per
  frame.  It moves every body and resolves collisions.
* Mirror the body's position back onto a sprite each frame so the physics
  and the visuals agree.

---

## 6. Scenes — a menu and a game on a stack

A game is a stack of `Scene`s.  Only the top scene is updated and drawn.
Pushing a scene suspends the one below it; popping reveals it again.  This
is how you build a menu -> game -> pause structure.

```python
import pydex_ge


class MenuScene(pydex_ge.Scene):
    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self.add(pydex_ge.Label("MY GAME", font=pydex_ge.Font(size=40),
                             position=(280, 200), color=(255, 255, 255)))
        self.add(pydex_ge.Label("SPACE: start   ESC: quit",
                             font=pydex_ge.Font(size=18),
                             position=(270, 300), color=(255, 210, 90)))

    def on_enter(self) -> None:
        print("[menu] shown")

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.game.input.is_key_pressed("space"):
            self.manager.push(GameScene(self.game))
        elif self.game.input.is_key_pressed("escape"):
            self.game.close()


class GameScene(pydex_ge.Scene):
    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self.player = pydex_ge.Sprite.from_pixels(40, 40, _solid(40, 40))
        self.player.position = (300, 220)
        self.add(self.player)                 # scene updates + draws it for you

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.game.input.is_key_down("left"):
            self.player.x -= int(220 * dt)
        if self.game.input.is_key_down("right"):
            self.player.x += int(220 * dt)

    def draw(self, renderer) -> None:
        renderer.draw_sprite(self.player)


class Demo(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Scenes", 800, 600, fps=60)
        self.background = (22, 24, 34)
        self.scenes.push(MenuScene(self))     # start on the menu


def _solid(w: int, h: int) -> bytes:
    return bytes((120, 220, 255, 255)) * (w * h)


if __name__ == "__main__":
    Demo().run()
```

* Scene hooks you can override: `on_enter()`, `on_exit()`, `update(dt)`,
  `draw(renderer)`, `handle_event(event)`.
* `self.manager` is the `SceneManager` the scene was pushed onto.  Use it
  for `push`, `pop`, `replace`, and `current`.
* `scene.add(obj)` forwards `update(dt)` and `draw(renderer)` to `obj`
  automatically, so a sprite added to a scene needs no other wiring.
* A scene's `draw` **does** receive the renderer argument (unlike
  `Game.draw()`).

---

## 7. Cameras — following a player through a big world

A `Camera2D` scrolls a world larger than the screen.  World-space sprites
drawn between `camera.begin(renderer)` and `camera.end()` are transformed;
labels drawn outside the block stay fixed on screen (HUD).

```python
import pydex_ge
from pydex_ge.physics import Rect

WORLD_W, WORLD_H = 1600, 1000


class CameraGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Camera", 800, 600, fps=60)
        self.background = (22, 24, 34)

        self.player = pydex_ge.Sprite.from_pixels(32, 32, bytes((120, 220, 255, 255)) * 1024)
        self.player.position = (400, 500)

        self.floor = pydex_ge.Sprite.from_pixels(WORLD_W, 40, bytes((70, 90, 120, 255)) * (WORLD_W * 40))
        self.floor.position = (0, WORLD_H - 40)

        self.camera = pydex_ge.Camera2D(800, 600, position=(400, 500))  # viewport 800x600
        self.camera.bounds = Rect(0, 0, WORLD_W, WORLD_H)            # world limits
        self.camera.follow(self.player, smoothing=4.0)               # smooth tracking

        self.status = pydex_ge.Label("Cam (0,0)  press +/- to zoom", font=pydex_ge.Font(size=16),
                                  position=(12, 12), color=(120, 255, 120))

    def update(self, dt: float) -> None:
        speed = 260.0
        if self.input.is_key_down("left"):
            self.player.x -= int(speed * dt)
        if self.input.is_key_down("right"):
            self.player.x += int(speed * dt)
        if self.input.is_key_down("up"):
            self.player.y -= int(speed * dt)
        if self.input.is_key_down("down"):
            self.player.y += int(speed * dt)
        self.player.x = max(0, min(self.player.x, WORLD_W - 32))
        self.player.y = max(0, min(self.player.y, WORLD_H - 32))

        if self.input.is_key_pressed("minus"):
            self.camera.zoom = max(0.4, self.camera.zoom * 0.9)
        if self.input.is_key_pressed("equals"):
            self.camera.zoom = min(3.0, self.camera.zoom * 1.1)

        self.camera.update(dt)    # follow target + smooth + bounds + shake

        self.status.text = (f"Cam ({int(self.camera.position.x)},{int(self.camera.position.y)}) "
                            f"zoom {self.camera.zoom:.2f}")

    def draw(self) -> None:
        self.camera.begin(self.renderer)      # enter world space
        self.renderer.draw_sprite(self.floor)
        self.player.draw(self.renderer)
        self.camera.end()                     # back to screen space

        self.renderer.draw_label(self.status) # HUD: fixed on screen


if __name__ == "__main__":
    CameraGame().run()
```

Camera helpers worth knowing: `follow(target, smoothing=)`, `bounds`,
`move(dx, dy)`, `position`, `zoom`, `shake(amount, duration)`,
`look_at(pos)`, `world_to_screen(pos)`, `screen_to_world(pos)`.  A camera
given to a scene (`Scene(camera=camera)`) is updated and applied for you.

---

## 8. Animation — a walking character

A `SpriteSheet` chops an image into cells.  `sheet.animation(...)` builds an
`Animation` from cell coordinates, and you play it through the sprite.

```python
import pydex_ge


class AnimationGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Animation", 800, 300, fps=60)
        self.background = (22, 24, 34)

        # Suppose "player.png" is a sheet of 4 cells in one row (each 32x32).
        sheet = pydex_ge.SpriteSheet(pydex_ge.Image("assets/player.png"), 32, 32)

        # One sprite for the whole sheet; the animation swaps the frame.
        self.player = pydex_ge.Sprite(sheet.image)
        self.player.position = (350, 130)
        self.player.animations["idle"] = sheet.animation([(0, 0)], fps=2, loop=True)
        self.player.animations["walk"] = sheet.animation_run(0, 0, 4, fps=10, loop=True)
        self.player.play_animation("idle")

        self.moving = False

    def update(self, dt: float) -> None:
        self.moving = False
        if self.input.is_key_down("left"):
            self.player.x -= 4
            self.moving = True
        if self.input.is_key_down("right"):
            self.player.x += 4
            self.moving = True

        self.player.play_animation("walk" if self.moving else "idle")
        self.player.update(dt)       # advance the current animation

    def draw(self) -> None:
        self.player.draw(self.renderer)


if __name__ == "__main__":
    AnimationGame().run()
```

* `sheet.animation([(col, row), ...], fps=..., loop=True)` builds an
  animation from cell positions; `sheet.animation_run(col, row, count, ...)`
  is shorthand for a run of cells across a row.
* Attach animations to a sprite with `sprite.animations["name"] = anim`,
  then switch with `sprite.play_animation("name")`.
* The sprite only advances when you call `sprite.update(dt)` (or when it is
  in a Scene, which calls `update` for you).
* `sprite.animation` gives the live `Animation` for `pause()`, `resume()`,
  `reset()`, and reading `frame_index` / `frame_count`.

---

## 9. Parallax and sprite effects

`Parallax` makes a background sprite scroll slower than the camera.
Sprites can also flash, fade, and hold a tint.

```python
import pydex_ge


class ParallaxGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Parallax", 800, 400, fps=60)
        self.background = (20, 22, 34)

        self.far = pydex_ge.Sprite.from_pixels(64, 24, bytes((90, 110, 170, 255)) * (64 * 24))
        self.far.x = 0
        self.near = pydex_ge.Sprite.from_pixels(24, 24, bytes((60, 160, 90, 255)) * (24 * 24))
        self.near.x = 200

        # factor 1.0 = normal movement, 0.0 = screen-fixed, (x, y) per axis.
        self.far_layer = pydex_ge.Parallax(self.far, factor=(0.2, 1.0))
        self.near_layer = pydex_ge.Parallax(self.near, factor=0.6)

        self.camera = pydex_ge.Camera2D(800, 400, position=(400, 200))

        self.status = pydex_ge.Label("Arrows: scroll   F: flash   D: fade",
                                  font=pydex_ge.Font(size=15),
                                  position=(12, 12), color=(150, 160, 185))

    def update(self, dt: float) -> None:
        if self.input.is_key_down("left"):
            self.camera.move(-4, 0)
        if self.input.is_key_down("right"):
            self.camera.move(4, 0)
        self.camera.update(dt)

        if self.input.is_key_pressed("f"):
            self.far.flash(0.3, (255, 220, 120))
        if self.input.is_key_pressed("d"):
            self.far.fade_to(0, duration=1.0)   # fade alpha to 0 over 1s

    def draw(self) -> None:
        self.camera.begin(self.renderer)
        self.far_layer.draw(self.renderer)
        self.near_layer.draw(self.renderer)
        self.camera.end()

        self.renderer.draw_label(self.status)


if __name__ == "__main__":
    ParallaxGame().run()
```

---

## 10. Audio — sounds and music

`Audio` loads and plays sounds and music, and everything is safe on
headless backends (your game still runs in tests).

```python
import pydex_ge


class AudioGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Audio", 640, 240, fps=60)
        self.background = (18, 18, 24)

        self.audio = pydex_ge.Audio()
        self.snd = self.audio.load_sound("assets/click.wav")   # cached Sound
        self.music = self.audio.load_music("assets/theme.ogg") # cached Music

        self.music.volume = 0.6
        self.music.play(loop=True)        # start looping music

        self.label = pydex_ge.Label("Space: effect   M: mute   ESC: quit",
                                 font=pydex_ge.Font(size=15),
                                 position=(12, 12), color=(255, 220, 120))

    def update(self, dt: float) -> None:
        if self.input.is_key_pressed("space"):
            self.snd.play(loop=False)
        if self.input.is_key_pressed("m"):
            self.audio.master_volume = 0.0 if self.audio.master_volume else 1.0
        if self.input.is_key_pressed("escape"):
            self.audio.close()            # free the audio backend
            self.close()

    def draw(self) -> None:
        self.renderer.draw_label(self.label)


if __name__ == "__main__":
    AudioGame().run()
```

* `load_sound` / `load_music` cache: the same object comes back for the
  same path.
* Play with `sound.play(loop=False)` or `music.play(loop=True)`; set
  per-channel volume via `music.volume = 0.6`.
* Master mixing: `audio.master_volume`, `audio.music_volume`,
  `audio.sound_volume`.

---

## 11. 3D — spinning cubes on a grid

PYDEX renders simple 3D on the CPU.  Drive the renderer directly with a
`begin_3d` / `draw_mesh` / `end_3d` block; HUD labels drawn after the block
stay in screen space.

```python
import math

import pydex_ge


class Game3D(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("3D", 900, 600, fps=60)
        self.background = (16, 18, 24)

        self.camera = pydex_ge.Camera3D()
        self.camera.position = (0, 3, 10)
        self.camera.rotation = pydex_ge.Quaternion.from_euler(0.0, -8.0, 0.0)
        self.camera.fov = 70

        self.light = pydex_ge.DirectionalLight(direction=(0.6, -1, 0.8),
                                            intensity=0.9, ambient=0.35)

        self.mesh = pydex_ge.Mesh.cube(size=2)
        self.cube = pydex_ge.Transform3D(position=(0, 0, 0))
        self.material = pydex_ge.Material(color=(230, 120, 60), emission=(15, 6, 0))
        self.spin = 0.0

        self.grid = []
        for i in range(-7, 8, 2):
            self.grid.append(((float(i), 0.0, -7.0), (float(i), 0.0, 7.0)))
            self.grid.append(((-7.0, 0.0, float(i)), (7.0, 0.0, float(i))))

        self.hint = pydex_ge.Label("Arrows: look   W/S: move   R: reset   ESC: quit",
                                font=pydex_ge.Font(size=13),
                                position=(12, 12), color=(120, 140, 165))

    def update(self, dt: float) -> None:
        self.spin += 45 * dt
        self.cube.rotation_euler = (self.spin, self.spin * 0.7, self.spin * 0.3)

        forward = self.camera.forward
        if self.input.is_key_down("w"):
            self.camera.move(forward.x * 6 * dt, 0, forward.z * 6 * dt)
        if self.input.is_key_down("s"):
            self.camera.move(-forward.x * 6 * dt, 0, -forward.z * 6 * dt)
        if self.input.is_key_down("left"):
            self.camera.rotation = pydex_ge.Quaternion.from_euler(self.spin, -8.0, 0.0)
        if self.input.is_key_pressed("escape"):
            self.close()

    def draw(self) -> None:
        self.renderer.begin_3d(self.camera)
        for start, end in self.grid:
            self.renderer.draw_line_3d(start, end, color=(45, 55, 75))
        self.renderer.draw_mesh(self.mesh, self.cube, self.material)
        self.renderer.end_3d()

        self.renderer.draw_label(self.hint)


if __name__ == "__main__":
    Game3D().run()
```

* `pydex_ge.Mesh.cube(size=2)` (plus `Mesh.quad`, `Mesh.triangle`) builds a
  mesh; `pydex_ge.Material(color=..., emission=..., opacity=...)` describes its
  surface; `pydex_ge.DirectionalLight(...)` lights the whole scene.
* `pydex_ge.Transform3D(position=..., rotation_euler=(yaw, pitch, roll))`
  places a mesh.  `Transform3D.rotation_euler` drives animation.
* `pydex_ge.Quaternion.from_euler(yaw, pitch, roll)` sets 3D orientation.

---

## 12. Splash screen + assets cache

`SplashScreen` shows a logo, a progress bar, and auto-transitions to the
next scene once its loadables are ready.  It uses an `Assets` cache that
returns the *same* object for the same path.

```python
import pydex_ge


class GameScene(pydex_ge.Scene):
    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        assets = game.assets
        self.player = pydex_ge.Sprite(assets.image("assets/player.png"))
        self.player.position = (300, 220)
        self.add(self.player)

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.game.input.is_key_pressed("escape"):
            self.game.close()


class Demo(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Splash + Assets", 800, 600, fps=60)
        self.background = (22, 24, 34)
        self.assets = pydex_ge.Assets()          # one cache for the whole game

        splash = pydex_ge.SplashScreen(
            logo="assets/logo.png",
            name="My Game",
            version="1.0",
            loadables=[
                ("image", "assets/player.png"),
                ("font", "assets/font.ttf", 24),
            ],
            next_scene=GameScene(self),
            min_duration=1.0,
        )
        self.scenes.push(splash)

    def close(self) -> None:
        self.assets.clear()                   # free cached images/fonts
        super().close()


if __name__ == "__main__":
    Demo().run()
```

* Loadables are `("image", path)`, `("font", path, size)`, or
  `("sprite_sheet", path, cell_w, cell_h)` tuples, or callables taking the
  shared `Assets`.
* Reusing assets: `assets.image(path)`/`assets.font(...)`/
  `assets.sprite_sheet(...)` all return the same cached object.
  `assets.contains(path)` tells you if something is cached.

---

## 13. The static checker (before you run)

PYDEX ships a headless project checker that finds problems in your code
without opening a window:

```python
import pydex_ge

report = pydex_ge.check_project()           # checks the current directory
for problem in report:
    print(problem)                       # e.g. path:5:12: undefined name 'blah'
if report.ok:
    print("No errors!")
```

Or from the terminal:

```text
python -m pydex_ge.check .          # check this project
python -m pydex_ge.check --json .   # machine-readable output
python -m pydex_ge.check --pydex_ge .  # PYDEX-API checks only
```

---

## 14. Headless testing (CI / automated checks)

Swap in the null backend and games run without a window or SDL.  This is
how you test scenes and logic in CI.

```python
import pydex_ge
from pydex_ge.backend.null import NullBackend


class Demo(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("Test", 320, 240, backend=NullBackend())
        self.background = (10, 10, 10)
        self.frames = 0

    def update(self, dt: float) -> None:
        self.frames += 1


game = Demo()
game.run(max_frames=5)     # advance 5 frames, then stop
assert game.frames == 5
assert game.window.closed
print("Headless run OK")
```

The `Game.update`, scenes, physics, and even audio all work the same on the
null backend, so the same test can run on a CI machine with no display.