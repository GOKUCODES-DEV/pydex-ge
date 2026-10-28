# PYDEX Syntax Manual

A quick-reference guide for writing games with PYDEX, the beginner-friendly
Python game-development framework.

This manual is **reference material**: it shows the correct PYDEX syntax
for each feature so developers can look things up and build their own game.
Every snippet below mirrors real, working PYDEX code.

---

## 1. Your first game (the skeleton every game shares)

```python
import pydex_ge


class MyGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("My Game", 800, 600, fps=60)  # title, width, height
        self.background = (20, 22, 30)                 # RGB clear colour

    def update(self, dt: float) -> None:
        # Called every frame.  dt = seconds since the last frame.
        pass

    def draw(self) -> None:
        # Called every frame after update.  Draw everything here.
        # Use self.renderer for drawing; it takes no argument here.
        pass


if __name__ == "__main__":
    game = MyGame()
    game.run()               # runs until the window is closed
```

Your game class **subclasses** `pydex_ge.Game`.  The `Game` object already
gives you everything you need as attributes:

| Attribute   | What it is                                          |
|-------------|-----------------------------------------------------|
| `game.input`    | keyboard / mouse (`pydex_ge.Input`)                    |
| `game.scenes`   | the scene stack (`pydex_ge.SceneManager`)              |
| `game.window`   | the window (`pydex_ge.Window`)                         |
| `game.renderer` | the drawing surface (`pydex_ge.Renderer`)              |
| `game.clock`    | frames-per-second timing (`pydex_ge.Clock`)            |
| `game.background` | RGB clear colour shown every frame               |
| `game.assets`   | optional, create it yourself (see §9)               |

Constructor: `Game(title='PYDEX', width=800, height=600, *, fps=60,
backend=None)`.  `fps=None` means uncapped.

### The simpler `setup()` style (no `__init__`)

Instead of writing `__init__` and `super().__init__(...)`, override
`setup()` — it is called automatically once a default window already
exists.  Configure the window with `self.screen = (title, width, height)`
(or a 4-tuple ending in `fps`), plus `self.fps` and `self.background`:

```python
import pydex_ge


class MyGame(pydex_ge.Game):
    def setup(self) -> None:
        self.screen = "My Game", 800, 600   # title, width, height
        self.fps = 60
        self.background = (20, 22, 30)

    def update(self, dt: float) -> None:
        pass

    def draw(self) -> None:
        pass


MyGame().run()
```

- `self.screen` reads back the window as `(title, width, height, fps)`
  and can be assigned `(title, width, height)` or `(title, width, height,
  fps)`.
- If you don't override `setup()`, the defaults stay (`"PYDEX"`, 800x600,
  fps 60), so even an empty subclass runs.

---

## 2. Window options

```python
game = pydex_ge.Game("Hello", 1280, 720, fps=144)
print(game.window.width, game.window.height)
game.close()        # close from inside an update()
```

The window can be resized at runtime with `game.window.resize(w, h)` and
the renderer follows automatically.

---

## 3. The scene system (organising your game)

A game is a stack of **scenes** (`pydex_ge.Scene`).  A `Menu` scene, a `Game`
scene, and a `Pause` overlay all derive from `pydex_ge.Scene`.

```python
class MenuScene(pydex_ge.Scene):
    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self.add(pydex_ge.Label("MY GAME", font=pydex_ge.Font(size=40),
                             position=(280, 200), color=(255, 255, 255)))

    def on_enter(self) -> None:      # called when shown
        print("menu shown")

    def on_exit(self) -> None:       # called when suspended/removed
        print("menu hidden")

    def update(self, dt: float) -> None:
        if self.game.input.is_key_pressed("space"):
            self.manager.push(GameScene(self.game))   # overlay a new scene

    def draw(self, renderer) -> None:
        # A Scene's draw always receives the renderer.
        # Scene.draw(renderer) is called every frame after update.
        pass
```

Scene lifecycle hooks you can override:

* `on_enter()` — when the scene becomes the stack top.
* `on_exit()` — when a scene is pushed above it or it is removed.
* `update(dt)` — per-frame logic.
* `draw(renderer)` — per-frame drawing.
* `handle_event(event)` — raw input events (see §11).

Every scene has a `self.manager` (its `SceneManager`) and an `.add(item)`
helper for keeping drawable objects (sprites, labels) that you also pass to
`renderer.draw_*`.

### SceneManager

```python
game.scenes.push(MenuScene(game))     # put a scene on top
game.scenes.pop()                     # remove the top scene
game.scenes.replace(OtherScene(game)) # replace the top without suspend/enter
game.scenes.current                   # the active scene
game.scenes.clear()                   # empty the whole stack
```

`push` suspends the scene below; `pop` reveals and resumes it.  A string is
**not** a valid push argument — always push a `Scene` instance.

---

## 4. Cameras

### 2D camera (`Camera2D`)

```python
self.camera = pydex_ge.Camera2D(800, 600, position=(400, 300), zoom=1.0)
self.camera.bounds = pydex_ge.Rect(0, 0, 1200, 800)   # optional world limits
self.camera.follow(self.player, smoothing=4.0)     # follow a sprite/position
self.camera.shake(6.0, 0.4)                        # screen shake (strength, s)
self.camera.move(100, 0)                           # pan
self.camera.position = (200, 200)                  # teleport
```

In the scene's `draw`, wrap world drawing between `begin`/`end`:

```python
def draw(self, renderer) -> None:
    self.camera.begin(renderer)        # transform into camera space
    renderer.draw_sprite(self.floor)
    self.player.draw(renderer)
    self.camera.end()                  # back to screen space
    renderer.draw_label(self.hud)      # HUD stays put (screen space)
```

`pydex_ge.Camera` is an alias of `Camera2D`.  Camera helpers: `world_to_screen`,
`screen_to_world`, `look_at`, `dead_zone`, `viewport`, `shaking`, `smoothing`.
A camera attached to a scene (`Scene(camera=...)`) is updated automatically.

### 3D camera (`Camera3D`)

```python
self.camera = pydex_ge.Camera3D()
self.camera.position = (0, 3, 10)
self.camera.rotation = pydex_ge.Quaternion.from_euler(0.0, -8.0, 0.0)  # yaw pitch roll
self.camera.fov = 70                 # 1..179 (default 60)
self.camera.move(1, 0, 0)            # camera-relative movement
self.camera.look_at((0, 0, -1))      # point the camera at a position
```

Use it with a `Scene(camera3d=self.camera)` or drive the renderer yourself:

```python
renderer.begin_3d(self.camera)
renderer.draw_mesh(self.cube, self.material_a)   # and draw_line_3d, etc.
renderer.end_3d()
```

---

## 5. Sprites

```python
player = pydex_ge.Sprite("assets/player.png")          # from a file
player = pydex_ge.Sprite(image_obj)                    # from an Image
player = pydex_ge.Sprite.from_pixels(16, 16, rows)     # from raw RGBA data

player.position = (100, 50)         # top-left corner
player.x = 100                      # integer pixel coords
player.y = 50
player.flip_x = True                # mirror horizontally
player.flip_y = False
player.rotation = 45                # degrees
player.origin = (0.5, 0.5)          # centre pivot (0..1)
player.scale = (2, 1)               # per-axis, or scale = 2 for uniform
player.alpha = 128                  # opacity 0..255
player.visible = False
player.z = 5                        # draw order within a scene
player.parent = other_sprite        # optional Transform2D/Sprite parent
```

Draw with `sprite.draw(renderer)` or `renderer.draw_sprite(sprite)`.

### Sprite from a region or pixel data

```python
sprite = pydex_ge.Sprite(sheet_image, region=(0, 0, 16, 16))   # crop a sheet
```

### Sprite-specific shorthand

`pydex_ge.Sprite("player.png")` itself finds the asset file.  See §9 for the
`Assets` cache and §10 for `from_file` details.

---

## 6. Animations

```python
sheet = assets.sprite_sheet("player.png", 16, 16)   # 16x16 cells

sprite.animations["idle"] = sheet.animation([(0, 0)], fps=2, loop=True)
sprite.animations["walk"] = sheet.animation_run(0, 0, 4, fps=10, loop=True)
sprite.play_animation("walk")
sprite.pause()          # pause all animation
sprite.play()           # resume playback
sprite.stop()           # stop and reset
sprite.stop_animation() # remove the animation; return to static drawing
current = sprite.current_animation
```

Standalone animations also exist:

```python
anim = pydex_ge.Animation(frames, fps=10, loop=True, speed=1.0)
frame = anim.current_frame      # the current frame object
anim.update(dt)                 # advance manually
```

---

## 7. Text, fonts, and labels

```python
title = pydex_ge.Font(size=40)                       # default framework font
custom = pydex_ge.Font("assets/font.ttf", size=24)   # a real font file

label = pydex_ge.Label("Score: 0", font=title, position=(12, 12), color=(255, 220, 120))
label.text = "Score: 5"       # update in-place
label.position = (20, 20)
label.x = 20
label.color = (200, 200, 200)
renderer.draw_label(label)    # or label.draw(renderer)
```

`pydex_ge.Text` is an alias of `pydex_ge.Label`.  A label that uses a shared
`font=` (as above) cannot change size in place — pass a different `Font`
at construction, e.g. `pydex_ge.Label("hi", font=pydex_ge.Font(size=32))`.
(This still raises `pydex_ge.MissingAssetError` for a missing font file.)

---

## 8. Drawing shapes and lines

```python
renderer.draw.line(0, 0, 100, 100, color=(255, 255, 255))
renderer.draw.rect(10, 10, 60, 40, color=(255, 0, 0), filled=True)
renderer.draw.circle(200, 200, 30, color=(0, 255, 0), filled=False)
renderer.draw.pixel(5, 5, color=(255, 255, 255))
```

In 3D scenes:

```python
renderer.begin_3d(camera)
renderer.draw_line_3d((0, 0, 0), (5, 0, 0), color=(255, 255, 255))
renderer.draw_mesh(mesh, material)
renderer.end_3d()
```

---

## 9. Loading assets

```python
self.assets = pydex_ge.Assets()          # an asset cache (create it yourself)

image = self.assets.image("coin.png")                       # cached Image
sheet = self.assets.sprite_sheet("player.png", 16, 16)      # cached SpriteSheet
font  = self.assets.font("font.ttf", size=24)               # cached Font

self.assets.contains("coin.png")   # True if already cached
self.assets.clear()              # drop all cached assets
```

### Loading directly (no cache)

```python
img  = pydex_ge.Image("assets/title.png")        # raises MissingAssetError
font = pydex_ge.Font("assets/font.ttf", size=20)
snd  = pydex_ge.Sound("assets/click.wav")
mus  = pydex_ge.Music("assets/theme.ogg")
```

`Assets.image/font/sprite_sheet` and `Sprite.from_file` all accept the same
path and return the **same cached object** for repeated calls.

---

## 10. Missing-asset behaviour (standard PYDEX contract)

Loading a file that does not exist raises `pydex_ge.MissingAssetError` with
`Missing asset: <filename>` in the message.  You can catch it:

```python
try:
    player = pydex_ge.Sprite("assets/player.png")
except pydex_ge.MissingAssetError as exc:
    print(exc)               # Missing asset: player.png (looked for '...')
    print(exc.requested_by)  # my_game/main.py:12  (which file:line asked)
```

---

## 11. Input

```python
if game.input.is_key_pressed("space"):   # just this frame
    jump()
if game.input.is_key_down("left"):       # held down (per-frame state)
    move(-1)
if game.input.is_key_released("a"):
    release()

if game.input.is_button_pressed("left"): # mouse button
    shoot()
mouse = game.input.mouse_position        # (x, y)
dx, dy = game.input.mouse_delta          # movement since last frame
```

Key names are strings and case-insensitive: `"space"`, `"escape"`, `"w"`,
`"left"`, `"shift"`, `"up"`, letters `"a"`…`"z"`, numbers, `"enter"`,
`"tab"`, etc.  `pydex_ge.Keys` documents the full list.

`Input` also exposes `is_key_held` (an alias for `is_key_down`),
`is_button_down`, `is_button_released`, `mouse_x`, `mouse_y`.

---

## 12. Events

```python
if game.input.is_key_pressed("q"):
    game.close()                 # quit the whole application
```

`Game.run` pumps events for you.  Inside a scene you can also override
`handle_event`:

```python
def handle_event(self, event) -> None:
    if event.type == pydex_ge.EventType.QUIT:
        self.manager.clear()
```

`EventManager` (`game.input` uses one internally) offers
`has_quit()`, `poll()`, `get()`, `clear()`.

---

## 13. Physics

2D physics is AABB-based: `Body` + `World`, with `Rect` and `Vector2`
math helpers.

```python
from pydex_ge.physics import World, Body, Rect, Vector2

world = pydex_ge.World(gravity=(0, 500))          # pixels/second^2

player = pydex_ge.Body(position=(100, 0), size=(32, 32), velocity=(0, 0))
world.add_body(player)

floor = Rect(0, 550, 800, 600)
world.static_rects.append(floor)               # collidable ground

# per-frame:
world.update(dt)                               # integrate bodies + resolve statics
if player.collides_with(floor):                # overlap test (single Rect)
    print("on the floor")
for rect in world.static_rects:                # optional manual resolution
    if player.collide_static(rect):            # takes ONE Rect, not the list
        on_ground = True
```

`Body` helpers: `apply_force`, `apply_impulse`, `copy`, `rect`, `colreach`.
`Rect` helpers: `overlaps`, `contains_point`, `intersection`, `union`,
`inflate`, `center`.
`Vector2` helpers: `dot`, `cross`, `length`, `normalized`, `rotate`,
`perpendicular`, `clamp_length`, `from_polar`.

---

## 14. Tilemaps

```python
sheet = self.assets.sprite_sheet("tiles.png", 16, 16)

tilemap = pydex_ge.TileMap(30, 20, tile_size=(32, 32), sprite_sheet=sheet)
tilemap.set_tile(5, 3, 2)          # col, row, tile id (1..) into the sheet
tilemap.set_solid(2, True)         # mark tile id 2 as solid (per tile id)
if tilemap.is_solid(2):            # is tile id 2 solid?
    ...
cell = tilemap.get_tile(5, 3)      # tile id at a cell
rect = tilemap.tile_rect(5, 3)     # Rect for a cell

tilemap.render(self.renderer)      # draw the whole map (no return value)
# with camera culling:
tilemap.render(self.renderer, camera=self.camera)
```

`TileMap.solid_rects()` returns merged world `Rect`s for every solid tile
(see §13) and you resolve a body with `tilemap.collide_body(body)`.
`set_solid`/`is_solid` apply to a tile **id** (a sheet index), not to a
specific cell.

---

## 15. Particle-free 2D extras

### Parallax background layers

```python
layer = pydex_ge.Parallax(sprite, factor=0.25)   # moves slower with the camera
layer = pydex_ge.Parallax(sprite, factor=(0.2, 0.5))  # per-axis
layer.draw(renderer)
```

### Sprite flash / fade

```python
sprite.flash(0.3, (255, 80, 80))        # flash a colour for `duration` seconds
sprite.fade_to(0, duration=1.0)         # fade alpha to a value
sprite.tint = (255, 0, 0)               # colour tint
```

### Transform2D (parent/child 2D transforms)

```python
ship = pydex_ge.Transform2D(position=(100, 50), rotation=45, scale=(2, 1))
gun  = pydex_ge.Transform2D(position=(20, 0), parent=ship)
ship.position = (200, 80)     # gun follows automatically
gun.world_position            # Vector2(220, 80)
gun.move(5, 0)                # local move
```

`Transform2D` API: `position`, `local_position`, `rotation`, `scale`,
`x`/`y`, `move`, `add_child`, `remove_child`, `world_*` properties,
`origin`.

---

## 16. Audio

```python
audio = pydex_ge.Audio()
snd = audio.load_sound("click.wav")    # cached Sound
mus = audio.load_music("theme.ogg")    # cached Music

snd.volume = 0.5
snd.play(loop=False)                   # play a Sound (already loaded)
mus.volume = 0.7
mus.play(loop=True)
audio.play_sound("click.wav", loop=False)   # play by path
audio.play_music("theme.ogg", loop=True)    # play by path
audio.master_volume = 1.0
audio.music_volume = 0.6
audio.sound_volume = 0.8
audio.stop_sounds()
audio.stop_music()
audio.close()          # free the audio backend
```

`Sound`/`Music` also have `pause`, `resume`, `stop`, `volume`, `playing`,
`paused`, `destroy`.  Audio calls are silently safe on the headless/null
backend, so your game still runs in tests.

---

## 17. 3D objects, meshes, materials, and lights

```python
mesh = pydex_ge.Mesh.cube(size=2)               # a cube spanning [-size, size]
quad = pydex_ge.Mesh.quad(a, b, c, d)           # a quad from 4 corner positions
tri  = pydex_ge.Mesh.triangle(a, b, c)          # a triangle from 3 corner positions
obj  = pydex_ge.Object3D(mesh=mesh, material=mat)

mat = pydex_ge.Material(color=(230, 120, 60), emission=(15, 6, 0), opacity=1.0)
mat.texture = texture              # optional Texture

light = pydex_ge.DirectionalLight(direction=(0.6, -1, 0.8), intensity=0.9,
                               ambient=0.35, color=(255, 255, 255))
light.enabled = False               # turn a light on/off
```

`Mesh` gives `vertices` (positions), `indices`, `uvs`, `face_normals`,
`bounding_radius`, `vertex_count`.  `Object3D` mirrors a `Transform3D`
(`position`, `rotation`, `scale`, `move`) and you draw it with
`renderer.draw_mesh(obj.mesh, obj.material)` inside a `begin_3d`/`end_3d`
block (see §4).  Quaternions drive 3D rotation:

```python
q = pydex_ge.Quaternion.from_euler(yaw, pitch, roll)      # degrees
v = pydex_ge.Vector3(1, 2, 3)
rotated = q * v          # or q.rotate_vector(v)
q2 = q * q1              # combine rotations
yaw, pitch, roll = q.to_euler()
```

---

## 18. Splash screen

```python
splash = pydex_ge.SplashScreen(
    logo="assets/logo.png",
    name="My Game",
    version="1.0",
    loading_text="Loading...",
    loadables=[
        ("image", "assets/player.png"),
        ("font", "assets/font.ttf", 24),   # font entries take a size
    ],
)
game.scenes.push(splash)
```

The splash auto-checks its files, shows a progress bar, and transitions to
`next_scene` when loaded.

---

## 19. The checker (find problems before running)

PYDEX ships a static, headless project checker — run it on your game folder
to catch mistakes without opening a window:

```python
import pydex_ge
report = pydex_ge.check_project()          # checks the current directory
for problem in report:
    print(problem)                      # path:line:column: message
if report.ok:
    print("No errors!")
```

Or from the terminal:

```text
python -m pydex_ge.check .                 # check this project
python -m pydex_ge.check --json .          # machine-readable output
python -m pydex_ge.check --python .        # Python-only checks
python -m pydex_ge.check --assets .        # asset-path checks
python -m pydex_ge.check --pydex_ge .         # PYDEX API checks
```

What it catches: invalid syntax, bad `from pydex_ge import x`, undefined
names, PYDEX typo near-misses (`Camra2D` → `Camera2D`), invalid
configuration (`Game(fps="high")`, `Camera3D(fov=0)`), `SceneManager.push`
with a string, and missing asset paths.  Full documentation lives in
`docs/checking-manual.md`.

---

## 20. Error handling

```python
from pydex_ge.exceptions import ConfigurationError, MissingAssetError, PydexError

try:
    game = pydex_ge.Game("x", 640, 480, fps=0)   # invalid fps
except pydex_ge.ConfigurationError as exc:
    print(pydex_ge.format_error(exc))            # file:line: ConfigError: msg
```

| Exception          | Raised for |
|--------------------|------------|
| `pydex_ge.PydexError`      | base class of all PYDEX errors |
| `pydex_ge.ConfigurationError` | invalid framework settings/values |
| `pydex_ge.BackendError`    | backend (renderer/audio) failures |
| `pydex_ge.MissingAssetError` | a requested file does not exist |

`pydex_ge.format_error(exc)` renders any exception as one clean
`file:line: ErrorType: message` line, preferring the frame in *your* code.

---

## 21. Running headless (tests / CI)

The null backend lets your game log in and run without a window or SDL:

```python
import pydex_ge
from pydex_ge.backend.null import NullBackend

game = pydex_ge.Game("Test", 320, 240, backend=NullBackend())
game.run(max_frames=5)     # advance a handful of frames, then stop
```

Everything else stays the same, so you can unit-test scenes and helpers
without opening windows.

---

## 22. Common pitfalls

* `SceneManager.push` only accepts `Scene` instances — never a string name.
* `Camera2D.begin/end` pair: every `begin` needs a matching `end`.
* `Game.fps` must be a positive number or `None` — a string like `"60"` is
  a configuration error.
* `Camera3D.fov` must be between 1 and 179; `zoom` must be greater than 0.
* Assets are cached: if you change a file on disk at runtime, clear the
  cache (`assets.clear()`) or the old image stays in memory.
* `sprite.position` is a pixel-coordinate `(x, y)` tuple; `sprite.x`/`y` are
  ints.  Use the camera helpers to convert world-to-screen coordinates.

---

## 23. Full public API

Every name below is importable from `pydex_ge` (or from its submodule):

```text
Animation  Assets  Audio  BackendError  Body  Camera  Camera2D  Camera3D
CheckReport  CheckResult  Clock  ConfigurationError  DirectionalLight  Event
EventManager  EventType  Font  Game  Image  Input  Keys  Label  Material  Mesh
MissingAssetError  Music  Object3D  Parallax  PydexError  Quaternion  Rect
Renderer  Scene  SceneManager  Sound  Sprite  SpriteSheet  SplashScreen  Text
Texture  TextureRegion  TileMap  Transform2D  Transform3D  Vector2  Vector3
Window  World

check_file  check_project  check_python  check_assets  check_pydex  check_all
format_error  format_result

Assets:      image/ font/ sprite_sheet/ contains/ clear/ remove
Audio:       load_sound/ load_music/ play_* / stop_* / volumes
Camera2D:    follow/ look_at/ move/ begin/ end/ shake/ bounds/ viewport
Camera3D:    look_at/ move/ project/ fov/ near/ far/ aspect/ forward/ right/ up
Game:        run/ close/ update/ draw/ setup/ screen/ input/ scenes/ window/
             renderer/ clock
Input:       is_key_down/ held/ pressed/ released   is_button_*
Scene:       add/ remove/ clear/ update/ draw/ handle_event/ on_enter/ on_exit
SceneManager: push/ pop/ replace/ current/ clear
Sprite:      position/ x/ y/ rotation/ scale/ origin/ flip_* / alpha/ parent
             play_animation/ play/ pause/ fade_to/ flash/ tint/ from_pixels
TileMap:     set_tile/ get_tile/ set_solid/ is_solid/ render/ solid_rects
```

See the example programs in `examples/` for complete, runnable games:
`foundation.py`, `scenes.py`, `sprites.py`, `physics.py`, `3d_basic.py`,
`audio.py`, `input_sound_label.py`, and others.  The `snake.py` at the
project root is a complete start-to-finish Snake game that uses the
`setup()` style from §1.