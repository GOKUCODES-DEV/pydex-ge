# PYDEX-GE

PYDEX-GE is a beginner-friendly Python game-development framework under active
development. Its long-term goal is a simple public API:

```python
import pydex_ge

game = pydex_ge.Game("My Game", 1280, 720)
game.run()
```

## Current Status

PYDEX-GE is in **early development** (pre-alpha). The **Part 1 foundation**
(package structure, core abstractions, backend wiring) is complete, as is
**Part 2** (game loop, window, clock, events), **Part 3** (2D drawing
primitives), **Part 4** (images, textures, sprites, sprite sheets, and
an asset cache), **Part 5** (input, fonts, text, and labels),
**Part 6** (audio: sound effects and music), **Part 7** (physics:
2D vectors, rectangles, and collision predicates), **Part 7.5**
(simple physics objects: `Body`, `World`, gravity, and static-rectangle
collisions), **Part 8** (frame-based `Animation`, a 2D `Camera`
with follow/zoom/bounds, and configurable frame rate), **Part 9**
(a `Scene`/`SceneManager` scene stack and a full `Assets` cache for
images, fonts, and sprite sheets), and **Part 10** (a `SplashScreen`
loading scene with true visual logo clipping and an automatic transition
to the next scene). **Part 11** adds the error and syntax-checking
system (`pydex_ge.check_file`, `pydex_ge.check_project`,
`pydex_ge.check_python/check_assets/check_pydex/check_all`, a `CheckReport`
object, a `python -m pydex_ge.check` command line, and
`pydex_ge.format_error`) and standardized `Missing asset: ...` errors.  **Part 12** adds the
Advanced 2D layer: reusable `Transform2D` objects, sprite transforms
(rotation, origin, flip, per-axis scale, parenting, `z`), renderer/backend
transform forwarding, camera `dead_zone` and `shake`, `Parallax`
backgrounds, camera-culled `TileMap`s with tile collision, named
`Sprite` animations with `on_finish`, and deterministic 2D effects
(`fade_to`, `flash`, `tint`).  **Part 3D** adds the first 3D
subsystem: a CPU-side 3D foundation with `Vector3`, `Quaternion`,
`Transform3D`, a perspective `Camera3D`, meshes, materials, an
`Object3D`, a directional light, and renderer/scene integration —
all rendered on the CPU with perspective projection, back-face
culling, depth-sorted triangles, and diffuse lighting.

There is still no full physics-simulation pipeline today — that arrives in
a later part.  Parts 7/7.5 are deliberately a **geometry +
simple-object foundation**, not a rigid-body physics engine: no rotation,
friction, restitution, or body-to-body collisions.  The camera is 2D-only
for now; the design leaves room for a future 3D camera.

## 3D status note

PYDEX now has a **CPU-rendered 3D foundation** (Part 3D).  It is real but
deliberately minimal: solid meshes, perspective projection, one
directional light, and painter's-algorithm depth sorting.  It is **not**
yet a full 3D engine — there is no z-buffer (so intersecting triangles may
order imperfectly), no textures on meshes, no skeletal animation, no
post-processing, and no GPU pipeline.  Those remain out of scope for now.

## Installation

Requires Python 3.11 or newer. The test suite is run with Python 3.14 in the current environment; broader CI coverage is planned.

**From PyPI** (once published):

```shell
pip install PYDEX-GE
```

**Directly from GitHub** (always current):

```shell
pip install "git+https://github.com/GOKUCODES-DEV/pydex-ge.git"
```

**From a local checkout** (editable, for development):

```shell
git clone https://github.com/GOKUCODES-DEV/pydex-ge.git
cd pydex-ge
pip install -e .
```

Any of these installs PYDEX-GE plus its backend dependencies (`pysdl2`
and `pysdl2-dll`, which bundle the SDL2 binaries) so `import pydex_ge`
works from anywhere.

## Backend

PYDEX runs on top of SDL2 through the `pysdl2` / `pysdl2-dll` packages.
The SDL2 backend is hidden behind the public API, so you never deal with
SDL objects directly.

- **SDL2 backend (default).** Used for normal graphical applications. If
  it cannot be initialized, PYDEX raises a clear `BackendError` explaining
  how to fix the installation — it never silently draws nothing. SDL2_ttf
  ships with `pysdl2-dll`, so fonts work out of the box with no extra
  installation step.
- **Null backend (headless).** For tests, CI, or machines without a
  display. Select it explicitly with `PYDEX_BACKEND=null`, or pass
  `NullBackend()` directly when constructing objects. It reads image
  dimensions from PNG/JPG/BMP headers (no pixel decoding) and records
  sprite draws in memory.

## Current Features

- Installable, importable package (`pydex_ge`, `pydex_ge.core`, `pydex_ge.backend`).
- **SDL2 backend** built on `pysdl2` + `pysdl2-dll`: real window creation,
  rendering, event polling, and clean shutdown.
- `Game` — top-level object that owns a window, clock, event system,
  renderer, and a `SceneManager`, and drives the main loop (`update`/`draw`
  hooks, `run()`, `close()`).
- `Window` — title, size, lifecycle (`open()`, `close()`, `closed`), and
  resizing; exposes a renderer that can clear and present the frame.
- **2D drawing** — `game.renderer.draw` provides `pixel`, `line`,
  `rect` (filled or outlined), and `circle` (filled or outlined).
- **Images** — `pydex_ge.Image("player.png")` loads PNG/JPG/BMP files and
  exposes `width`/`height`.
- **Textures** — `renderer.create_texture(image)` prepares a drawable
  texture (cached per image per window session); `TextureRegion` describes
  a rectangular part of an image.
- **Sprites** — `pydex_ge.Sprite(image)`, `pydex_ge.Sprite("player.png")`, or
  `pydex_ge.Sprite.from_pixels(width, height, rgba_bytes)`, with `position`,
  `scale`, `alpha`, and `visible`. Draw with `renderer.draw_sprite(sprite)`
  (or `sprite.draw(renderer)`).  A sprite can also play an `Animation` (or
  swap between several via `play_animation(name)`).
- **Sprite sheets** — `pydex_ge.SpriteSheet(image, cell_width, cell_height)`
  with `sprite(x, y, w, h)`, `region(x, y, w, h)`, `cell(col, row)`, and
  `animation()` / `animation_run()` helpers that build frame-based
  animations straight from the sheet's cells.
- **Asset cache (Part 9)** — `pydex_ge.Assets()` caches images, fonts, and
  sprite sheets by path (fonts also by size) so repeated requests reuse one
  instance; `remove(path)` and `clear()` free the resources it created, and
  cleanup is idempotent.
- **Scenes (Part 9)** — `pydex_ge.Scene` groups objects (sprites, labels,
  bodies) and forwards `update`/`draw`/`handle_event` to them; a
  `pydex_ge.SceneManager` stack (`game.scenes`) supports `push`/`pop`/
  `replace`/`clear` so only the current scene runs while scenes below stay
  suspended.
- **Splash screen (Part 10)** — `pydex_ge.SplashScreen` is a scene that shows
  a logo, game name/version, PYDEX branding, and a progress bar while
  asset files are silently checked and loaded through a shared `Assets`
  cache, then auto-transitions to the next scene.  Logo shapes use real
  visual clipping (`"circle"`/`"rounded"`) via the existing 2D primitives.
- **Animation (Part 8)** — `pydex_ge.Animation(frames, fps=..., loop=...,
  speed=...)` plays a sequence of frames (a `Sprite` or `TextureRegion`
  each) with full play/pause/resume/stop control; attach one to a sprite
  with `sprite.play_animation(...)` or `sprite.animation = ...`.
- **Camera (Part 8)** — `pydex_ge.Camera(width, height)` is a 2D viewport
  with `position` (the world point at the viewport center), `zoom`,
  `look_at()`, `follow(target, smoothing=...)`, and optional `bounds`;
  `renderer.begin_camera(camera)` / `end_camera()` render the world through
  it while text and labels stay in screen space.
- `Clock` — delta time (`tick()`), optional FPS frame limiting, and time
  tracking.  The frame rate is configurable via `game.fps` (a positive
  number like `60` or `120`, or `None` for unlimited).
- `EventManager` — a backend-agnostic event queue that translates the
  window-quit, window-close, and window-resized events.
- `Backend` abstraction with `sdl2` and `null` implementations.
- **Input** — `game.input` provides `is_key_pressed`/`is_key_released`/
  `is_key_down` (with `is_key_held` alias) plus mouse buttons, position,
  and motion delta; `pydex_ge.Keys` holds friendly key names (e.g.
  `Keys.ESCAPE`, `Keys.SPACE`).
- **Text and labels** — `pydex_ge.Font(path, size)` loads a font file (`.ttf`
  or `.otf`) directly from your project folder; `pydex_ge.Text` and
  `pydex_ge.Label` draw text at a position in any color.
- **Custom fonts** — give `pydex_ge.Font` a relative or absolute path and it
  loads that file in place (relative paths resolve against the current
  working directory, like images). No font is ever installed into Windows.
  A missing file raises a clear `BackendError`. If you pass no path at all,
  PYDEX searches common system font locations for a usable font.
- **Audio** — `pydex_ge.Sound(path)` for sound effects and
  `pydex_ge.Music(path)` for music, plus the `pydex_ge.Audio` manager that
  bundles cached loading and three volume levels (master, sound, music).
  Sound effects overlap freely; only one music track plays at a time.
- **Physics (geometry)** — `pydex_ge.Vector2` (a 2D float vector with
  arithmetic, normalize, rotate, dot, distance, and more) and
  `pydex_ge.Rect` (an axis-aligned rectangle with edges, center, corners,
  containment, overlap, intersection, and union), plus collision
  predicates (`point_in_rect`, `rects_overlap`, `circles_overlap`,
  `point_in_circle`, `circle_rect_overlap`) in `pydex_ge.physics`.
- **Physics objects (Part 7.5)** — `pydex_ge.Body` (position, velocity,
  acceleration, mass, size) and `pydex_ge.World` (gravity, stepping, and
  static-rectangle collision resolution via `collide_static`).
- Core classes raise `PydexError`/`ConfigurationError` on invalid use.
- **Error and syntax checking (Part 11)** — `pydex_ge.check_file(path)`
  compiles a Python file and reports syntax errors with the exact
  `file:line:column`; `pydex_ge.check_project(folder)` scans a whole project;
  `pydex_ge.check_python/check_assets/check_pydex/check_all` run individual
  check families; `pydex_ge.check` also runs from the command line
  (`python -m pydex_ge.check .`) with `--json`/`--quiet` output;
  `pydex_ge.format_error(exc)` renders any exception as one clean
  `file:line: ErrorType: message` line; and missing assets raise
  `MissingAssetError` whose message says `Missing asset: <filename>` and
  whose `requested_by` names the file/line that asked for it.
- **Advanced 2D (Part 12)** — `pydex_ge.Transform2D` reusable transforms with
  parent/child world math; sprite transforms (rotation, origin, flip,
  per-axis scale, parenting, `z`); camera `dead_zone` and deterministic
  `shake()`; `pydex_ge.Parallax` backgrounds; camera-culled `pydex_ge.TileMap`s
  with merged solid runs and `collide_body`; named sprite animations with
  `add_animation`/`play_animation`/`on_finish`; and deterministic 2D
  effects (`fade_to`, `flash`, `tint`, plus `pydex_ge.graphics.Fade` /
  `Flash` / `Tint`).
- **3D Foundation (Part 3D)** — `pydex_ge.Vector3`, `pydex_ge.Quaternion`, and
  `pydex_ge.Transform3D` for 3D math; a perspective `pydex_ge.Camera3D` with
  `look_at`/`project`; `pydex_ge.Mesh` (triangle/quad/cube primitives),
  `pydex_ge.Material`, and `pydex_ge.Object3D`; a `pydex_ge.DirectionalLight`; and
  renderer 3D paths (`begin_3d`/`draw_mesh`/`end_3d`/`draw_line_3d`) that
  project, back-face cull, depth-sort, light, and scanline-fill every
  triangle on the CPU.  A `Scene` can carry a `camera3d` to render 3D
  objects alongside 2D sprites.

## Drawing

### Coordinate system

The origin `(0, 0)` is the **top-left** corner of the window, `+X` points
right, and `+Y` points down. Coordinates are in pixels:

```text
(0,0) ────────────→ X (right)
  │
  │
  ↓
  Y (down)
```

There is no logical/scaling transform yet.  Part 8 adds a `Camera` that
introduces a world-coordinate transform (see [Animation and Camera](#animation-and-camera-part-8)).

### Colors

Colors are plain tuples of integers, each channel in `0-255`:

- RGB: `(255, 0, 0)`
- RGBA: `(255, 0, 0, 128)`

Invalid colors (wrong length, wrong type, or channels outside `0-255`)
raise `ConfigurationError`.

### Example

```python
import pydex_ge

class MyGame(pydex_ge.Game):
    def __init__(self):
        super().__init__("My Game", 800, 600, fps=60)
        self.background = (20, 20, 25)
        self.player = pydex_ge.Sprite("player.png")
        self.player.position = (100, 100)
        self.player.scale = 2.0
        self.face = pydex_ge.Sprite.from_pixels(16, 16, bytes([255] * 16 * 16 * 4))
        self.sheet = pydex_ge.SpriteSheet("tiles.bmp", 32, 32)
        self.tile = self.sheet.sprite(0, 0, 32, 32)

    def draw(self):
        self.renderer.draw.rect(50, 50, 200, 100, color=(255, 0, 0))
        self.renderer.draw.circle(180, 300, 60, color=(0, 255, 0))
        self.renderer.draw_sprite(self.player)
        self.renderer.draw_sprite(self.face)
        self.renderer.draw_sprite(self.tile)

def main():
    game = MyGame()
    game.run(max_frames=120)
```

Run the bundled examples:

```shell
python examples/sprites.py     # image, pixel, and sprite-sheet sprites
python examples/shapes.py      # draws shapes; stays open until closed
python examples/window.py      # working SDL2 window with a background color
python examples/foundation.py  # minimal foundation example
python examples/input_label.py # press E to change a label, ESC to quit
python examples/audio.py       # sound effects, music, and volume controls
python examples/physics.py     # Vector2 movement, Rect bounds, collision highlight
python examples/falling.py     # a Body drops under gravity and lands on a floor
python examples/animation_camera.py  # sprite animations, camera follow, zoom, FPS
python examples/scenes.py            # scene stack, transitions, asset caching
python examples/splash.py            # splash screen, loading, auto-transition
python examples/check_demo.py        # syntax check + missing-asset error demo
python examples/3d_basic.py          # rotating 3D cube, grid, light, 3D camera
```

## Input, Text, and Labels

### Keyboard and mouse

Query `game.input` inside `update()`:

```python
if game.input.is_key_pressed("e"):      # true only on the frame E goes down
    ...
if game.input.is_key_held(Keys.LEFT):   # alias for is_key_down
    ...
if game.input.is_button_pressed("left"):
    ...
x, y = game.input.mouse_position
dx, dy = game.input.mouse_delta
```

`pydex_ge.Keys` provides friendly names: `Keys.ESCAPE`, `Keys.SPACE`,
`Keys.ENTER`, `Keys.UP`, letters like `Keys.A`, digits, `F1`–`F12`, and
more. Plain strings (e.g. `"escape"`, `"left"`) work too and are matched
case-insensitively. Unknown key or button names return `False` rather than
erroring.

### Fonts

```python
font = pydex_ge.Font("assets/fonts/MyGameFont.ttf", size=32)  # from your project
font = pydex_ge.Font(size=24)                                  # system font fallback
```

- Relative paths resolve against the current working directory; absolute
  paths work as-is.
- `.ttf` and `.otf` files are supported; a missing file raises
  `BackendError`.
- Fonts are cached per `(path, size)` and freed when you call
  `font.destroy()`.

### Text and labels

```python
label = pydex_ge.Label("Press E", font=font, position=(100, 100), color=(255, 255, 255))

# inside draw():
renderer.draw_label(label)   # or label.draw(renderer)
```

`Label` (a friendly `Text`) supports `text`, `position`/`x`/`y`, `color`,
`font`, `font_size`, `visible`, and `width`/`height` (from measuring the
text). Changing `text` or `color` only costs a re-render when drawn, and
rendered text is cached.

**Sharing fonts.** A `Font` instance can be shared by many `Text`/`Label`s.
`Text.destroy()`/`Label.destroy()` never destroy a font you passed in — an
explicitly created `Font` stays usable until *you* call `font.destroy()`.
For this reason, changing `font_size` on a `Text`/`Label` that shares a
font raises `ConfigurationError` (create a new `Font` instead); a label
that created its own font from a path can change `font_size` freely.

### Example

```python
import pydex_ge

class MyGame(pydex_ge.Game):
    def __init__(self):
        super().__init__("Input + Label", 640, 480, fps=60)
        font = pydex_ge.Font(size=32)
        self.label = pydex_ge.Label("Press E", font=font, position=(180, 200))

    def update(self, dt):
        if self.input.is_key_pressed("e"):
            self.label.text = "E was pressed!"
        if self.input.is_key_pressed("escape"):
            self.close()

    def draw(self):
        self.renderer.draw_label(self.label)
```

See `examples/input_label.py` for a runnable version.

### Limitations

- Circles are rasterized on the CPU (SDL2 provides no circle primitive).
- Drawing fills always use full alpha; color alpha is stored but not yet
  blended.
- The null backend reads only image dimensions from file headers; decoding
  actual pixels (for PNG/JPG) happens only in the SDL2 backend.
- Text rendering is not yet cached at the system level; `font.measure()`
  always consults the backend. Text textures are cached per (font, text,
  color) for the life of a window session.
- No logical/scaling transforms or a rigid-body physics engine yet — those
  arrive in later parts.  (Parts 7/7.5 add the geometry foundation and
  simple gravity-driven bodies; Part 8 adds the 2D camera; Part 9 adds
  scenes and the asset cache; Part 10 adds the splash/loading screen.)

## Physics

Part 7 provides a **math/geometry foundation** and Part 7.5 adds small
physics objects on top of it.  There is no rigid-body simulation (no
rotation, friction, restitution, or body-to-body collisions), but you do
get vectors, rectangles, collision predicates, and simple gravity-driven
bodies that collide with static rectangles.

### Vector2

`pydex_ge.Vector2` is a 2D vector with float components:

```python
import pydex_ge
from pydex_ge.physics import Rect

pos = pydex_ge.Vector2(100, 200)
velocity = pydex_ge.Vector2(60, 0)
pos += velocity * dt                      # move per frame

length = velocity.length                  # magnitude
direction = velocity.normalized()         # unit vector (0,0 -> (0,0))
speed = velocity.dot(pydex_ge.Vector2(1, 0)) # horizontal component
rotated = velocity.rotate(45)             # clockwise degrees
limited = velocity.clamp_length(120)      # cap the speed
```

Vectors support `+`, `-`, `*`/`/` (by a scalar or another vector),
in-place `+=`/`-=`/`*=`/`/=`, unary `-`, `distance()`, `cross()`,
`perpendicular()`, and tolerance-based `==`.  `bool` is rejected (it is
not a number); invalid values raise `ConfigurationError`.

### Rect

`pydex_ge.Rect` is an axis-aligned rectangle (floats allowed, zero size
allowed):

```python
bounds = pydex_ge.Rect(0, 0, 800, 600)               # x, y, width, height
box = pydex_ge.Rect(position=(10, 10), size=(50, 50)) # or Vector2/position/size

box.left, box.right, box.top, box.bottom           # edges
box.center                                          # Vector2
box.top_left, box.top_right, box.bottom_left, box.bottom_right
box.size                                            # Vector2(width, height)

box.contains_point((25, 25))       # True (edges count as inside)
box.overlaps(other_rect)           # touching edges count as overlap
box.intersection(other_rect)       # the overlap Rect, or None
box.union(other_rect)              # smallest rect containing both
box.inflate(4, 4)                  # grown copy
box.moved(10, 0)                   # shifted copy
```

`Rect` `==` is float-tolerant.  `width`/`height` must be non-negative;
`x`/`y` may be any number.

### Collision predicates

Standalone geometry-only helpers live in `pydex_ge.physics`:

```python
from pydex_ge.physics import (circle_rect_overlap, circles_overlap,
                           point_in_circle, point_in_rect, rects_overlap)

point_in_rect((5, 5), box)                 # point vs rect
rects_overlap(a, b)                        # rect vs rect
circles_overlap((0, 0), 5, (4, 0), 5)      # circle vs circle
point_in_circle((1, 1), (0, 0), 2)         # point vs circle
circle_rect_overlap((0, 0), 3, box)        # circle vs rect
```

All of them treat touching edges as an overlap, accept `(x, y)` tuples or
`Vector2` for points/centers, and validate inputs (`ConfigurationError`
for invalid types, negative radii, or non-`Rect` rectangles).

See `examples/physics.py` for a runnable demo: a sprite steered with the
arrow keys that bounces off window edges using `Rect` checks and flashes
a target rectangle when the sprite overlaps it.

### Simple physics objects (Part 7.5)

`pydex_ge.Body` holds a position, velocity, acceleration, mass, and size, and
integrates them each step.  `pydex_ge.World` applies gravity to a list of
bodies and resolves them against static rectangles (floors, walls):

```python
from pydex_ge.physics import Body, Rect, World

world = World(gravity=(0, 700), static_rects=(Rect(0, 440, 640, 40),))
box = Body(position=(300, 40), size=(40, 40))
world.add_body(box)

# every frame:
world.update(dt)                     # gravity + integrate + floor collision
if box.collides_with(floor):         # is the box touching the floor?
    ...
box.apply_force((0, 200))            # force -> acceleration (F = ma)
box.apply_impulse((0, -260))         # instantaneous velocity change (a hop)
```

- `Body` supports `position`, `velocity`, `acceleration`, `mass`,
  `width`/`height`, `size`, and `rect` (its collision rectangle).
- `Body.update(dt)` uses semi-implicit Euler: velocity from acceleration,
  then position from the new velocity.
- `Body.collide_static(rect)` resolves a collision against a static
  rectangle by pushing the body out along the axis of least penetration
  and zeroing that velocity component (so a body lands on a floor and
  stops falling).
- `World.update(dt)` applies gravity to every body, steps it, then
  resolves it against each static rectangle.

See `examples/falling.py` for a runnable demo: a box drops under gravity,
lands on a floor, and can be dropped again (**R**) or hopped (**Space**).

## Animation and Camera (Part 8)

Part 8 adds frame-based animation, a 2D camera, and a configurable frame
rate on top of the drawing and physics foundation.

### Frame rate

`game.fps` is a read/write property.  A positive number (e.g. `60` or
`120`) caps the loop to that many frames per second; `None` means
unlimited.  You can change it at any time, even mid-run:

```python
game.fps = 120
game.fps = None   # unlimited
```

### Animation

An `Animation` plays a sequence of frames over time.  Each frame is a
`Sprite` or a `TextureRegion`, either as a plain item or as a
`(source, duration_seconds)` tuple so a frame can have its own length:

```python
import pydex_ge

# Simple: frames at 8 FPS, looping forever
spin = pydex_ge.Animation([r1, r2, r3, r4], fps=8)

# Custom durations per frame, playback speed 2x, not looping
jump = pydex_ge.Animation(
    [(r1, 0.10), (r2, 0.15), (r3, 0.20)],
    loop=False,
    speed=2.0,
)

# Control playback
spin.play()       # start (or restart if it already finished)
spin.pause()      # freeze on the current frame
spin.resume()     # continue
spin.stop()       # rewind and stop
spin.reset()      # rewind, keep current play state
spin.restart()    # rewind and play

frame = spin.current_frame   # the active Sprite / TextureRegion
spin.time                    # seconds elapsed since the last reset
spin.frame_index             # index of the active frame
spin.finished                # True once a non-looping animation ends
```

Timing is seconds-based, so an animation looks the same at 30, 60, or
unlimited FPS.  If you hand `update(dt)` a very large `dt`, the animation
consumes it fully instead of skipping frames.  Invalid frames, fps,
durations, or speeds raise `ConfigurationError`.

### Animating a sprite

Attach an animation (or a whole set) to a `Sprite` and call
`sprite.update(dt)` in your game loop:

```python
player = pydex_ge.Sprite("player.png")
player.animations = {
    "idle": pydex_ge.Animation([idle1, idle2], fps=4),
    "walk": pydex_ge.Animation([w1, w2, w3, w4], fps=8),
}
player.play_animation("idle")   # play; call again with the same name = no-op

# every frame:
player.update(dt)               # advance whichever animation is active
player.draw(renderer)           # draws the current animation frame
```

`sprite.animation = spin` attaches a single animation directly (setting it
to `None` restores the plain static sprite).  `sprite.stop_animation()`
pauses the active one and shows its current frame.  A sprite that never
uses animations allocates no extra resources and behaves exactly as before.

### Animations from a sprite sheet

`SpriteSheet` builds looping, cell-based animations for you:

```python
sheet = pydex_ge.SpriteSheet("player.png", cell_width=32, cell_height=32)

# columns 0-3 of row 1, at 8 FPS, looping
walk = sheet.animation(frames=[(0, 1), (1, 1), (2, 1), (3, 1)], fps=8)

# whole run: column 0..count-1 of a row; optional (col, row, duration)
idle = sheet.animation_run(column=0, row=0, count=2, fps=4)
custom = sheet.animation(frames=[(0, 0, 0.1), (1, 0, 0.2)])
```

### Camera

A `Camera` describes the region of the world you are looking at.  Its
`position` is the **world point at the center of the viewport**, and `zoom`
scales the world up (zoom `> 1`) or down (zoom `< 1`):

```python
from pydex_ge.physics import Rect

camera = pydex_ge.Camera(800, 600)       # same size as your window, zoom 1
camera.position = (100, 200)          # center of the view, in world coords
camera.move(10, 0)                    # nudge it
camera.look_at((400, 300))            # center on a point
camera.zoom = 1.5                     # 0.4 - 3.0 in the example
camera.bounds = Rect(0, 0, 2000, 1200)  # optional world limits to clamp to
```

To draw the world through the camera, wrap your world drawing in
`begin_camera` / `end_camera`:

```python
def draw(self):
    self.renderer.draw.rect(0, 0, 800, 600, color=(20, 20, 25))
    self.renderer.begin_camera(self.camera)
    self.renderer.draw_sprite(self.player)   # world space (transformed)
    self.renderer.end_camera()
    self.renderer.draw_label(self.hud)       # screen space (untouched)
```

Sprites are transformed by the camera (position and `zoom`); text and
labels are **not**, so UI stays pinned to the screen.  When no camera is
active, `draw_sprite` behaves exactly as before.

**Following a target.** `camera.follow(target, smoothing=None)` tracks a
`Vector2`, a `(x, y)` tuple, a `Body`, or anything with a `position` (like
a `Sprite`).  With `smoothing=0` (or `None`) the camera snaps; a positive
smoothing value eases it toward the target.  Call `camera.update(dt)` each
frame to apply the follow movement and the `bounds` clamp:

```python
camera.follow(self.player, smoothing=4.0)
camera.clear_follow()          # stop following

# every frame:
camera.update(dt)
```

`bounds` keeps the view inside the world: near the edges the camera stops
at the limit instead of showing out-of-world space, and a world smaller
than the viewport centers the view.  Setting `camera.enabled = False`
makes `begin()`/`begin_camera()` no-ops, which is handy for headless runs.
`Camera2D` is an alias, and the public API uses `Camera` for now (the
naming leaves room for a future 3D camera).

### Example

```python
import pydex_ge
from pydex_ge.physics import Rect

class MyGame(pydex_ge.Game):
    def __init__(self):
        super().__init__("Animation + Camera", 800, 600, fps=60)
        self.player = pydex_ge.Sprite("player.png")
        self.player.position = (400, 300)
        self.player.animations = {
            "idle": pydex_ge.Animation([self.player], fps=4),
            "walk": pydex_ge.Animation([self.player], fps=8),
        }
        self.player.play_animation("idle")
        self.camera = pydex_ge.Camera(800, 600)
        self.camera.follow(self.player, smoothing=4.0)
        self.camera.bounds = Rect(0, 0, 2000, 1200)

    def update(self, dt):
        if self.input.is_key_down("right"):
            self.player.x += 200 * dt
            self.player.play_animation("walk")
        else:
            self.player.play_animation("idle")
        self.player.update(dt)
        self.camera.update(dt)

    def draw(self):
        self.renderer.begin_camera(self.camera)
        self.renderer.draw_sprite(self.player)
        self.renderer.end_camera()

def main():
    game = MyGame()
    game.run()
```

See `examples/animation_camera.py` for a runnable version: a character with
idle/walk animations walks around a scrolling world under a following
camera.  Controls: arrow keys move, `+`/`-` zoom (`0.4`-`3.0`), `Space`
pauses/resumes the animation, `R` resets, `F1`-`F4` switch the frame rate
(24/60/120/unlimited), `ESC` quits.

## Scenes and Asset Management (Part 9)

Part 9 adds a lightweight scene system and a full asset cache on top of the
drawing, physics, and animation foundation.

### Scenes

A `Scene` is a container for objects.  It forwards lifecycle calls to any
object that has the matching method — no heavy base class required:

* objects with an `update(dt)` method are updated each frame,
* objects with a `draw(renderer)` method are drawn each frame,
* objects with a `handle_event(event)` method receive engine events.

Existing PYDEX classes already fit: `Sprite` provides `update` and `draw`,
`Label`/`Text` provide `draw`, and `Body` provides `update`.

```python
import pydex_ge

menu = pydex_ge.Scene()
menu.add(pydex_ge.Label("Press SPACE", font=pydex_ge.Font(size=24), position=(100, 100)))

class GameScene(pydex_ge.Scene):
    def __init__(self):
        super().__init__()
        self.player = pydex_ge.Sprite("player.png")
        self.add(self.player)

    def on_enter(self):     # called when the scene becomes current
        print("game started")

    def on_exit(self):      # called when the scene stops being current
        print("game ended")

    def update(self, dt):
        super().update(dt)          # forwards update() to the player
        if self.game.input.is_key_pressed("escape"):
            self.manager.pop()
```

A scene may carry a `Camera`: when `scene.camera` is set, the scene draws
its objects between `camera.begin(renderer)` and `camera.end()`, so world
sprites are transformed while labels stay screen-space.

### The scene stack

Each `Game` owns a `SceneManager` at `game.scenes`.  Only the top of the
stack — the **current** scene — receives `update`, `draw`, and events.
Scenes below it stay suspended, keeping their state:

```python
game.scenes.push(scene)     # enter scene; the one below it is suspended
game.scenes.pop()           # exit current; the revealed scene resumes
game.scenes.replace(scene)  # exit current, enter scene (same as push when empty)
game.scenes.clear()         # exit everything, top-down
scene = game.scenes.current # the active scene (None when the stack is empty)
```

Lifecycle rules:

* `push` calls the new scene's `on_enter()` only.  The scene below it is
  suspended without exiting.
* `pop` calls the popped scene's `on_exit()` and resumes the revealed scene
  without re-entering it.
* `replace` fully transitions: old scene exits, new scene enters.
* A scene can never appear twice in the stack, and only `Scene` instances
  can be pushed (anything else raises `ConfigurationError`).

Every frame `Game.run()` updates and draws the current scene *after* your
`Game.update()`/`Game.draw()` hooks, and forwards engine events to it, so a
scene-based game does not need to override the hooks at all.  With an empty
stack the loop behaves exactly as in earlier parts.

### The asset cache

`Assets` loads and caches images, fonts, and sprite sheets.  Asking for the
same asset twice returns the **same instance**, so repeated loads never
re-decode the file:

```python
assets = pydex_ge.Assets()                     # uses the default (SDL2) backend

coin = assets.image("assets/coin.png")          # Image, cached by path
coin_again = assets.image("assets/coin.png")    # the very same object

font = assets.font("assets/fonts/ui.ttf", size=16)  # cached by (path, size)
sheet = assets.sprite_sheet("player.png", 32, 32)   # SpriteSheet + shared Image

assets.contains("coin.png")   # True once loaded
len(assets)                   # number of cached assets
assets.remove("coin.png")     # destroy + drop every entry for that path
assets.clear()                # destroy everything, idempotent
```

Details:

* Paths are normalized to an absolute, case-normalized key, so relative and
  absolute forms of the same file hit the same cache entry.
* A sprite sheet wraps the same cached `Image` that `assets.image(path)`
  returns, so the image is shared and never double-loaded.
* `remove(path)` returns how many cache entries were dropped and is
  idempotent; `clear()` is idempotent too.
* The manager only destroys resources it created.  Textures are **not**
  cached here — they belong to a window's renderer and are created by the
  renderer instead.
* PYDEX never downloads assets and never installs fonts into the OS.

See `examples/scenes.py` for a runnable version: a menu scene pushes a
game scene (camera-followed player collecting coins), which pushes an
asset overlay showing that cached loads return identical objects.  Controls:
arrow keys move, `SPACE` starts, `A` opens the overlay, `ESC` goes back or
quits.

## Loading and Splash Screen (Part 10)

Part 10 adds a `SplashScreen` — a scene that shows a logo and loading
progress while game resources are silently checked and loaded, then
auto-transitions to the next scene.  It builds on the Part 9 `Scene`,
`SceneManager`, and `Assets`:

```python
import pydex_ge

class MainMenu(pydex_ge.Scene):
    pass

game = pydex_ge.Game("My Game", 800, 600)

game.scenes.push(
    pydex_ge.SplashScreen(
        logo="assets/logo.png",
        logo_shape="circle",          # "none", "circle", or "rounded"
        name="My Game",
        version="1.0.0",              # rendered as "v1.0.0"
        loadables=[
            ("image", "assets/coin.png"),
            ("font", "assets/fonts/ui.ttf", 16),
            ("sprite_sheet", "assets/player.png", 16, 16),
            lambda assets: assets.image("assets/menu_bg.png"),
        ],
        assets=game.assets,           # reuse (and never destroy) your cache
        next_scene=MainMenu,          # a Scene instance or a callable/class
        game=game,                    # enables ESC / window-close cancel
        loading_speed=2.0,
        min_duration=3.0,
        cancellable=True,
    )
)
```

### Lifecycle

The splash drives itself deterministically from the accumulated
`update(dt)` time — it never `sleep()`s, so it behaves the same at any
frame rate and is easy to test headlessly:

* **checking** — every referenced asset file is verified to exist (missing
  files raise `BackendError`).  The UI only ever shows a generic
  `Checking...`; asset file names never appear on screen.
* **loading** — each `loadables` entry is loaded through the shared
  `Assets` cache, one entry every `1/loading_speed` seconds, while the
  progress bar fills.
* **starting** — a short `Starting...` pause once everything is loaded.
* **done** — once `min_duration` (if set) has elapsed, the splash calls
  `manager.replace(next_scene())` and hands control to the next scene.

`start()` begins (or restarts) the flow and is called automatically from
`on_enter()`; `state`, `progress`, `status`, and `loaded` expose the
current phase, bar value, generic status message, and loaded objects.

### Loadables and the loader registry

`loadables` accepts `('kind', path, ...)` tuples or callables that receive
the shared `Assets`:

* `("image", path)` — `assets.image(path)`
* `("font", path, size)` — `assets.font(path, size)`
* `("sprite_sheet", path, cell_width, cell_height)` — `assets.sprite_sheet(...)`
* `lambda assets: ...` — any callable (may return `None` for side-effect
  loading)

New kinds can be registered with `SplashScreen.register_loader("kind",
loader)` (a class method, so it works from the class or an instance);
`loader` is called as `loader(assets, *args)`.  This is the extension
point for future asset types, including 3D loaders in a later part.

### Resource ownership

* When `assets` is given, the splash reuses it and **never** destroys it.
* When `assets` is omitted, the splash creates a private `Assets`, loads
  everything (including a path-based `logo`) through it, and frees it on
  exit.
* A `logo` passed as an `Image` or `Sprite` is shared and never destroyed.
* ESC or a window-close event calls `game.close()` only when a `game` is
  attached and `cancellable=True`; otherwise those events are ignored
  safely.

### Logo shapes

`logo_shape` clips the logo with the existing 2D drawing primitives over
the solid background (no pixel editing, no extra dependencies):

* `"none"` — the logo is drawn as-is.
* `"circle"` — the logo is clipped to the ellipse inscribed in its image
  box (a true circle for square logos), scanline by scanline.
* `"rounded"` — the logo is clipped to a rounded rectangle with corner
  radius `min(width, height) / 4`.

See `examples/splash.py` for a runnable version: a circle-clipped logo
(whose corner markers visibly disappear), the game name and version, PYDEX
branding, silent file checking, loading of a few generated assets, and an
automatic transition to a menu.  Controls: `ESC` quits (the demo also
closes itself after ~20 seconds).

## Error and Syntax Checking (Part 11)

Part 11 adds a small, headless toolkit for finding problems in a PYDEX
project — no window, no imports of your modules, and no new dependencies.
The checker is:

* **Static** — it only parses and compiles source; it never runs your code.
* **Headless** — no window or game loop is ever started.
* **Safe** — safe to run over a project before running the project.
* **Dependency-free** — it uses only the Python standard library.

### Checking a file or project

```python
import pydex_ge

results = pydex_ge.check_file("main.py")        # one file
report  = pydex_ge.check_project("my_game/")    # every .py file under a folder
report  = pydex_ge.check_project()              # the current directory
```

`check_file` returns a plain list (empty means the file is valid).
`check_project` returns a `CheckReport`, which also behaves like a list
of `CheckResult` objects but adds convenient views:

```python
for problem in report:          # list-like: for / len / indexing still work
    print(problem)              # path:line:column: message

report.errors                   # only error-severity problems
report.warnings                 # only warning-severity problems
report.infos                    # only info-severity problems
report.ok                       # True when there are no errors
print(report)                   # a formatted, human-readable report
```

A syntax error is reported with its exact 1-based `file:line:column`:

```text
my_game/main.py:12:8: invalid syntax
```

### Checking modes

`check_project` runs every check.  You can also run a single family:

```python
report = pydex_ge.check_python(path)   # syntax, imports, undefined names
report = pydex_ge.check_assets(path)   # missing / dynamic / duplicate assets
report = pydex_ge.check_pydex(path)    # PYDEX API, configuration, scenes
report = pydex_ge.check_all(path)      # every check (like check_project)
```

Each `CheckResult` has a stable error `code` (`SYNTAX001`, `IMPORT001`,
`NAME001`, `PYDEX001`/`002`, `CONFIG001`, `SCENE001`, `ASSET001`-`003`,
`PROJECT001`), a `category` (`syntax`/`import`/`name`/`pydex_ge`/
`configuration`/`scene`/`asset`/`project`), and a `severity`
(`error`/`warning`/`info`).

### Command-line use

The same checks are available from the terminal, scanning a folder for you:

```text
python -m pydex_ge.check                 # check the current directory
python -m pydex_ge.check my_game/        # check a specific folder or file
python -m pydex_ge.check --python .      # only Python checks
python -m pydex_ge.check --assets .      # only asset checks
python -m pydex_ge.check --pydex .       # only PYDEX API checks
python -m pydex_ge.check --json .        # machine-readable JSON output
python -m pydex_ge.check --quiet .       # summary only, no problem list
```

The exit code is `0` when there are no errors, `1` when there are, and `2`
when the path does not exist.  Hidden directories, `__pycache__`, and
common vendor/cache folders are skipped, and a `.pydexignore` file next to
the project root is honoured.

### format_error

`pydex_ge.format_error(exc)` renders any exception as one clean line,
preferring the frame that belongs to *your* code rather than PYDEX
internals:

```python
try:
    game = pydex_ge.Game("My Game", 1280, 720)
except pydex_ge.ConfigurationError as exc:
    print(pydex_ge.format_error(exc))
# my_game/main.py:8: ConfigurationError: fps must be a positive number...
```

### Missing assets

Missing files raise `pydex_ge.MissingAssetError` (a subclass of `BackendError`
and `PydexError`).  The message clearly says `Missing asset: <filename>`,
and `requested_by` names the `file:line` that asked for it:

```python
try:
    player = pydex_ge.Sprite("assets/player.png")
except pydex_ge.MissingAssetError as exc:
    print(exc)              # Missing asset: player.png (looked for '...')
    print(exc.requested_by) # my_game/main.py:12
    print(pydex_ge.format_error(exc))
```

### What the checker cannot do

The checker is static, and it is intentionally conservative about what it
reports:

* It cannot reliably detect every runtime error.
* It does not execute project code (no imports, no side effects).
* Dynamic Python behaviour (metaclasses, monkey-patching, `exec`, dynamic
  attribute/asset paths, and so on) may not be detectable statically.
* When it cannot determine something with confidence, it says nothing.

See `examples/check_demo.py` for a runnable demo: a valid file, an
intentional syntax error with its reported line/column, a project scan,
and a missing asset with its requester context.  `examples/manual_check_test.py
--check` is a self-checking demo that proves the checker finds syntax
errors, invalid imports, undefined names, PYDEX typos, configuration
problems, and missing assets.

## Advanced 2D (Part 12)

Part 12 adds an **additive, backward-compatible** layer of 2D features on
top of everything before it.  Every old example still runs unchanged; the
new features are opt-in.

### Transform2D

A reusable position/rotation/scale/origin object with parent/child links.
Children inherit their parent's movement:

```python
ship = pydex_ge.Transform2D(position=(100, 50), rotation=45, scale=(2, 1))
gun  = pydex_ge.Transform2D(position=(20, 0), parent=ship)

ship.position = (200, 80)     # gun follows automatically
gun.world_position            # Vector2(220, 80)
gun.world_rotation            # 45.0 (parent rotation + local rotation)
gun.world_scale               # (2.0, 1.0) (component-wise product)
```

`Transform2D` supports `x`/`y`, `move(dx, dy)`, `add_child`/`remove_child`,
`local_*` vs `world_*` properties, tolerance-based equality, and
validated values (`bool` is rejected everywhere a number is expected).

### Sprite transforms

Sprites gained rotation, a normalized `origin` (`(0, 0)` top-left keeps old
rendering identical, `(0.5, 0.5)` is the center), `flip_x`/`flip_y`,
per-axis `scale` (a plain float when uniform), an optional `parent` (a
`Transform2D` or another `Sprite`), and a `z` draw order:

```python
player = pydex_ge.Sprite("player.png")
player.rotation = 45
player.origin = (0.5, 0.5)     # rotate around the center
player.scale = (2, 1)          # or sprite.scale = 2
player.flip_x = True
player.parent = ship           # draws at ship.world_position
player.z = 5                   # drawn after lower-z objects in a Scene
```

### Renderer and backend transforms

`draw_texture` now accepts `angle`, `center`, `flip`, and `color_mod`, so
rotated/flipped/tinted sprites are forwarded to SDL2's hardware renderer
(`Renderer.copy`) while every backend keeps accepting the old plain
4-argument call.  The renderer also gained an `active_camera` property —
the camera currently between `begin_camera`/`end_camera` — that
world-space helpers like `Parallax` use automatically.

### Scene z-order

`Scene` now draws objects in **stable z-order**: lower `z` draws first,
and objects without a `z` attribute default to `0`, keeping insertion
order for equal values so existing scenes render unchanged.

### Parallax

```python
layer = pydex_ge.Parallax(pydex_ge.Sprite("mountains.png"), factor=0.5)
layer.factor = (0.5, 0.1)      # per-axis scrolling
scene.add(layer)               # drawn through the active camera
```

`factor=1.0` scrolls like a normal world object, `factor=0.0` stays fixed
to the screen, and values in between move at a fraction of the camera
speed.  The offset is **visual only** — the sprite's stored position is
restored after drawing.

### Camera dead zone and shake

```python
camera.dead_zone = (120, 100)  # only follow once the target leaves this zone
camera.shake(10, 0.4)          # deterministic, decays, expires at (0, 0)
camera.shake_offset            # (dx, dy) — visual only, never moves the world
```

Shake is deterministic (no random numbers), a new `shake()` replaces any
active one, and it is applied only inside `world_to_screen` /
`screen_to_world`, so sprites and physics never move.

### TileMap and tile collision

```python
level = pydex_ge.TileMap(40, 24, tile_size=(32, 32))
level.sprite_sheet = pydex_ge.SpriteSheet(tileset, 32, 32)
level.set_tile(3, 4, 1)        # draw sheet cell 1 here; 0 = empty
level.set_solid(1)             # tile 1 blocks the player

level.solid_rects()            # merged horizontal runs of solid tiles
level.collide_body(player_body)  # reuses Body.collide_static per run
level.render(renderer, camera)   # camera-culled: only visible tiles draw
```

`tile_at`, `tile_rect`, `get_tile`, and `clear` round out the grid API.
`render()` skips empty tiles and uses the renderer's active camera when no
camera is passed.

### Named animations with on_finish

```python
sprite.add_animation("idle", pydex_ge.Animation(idle_frames, fps=8))
sprite.add_animation("walk", pydex_ge.Animation(walk_frames, fps=12))
sprite.add_animation("attack", pydex_ge.Animation(attack_frames, fps=15, loop=False))

sprite.play_animation("attack", on_finish=lambda: sprite.play_animation("idle"))
sprite.animation_names        # ["idle", "walk", "attack"]
sprite.current_animation      # "attack"
sprite.stop_animation()       # back to static drawing
```

Re-playing the same animation is a no-op; switching restarts from frame 0;
`on_finish` runs exactly once when a non-looping animation finishes and
may switch to another animation.

### Deterministic 2D effects

```python
sprite.fade_to(0, 1.0)        # fade alpha to 0 over 1 second (sprite.update drives it)
sprite.flash(0.3)             # white flash that fades out
sprite.tint = (255, 0, 0)     # RGB multiply while drawing

# Standalone helpers, all advanced purely by update(dt):
fade  = pydex_ge.graphics.Fade(0, 255, 1.0)     # fade.alpha after update(dt)
flash = pydex_ge.graphics.Flash(1.0)            # flash.strength 1.0 -> 0.0
tint  = pydex_ge.graphics.Tint((255, 0, 0))     # validated RGB multiply
```

Effects advance from `update(dt)` only — deterministic, no threads, no
hidden timers.

### Not included in Part 12

To keep the scope honest, Part 12 does **not** add: an ECS framework,
networking/multiplayer, rigid-body physics (rotation, friction,
restitution, body-to-body), a particle engine, a tilemap editor or
external map importers, a full 3D pipeline, or an advanced rendering
pipeline (post-processing, lights, shaders).  Those remain out of scope
for now.

See `examples/manual_advanced_2d_test.py` for a runnable demo of every
Part 12 feature (headless `--check`, auto-driven `--demo`, or interactive).

## 3D Foundation (Part 3D)

Part 3D adds the first **3D subsystem**: solid meshes rendered entirely on
the CPU.  It builds on the existing 2D engine without breaking it — the 2D
path, sprites, cameras, and scenes all behave exactly as before.

Everything is CPU-side: the renderer projects each triangle with a
perspective camera, back-face culls it, sorts triangles far-to-near
(painter's algorithm), lights it with a single directional light, and
scanline-fills it into horizontal spans using the same 2D line primitive
the engine already has.  No GPU, no shaders, no extra dependencies.

### 3D math

```python
pos  = pydex_ge.Vector3(0, 0, -5)         # x, y, z floats (Vector2's sibling)
dist = pos.distance(pydex_ge.Vector3(1, 1, -4))
n    = pydex_ge.Vector3(0, 1, 0).cross(pydex_ge.Vector3(1, 0, 0))  # -> (0, 0, -1)

rot  = pydex_ge.Quaternion.from_euler(0, 45, 0)    # yaw, pitch, roll (degrees)
rot  = pydex_ge.Quaternion.from_axis_angle((1, 0, 0), 90)
rot.rotate_vector(pydex_ge.Vector3(0, 0, 1))       # rotate a vector
rot.to_euler()                                  # (yaw, pitch, roll) degrees
```

`pydex_ge.Transform3D` mirrors `Transform2D` with a quaternion rotation:

```python
ship = pydex_ge.Transform3D(position=(0, 0, -5), rotation=pydex_ge.Quaternion.from_euler(0, 30, 0))
gun  = pydex_ge.Transform3D(position=(1, 0, 0), parent=ship)
ship.position = (0, 0, -10)     # gun follows automatically
gun.world_position              # parent position + rotated local offset
gun.world_rotation              # parent quaternion * local quaternion
```

### Mesh, material, object

```python
cube = pydex_ge.Object3D(
    mesh=pydex_ge.Mesh.cube(size=2),                    # or Mesh.triangle / Mesh.quad
    material=pydex_ge.Material(color=(200, 80, 40)),
    transform=pydex_ge.Transform3D(position=(0, 0, -6)),
)
cube.rotation = pydex_ge.Quaternion.from_euler(0, 45, 0)
scene.add(cube)          # Object3D is a duck-typed scene object like a Sprite
```

### Camera and lights

```python
camera = pydex_ge.Camera3D()                 # viewport auto-fills from the window
camera.position = (0, 2, -6)
camera.look_at((0, 0, 0))                 # point the camera at the origin
camera.fov = 60                           # vertical field of view, degrees
camera.zoom = 1.0

light = pydex_ge.DirectionalLight(direction=(0, -1, 0), intensity=1.0)
```

### Drawing 3D in a scene

Give the scene a `camera3d` and draw it like any scene:

```python
scene = pydex_ge.Scene(camera3d=camera)
scene.add(cube)
scene.add(ground)           # a second Object3D (a flat quad works as a floor)

# in Game.draw():
self.renderer.clear((15, 15, 20))
scene.draw(self.renderer)   # begin_3d -> draw meshes -> end_3d
```

You can also drive the renderer directly:

```python
self.renderer.begin_3d(camera)
self.renderer.draw_mesh(mesh, transform, material)
self.renderer.draw_line_3d((0, 0, 0), (5, 0, 0), color=(255, 0, 0))  # grid, axes
self.renderer.end_3d()
```

### Limitations (Part 3D)

- **No z-buffer.** Triangles are sorted back-to-front, so two *intersecting*
  triangles may briefly order incorrectly (ordinary non-overlapping objects
  are fine).  This is a foundation, not a complete 3D engine.
- **Flat shading.** Each triangle gets one diffuse color from the material,
  the light, and its face normal.  No textures on meshes yet (a `Material`
  can hold a texture *reference* for forward compatibility).
- **Near-plane clipping.** Triangles and 3D grid lines are clipped against
  the near plane in camera space, so geometry that passes close to the
  camera is **cut, not dropped** — it no longer pops out of existence.
  Faces whose plane lies entirely between the camera and the near plane are
  skipped, which is the standard near limit of any renderer.
- Not included: physics, skeletal animation, terrain, post-processing,
  PBR, GPU rendering, or a full editor.

See `examples/3d_basic.py` for a runnable version: two spinning cubes, a
lit ground grid, a `Camera3D` you move with WASD/Space/Shift and look
around with the arrow keys, FOV up/down, and a HUD (camera position,
rotation, FOV, object count, FPS).  `examples/manual_3d_test.py` exercises
the whole subsystem headlessly (`--check`), in auto-demo mode (`--demo`),
or interactively.

## Audio

### Sound effects and music

```python
# A one-shot sound effect (overlapping plays are fine):
laser = pydex_ge.Sound("sounds/laser.wav")
laser.play()
laser.play(loop=True)          # repeat forever

# A music track (only one track plays at a time):
track = pydex_ge.Music("music/theme.ogg")
track.play()                   # loops by default
track.pause()
track.resume()
track.stop()
```

- **Sound effects overlap.** Every `play()` starts the clip on a free mixer
  channel, so you can fire the same sound many times.
- **One music track at a time.** Starting a new track replaces the one
  currently playing; pause/resume/stop act on that shared music channel.
- Volumes are in the `0.0-1.0` range: per-object `sound.volume` /
  `music.volume` on top of the global levels below. Invalid values raise
  `ConfigurationError`.

### The Audio manager

`pydex_ge.Audio` is a convenient way to control everything at once. It opens
the audio subsystem, caches loaded sounds and tracks, and gives you three
volume levels:

```python
audio = pydex_ge.Audio()

audio.master_volume = 0.8      # overall level
audio.sound_volume = 1.0       # all sound effects
audio.music_volume = 0.6       # all music

laser = audio.load_sound("sounds/laser.wav")   # cached: reused on re-load
theme = audio.load_music("music/theme.ogg")

audio.play_sound("sounds/laser.wav")   # load + play in one call
audio.play_music("music/theme.ogg")

audio.pause()     # pause everything
audio.resume()    # resume everything
audio.stop()      # stop everything
audio.close()     # stop, free resources, shut the subsystem down
```

### Formats and files

- **WAV is the guaranteed format.** The bundled SDL_mixer build also
  decodes **OGG** and **MP3** (and AIFF/VOC) for chunks and music, so those
  generally work too.
- Relative paths resolve against the current working directory; absolute
  paths work as-is. A missing or unreadable file raises a clear
  `BackendError`.
- Audio plays on the SDL2 backend; the null backend (`PYDEX_BACKEND=null`)
  records state so headless code and tests can still exercise the API.
- If no audio device is available, `pydex_ge.Audio(...)` raises a clear
  `BackendError` from SDL_mixer.

See `examples/audio.py` for a runnable version (it generates its own test
tones, so no asset files are needed).

## Python Compatibility

The test suite currently passes on Python 3.14 in this environment. `requires-python` allows 3.11+, but broader cross-version validation is in progress.

## License

MIT — see [LICENSE](LICENSE).
## Support PYDEX-GE

If you find PYDEX-GE useful, please consider [sponsoring its development](https://github.com/sponsors/GOKUCODES-DEV). Your support helps keep the project going!
