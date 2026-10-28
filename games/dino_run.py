"""PYDEX field-test: Chrome Dino (the endless runner).

A faithful-in-spirit remake of the Chrome offline "dino" game: a dino auto-runs
across a scrolling desert, jumping cacti and ducking pterodactyls while the
speed and score climb.  The palette flips to night every 500 points, exactly
like the original.

Everything is procedural -- the sprite sheets (PNG) and sound effects (WAV) are
generated at runtime into a private temp directory with the standard library
alone, so no asset files are committed and nothing is downloaded.

Controls
--------
* **Space** / **Up** / **W** -- jump (hold longer to jump higher)
* **Down** / **S** -- duck (and fast-fall while airborne)
* **R** -- restart
* **ESC** -- quit

Run with:  python games/dino_run.py
"""

from __future__ import annotations

import os
import random
import tempfile

from _gen import png_bytes, tone, wav_bytes

import pydex_ge

W, H = 900, 380
FPS = 60

# --- world metrics (all distances are in final on-screen pixels) -------------
GROUND_Y = 300           # y of the ground line
CELL = 22                # sprite art grid size
SCALE = 3                # art pixels -> screen pixels
DINO_W = CELL * SCALE    # 66
DINO_H = CELL * SCALE

DINO_X = 70              # the dino never moves horizontally
DUCK_H = 34              # dino hitbox height while ducking (art is ~11 rows)

GRAVITY = 2400.0
JUMP_VELOCITY = -830.0
JUMP_CUT = 1.9           # extra gravity once the jump key is released early
DUCK_FALL_BOOST = 2.4    # extra gravity multiplier while ducking mid-air
MAX_FALL = 1600.0

SPEED_START = 300.0
SPEED_MAX = 780.0
SPEED_RAMP = 7.5         # px/s added per second of survival

SCORE_DIVISOR = 12.0     # pixels travelled per point
NIGHT_SCORE = 500        # palette flips to night every NIGHT_SCORE points
BIRD_SCORE = 320         # pterodactyls start appearing at this score

# Pterodactyl altitudes, in art rows above the ground.  "low" cannot be ducked
# under (jump it), "mid" can only be ducked under, and "high" sails overhead.
BIRD_ALTITUDE = {"low": 2, "mid": 8, "high": 14}
BIRD_SAFE_ALTITUDE = BIRD_ALTITUDE["high"]
BIRD_CHANCE = 0.32       # odds an obstacle is a pterodactyl once they unlock

# Cacti are drawn from one sheet and squashed per kind to vary their height.
CACTUS_SQUASH = {"small": 0.8, "large": 1.0, "triple": 0.9}

# Spawn pacing: seconds between obstacles, shrinking as the run speeds up.
GAP_MIN = 0.75
GAP_MAX = 1.45
GAP_SLACK = 0.25         # extra random room on top of the shrinking window

# Scenery.
CLOUD_COUNT = 4
CLOUD_PARALLAX = 0.18    # fraction of the scroll speed the clouds travel at
GROUND_DASH = 60         # px between ground dashes

# --- palette ----------------------------------------------------------------
# Sprite art is pure white and recoloured per frame with Sprite.tint, which is
# what flips the entire game between day and night.
DAY_BG = (255, 255, 255)
DAY_FG = (53, 53, 53)    # the authentic Chrome dino grey
NIGHT_BG = (23, 23, 23)
NIGHT_FG = (216, 216, 216)


# =============================================================================
# Sprite art.  Each grid is 22x22 characters: '#' paints a pixel, '.' is
# transparent.  The dino faces RIGHT (the direction of travel).
# =============================================================================

# The dino faces RIGHT (the direction of travel).  Its eye is a 3x2 gap in the
# head art on rows 2-3, present in every frame.

DINO_STAND = [
    ".......#########......",
    "......###########.....",
    "......#####..######...",
    "......#####..######...",
    "......###########.....",
    ".....#############....",
    "....###############...",
    "...#################..",
    "..###################.",
    "..###################.",
    ".####..########..####.",
    "###...#########...####",
    "##....########....####",
    "#..............#####..",
    ".............#####....",
    ".............####.....",
    ".............####.....",
    "............#####.....",
    "............#####.....",
    "...........######.....",
    "...........######.....",
    "..........#######.....",
]

DINO_RUN1 = [
    ".......#########......",
    "......###########.....",
    "......#####..######...",
    "......#####..######...",
    "......###########.....",
    ".....#############....",
    "....###############...",
    "...#################..",
    "..###################.",
    "..###################.",
    ".####..########..####.",
    "###...#########...####",
    "##....########....####",
    "#..............####...",
    ".............#####....",
    "............#####.....",
    "...........######.....",
    "..........#######.....",
    ".........######.......",
    "........#####.........",
    ".......####...........",
    "......####............",
]

DINO_RUN2 = [
    ".......#########......",
    "......###########.....",
    "......#####..######...",
    "......#####..######...",
    "......###########.....",
    ".....#############....",
    "....###############...",
    "...#################..",
    "..###################.",
    "..###################.",
    ".####..########..####.",
    "###...#########...####",
    "##....########....####",
    "#..............####...",
    ".............#####....",
    ".............####.....",
    "............#####.....",
    "...........######.....",
    "..........#######.....",
    "..........#####.......",
    "........#####.........",
    ".......####...........",
]

DINO_JUMP = [
    ".......#########......",
    "......###########.....",
    "......#####..######...",
    "......#####..######...",
    "......###########.....",
    ".....#############....",
    "....###############...",
    "...#################..",
    "..###################.",
    "..###################.",
    ".#####.########..#####",
    "####..#########...####",
    "##....########....####",
    "##.............#####..",
    "#.............######..",
    "............#######...",
    "...........######.....",
    "..........#####.......",
    "..........#####.......",
    ".........####.........",
    "........####..........",
    "......................",
]

# Ducking: a wide, low silhouette whose feet sit on the ground line.
DINO_DUCK = [
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......#########.......",
    ".....###########..#...",
    "....#############.##..",
    "...#################..",
    "..##################..",
    ".#####.########..#####",
    "####..#########...####",
    "##....########....####",
    "##.............#####..",
    "#.............######..",
    "............#######...",
    "...........######.....",
    "..........#####.......",
    "..........#####.......",
]

DINO_CRASH = [
    ".......#########......",
    "......###########..#..",
    "......#####..######..#",
    "......#####..######..#",
    "......###########..#..",
    ".....#############..#.",
    "....###############.##",
    "...#################..",
    "..###################.",
    "..###################.",
    ".####..########..####.",
    "###...#########...####",
    "##....########....####",
    "#..............#####..",
    ".............#####....",
    ".............####.....",
    ".............####.....",
    "............#####.....",
    "............#####.....",
    "...........######.....",
    "...........######.....",
    "..........#######.....",
]

CACTUS_SMALL = [
    "......##..............",
    "......##..............",
    "..####.##....####.....",
    "..####.##....####.....",
    "..####.##....####.....",
    "..####.##....####.....",
    "..####.##....####.....",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
    "..####.########.####..",
]

CACTUS_LARGE = [
    "..........##..........",
    "..........##..........",
    "..........##..........",
    ".....####.##.####.....",
    ".....####.##.####.....",
    ".....####.##.####.....",
    ".....####.##.####.....",
    ".....####.##.####.....",
    ".....####.##.####.....",
    "....###############...",
    "....###############...",
    "....###############...",
    "....###############...",
    "....###############...",
    "....###############...",
    "....###############...",
    "....###############...",
    "....###############...",
    "....###############...",
    "....###############...",
    "....###############...",
    "....###############...",
]

CACTUS_TRIPLE = [
    "......................",
    "......##..............",
    "......##......##..##..",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
    "..##.###.####.##.##...",
]

# Pterodactyl, seen from the side flying right: a slim body with a beaked head
# on the right, a tail on the left, and one big wing.  The body occupies rows
# 9-13 in every frame so the hitbox stays put while it flies; only the wing
# changes position, and both carry a small gap for an eye.
BIRD_BODY = {
    9:  "....##.....#########..",
    10: "...###...###########..",
    11: "..####..#############.",
    12: "..####..############..",
    13: "...##....##########...",
}

BIRD_WINGS = (
    {  # wing swept up and back over the body
        4: "..........#####.......",
        5: "........#########.....",
        6: ".......###########....",
        7: "......#############...",
        8: ".....###############..",
    },
    {  # wing level, tucked against the body
        7: ".........##########...",
        8: "........############..",
    },
    {  # wing swept down and forward under the body
        14: "................#####.",
        15: "..............#######.",
        16: "............#########.",
        17: "..........###########.",
        18: "........############..",
    },
)


def _bird_frame(wings: dict[int, str]) -> list[str]:
    """Compose one pterodactyl frame from the shared body plus a wing pose."""
    grid = ["." * CELL for _ in range(CELL)]
    for y, line in {**wings, **BIRD_BODY}.items():
        grid[y] = line
    # A one-pixel eye, cut out of the art so it reads as a hole.
    eye_row = grid[10]
    grid[10] = eye_row[:15] + "." + eye_row[16:]
    return grid


BIRD_UP, BIRD_LEVEL, BIRD_DOWN = (_bird_frame(w) for w in BIRD_WINGS)

CLOUD = [
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......####............",
    "....########..........",
    "...##########..####...",
    "..############.######.",
    "..###################.",
    "..###################.",
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
    "......................",
]


# =============================================================================
# Rasterising helpers
# =============================================================================

def norm_grid(grid) -> list[str]:
    """Pad or trim an art grid to exactly ``CELL`` rows of ``CELL`` characters.

    Hand-drawn art is easy to mistype, and a ragged grid would silently shift
    every pixel after the short row, so normalise here rather than at 30 call
    sites.  Padding is transparent; trimming drops the overflow.
    """
    rows = [line.ljust(CELL, ".")[:CELL] for line in grid[:CELL]]
    rows += ["." * CELL] * (CELL - len(rows))
    return rows


def grid_pixels(grid) -> bytes:
    """Rasterise a character ``grid`` into ``CELL * CELL * 4`` RGBA bytes.

    Every painted pixel is opaque white, so the art is recoloured at draw time
    with ``Sprite.tint`` (that is what flips the whole game between day and
    night).  Transparent characters become fully transparent pixels, which is
    also how the dino's eye and the pterodactyl's are cut out -- they are simply
    gaps in the art.
    """
    out = bytearray()
    for line in norm_grid(grid):
        for ch in line:
            out += bytes((255, 255, 255, 255) if ch == "#" else (0, 0, 0, 0))
    return bytes(out)


def write_png(path: str, grids) -> str:
    """Write ``grids`` side by side as one horizontal sprite strip."""
    cells = [grid_pixels(grid) for grid in grids]
    rows: list[bytes] = []
    for y in range(CELL):
        line = bytearray()
        for cell in cells:
            line += cell[y * CELL * 4 : (y + 1) * CELL * 4]
        rows.append(bytes(line))
    with open(path, "wb") as handle:
        handle.write(png_bytes(CELL * len(cells), CELL, rows))
    return path


# =============================================================================
# Obstacles & scenery
# =============================================================================

class Obstacle:
    """A scrolling hazard: cactus or pterodactyl.

    ``kind`` is one of ``small``/``large``/``triple``/``bird``.  The hitbox is
    deliberately a little smaller than the art so near-misses feel fair, and
    cacti are scaled down vertically by ``squash`` to vary the obstacle heights.
    """

    def __init__(self, kind: str, x: float, sprite, squash: float = 1.0) -> None:
        self.kind = kind
        self.x = x
        self.sprite = sprite
        self.squash = squash
        # Birds fly above the ground; this is how far their art bottom sits up.
        self.y_offset = 0.0
        self.art_h = DINO_H

    def _box(self) -> tuple[int, int, int, int]:
        """Hitbox in art units: (x, y, width, height) from the sprite's top-left.

        The columns run 0..CELL-1 and the rows run 0..CELL-1 from the top of the
        cell, so the hitbox sits inside the drawn art with a small margin.  Birds
        use just the body rows so flapping wings cannot cause unfair hits.
        """
        if self.kind == "bird":
            return (2, 8, CELL - 4, 7)
        return (1, 1, CELL - 1, CELL - 1)

    @property
    def top(self) -> float:
        return GROUND_Y - self.art_h - self.y_offset

    @property
    def rect(self) -> pydex_ge.Rect:
        bx, by, bw, bh = self._box()
        return pydex_ge.Rect(
            self.x + bx * SCALE,
            self.top + by * SCALE * self.squash,
            bw * SCALE,
            bh * SCALE * self.squash,
        )

    def update(self, dt: float, speed: float) -> None:
        self.x -= speed * dt
        self.sprite.x = int(self.x)
        if self.kind == "bird":
            self.sprite.animation.update(dt)

    @property
    def offscreen(self) -> bool:
        return self.x < -DINO_W


class Cloud:
    """A slow parallax background cloud."""

    def __init__(self, x: float, y: float, sprite, speed_factor: float) -> None:
        self.x = x
        self.y = y
        self.speed_factor = speed_factor
        self.sprite = sprite
        sprite.position = (int(x), int(y))

    def update(self, dt: float, speed: float) -> None:
        self.x -= speed * self.speed_factor * dt
        if self.x < -DINO_W:
            self.x = W + random.uniform(0, 260)
            self.y = random.uniform(40, 150)
        self.sprite.position = (int(self.x), int(self.y))


# =============================================================================
# The game
# =============================================================================

class DinoRunGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Chrome Dino", W, H, fps=FPS)
        self.background = DAY_BG

        self._build_assets()
        self._build_sprites()
        self._build_audio()
        self._build_labels()

        self.best = 0
        self.night = False
        self.reset()

    # -- setup ------------------------------------------------------------

    def _build_assets(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name

        self.dino_path = write_png(
            os.path.join(base, "dino.png"),
            [DINO_STAND, DINO_RUN1, DINO_RUN2, DINO_JUMP, DINO_DUCK, DINO_CRASH],
        )
        self.cactus_path = write_png(
            os.path.join(base, "cactus.png"), [CACTUS_SMALL, CACTUS_LARGE, CACTUS_TRIPLE]
        )
        self.bird_path = write_png(
            os.path.join(base, "bird.png"), [BIRD_UP, BIRD_LEVEL, BIRD_DOWN]
        )
        self.cloud_path = write_png(os.path.join(base, "cloud.png"), [CLOUD])

        def write_wav(name: str, samples) -> str:
            path = os.path.join(base, name)
            with open(path, "wb") as handle:
                handle.write(wav_bytes(samples))
            return path

        # Jump: a short upward chirp.  Duck: a low blip.  Crash: a noise burst.
        self.jump_path = write_wav("jump.wav", tone(520, 0.11, decay=True))
        self.duck_path = write_wav("duck.wav", tone(180, 0.07, decay=True))
        self.crash_path = write_wav(
            "crash.wav",
            tone(140, 0.30, volume=0.9) + tone(90, 0.22, volume=0.7),
        )
        self.point_path = write_wav("point.wav", tone(880, 0.06) + tone(1320, 0.10))

    def _build_sprites(self) -> None:
        self.assets = pydex_ge.Assets()
        self.dino_sheet = self.assets.sprite_sheet(self.dino_path, CELL, CELL)
        self.cactus_sheet = self.assets.sprite_sheet(self.cactus_path, CELL, CELL)
        self.bird_sheet = self.assets.sprite_sheet(self.bird_path, CELL, CELL)
        self.cloud_sheet = self.assets.sprite_sheet(self.cloud_path, CELL, CELL)

        # Column order matches _build_assets(): stand, run1, run2, jump, duck, crash.
        self.dino = pydex_ge.Sprite(self.dino_sheet.image)
        self.dino.scale = float(SCALE)
        self.dino.animations["stand"] = self.dino_sheet.animation([(0, 0)], fps=1, loop=True)
        self.dino.animations["run"] = self.dino_sheet.animation(
            [(1, 0), (2, 0)], fps=14, loop=True
        )
        self.dino.animations["jump"] = self.dino_sheet.animation([(3, 0)], fps=1, loop=True)
        self.dino.animations["duck"] = self.dino_sheet.animation([(4, 0)], fps=1, loop=True)
        self.dino.animations["crash"] = self.dino_sheet.animation([(5, 0)], fps=1, loop=True)
        self.dino.play_animation("stand")

        self._cactus_sprites = [
            pydex_ge.Sprite(self.cactus_sheet.image) for _ in range(24)
        ]
        self._bird_sprites = [pydex_ge.Sprite(self.bird_sheet.image) for _ in range(12)]
        for sprite in self._cactus_sprites + self._bird_sprites:
            sprite.scale = float(SCALE)
            sprite.visible = False

        self._cloud_sprites = [
            pydex_ge.Sprite(self.cloud_sheet.image) for _ in range(CLOUD_COUNT)
        ]
        for sprite in self._cloud_sprites:
            sprite.scale = float(SCALE)
            sprite.visible = False

    def _build_audio(self) -> None:
        self.audio = None
        try:
            self.audio = pydex_ge.Audio()
            self.audio.master_volume = 0.55
        except Exception:
            self.audio = None

    def _build_labels(self) -> None:
        self.font = pydex_ge.Font(size=20)
        self.big_font = pydex_ge.Font(size=30)

        self.score_label = pydex_ge.Label(
            "0", font=self.big_font, position=(0, 40), color=DAY_FG
        )
        self.best_label = pydex_ge.Label(
            "HI 0", font=self.font, position=(0, 14), color=DAY_FG
        )
        self.hint_label = pydex_ge.Label(
            "SPACE jump   DOWN duck   R restart   ESC quit",
            font=pydex_ge.Font(size=13),
            position=(0, H - 26),
            color=DAY_FG,
        )
        self.banner = pydex_ge.Label(
            "", font=pydex_ge.Font(size=26), position=(0, 150), color=DAY_FG
        )
        self.sub = pydex_ge.Label(
            "", font=pydex_ge.Font(size=15), position=(0, 195), color=DAY_FG
        )

    # -- state ------------------------------------------------------------

    def reset(self) -> None:
        """Start a fresh run (also used by R and by the jump-after-crash)."""
        self.score = 0
        self.elapsed = 0.0
        self.speed = SPEED_START
        self.distance = 0.0

        self.dino_y = float(GROUND_Y - DINO_H)
        self.vy = 0.0
        self.grounded = True
        self.ducking = False

        self.over = False
        self.over_timer = 0.0
        self.started = False
        # Every new run starts in daylight, even if the last one ended at night.
        self.night = False

        self.obstacles: list[Obstacle] = []
        self.clouds: list[Cloud] = []
        self.spawn_timer = 0.9
        self.ground_offset = 0.0

        for sprite in self._cactus_sprites + self._bird_sprites:
            sprite.visible = False
            sprite.animation = None

        # Stagger the clouds across the sky so they are visible from frame one.
        for index, sprite in enumerate(self._cloud_sprites):
            sprite.visible = True
            sprite.position = (0, 0)
            self.clouds.append(
                Cloud(
                    -70.0 * index - 60.0,
                    40.0 + 30.0 * index,
                    sprite,
                    CLOUD_PARALLAX,
                )
            )

        self._free_cactus = list(self._cactus_sprites)
        self._free_bird = list(self._bird_sprites)

        self.dino.play_animation("run")
        self.dino.position = (DINO_X, int(self.dino_y))

        self.score_label.text = "0"
        self.best_label.text = f"HI {self.best}"
        self.banner.text = "CHROME DINO"
        self.banner.visible = True
        self.sub.text = "Press SPACE to start"
        self.sub.visible = True
        self._apply_palette()

    # -- palette ----------------------------------------------------------

    def _apply_palette(self) -> None:
        """Recolour every sprite and label for day or night.

        The art is rasterised pure white, so a single ``Sprite.tint`` swap flips
        the whole scene -- the same trick the original game uses.
        """
        fg = NIGHT_FG if self.night else DAY_FG
        self.background = NIGHT_BG if self.night else DAY_BG
        self.dino.tint = fg
        for sprite in self._cactus_sprites + self._bird_sprites + self._cloud_sprites:
            sprite.tint = fg
        for label in (self.score_label, self.best_label, self.hint_label,
                      self.banner, self.sub):
            label.color = fg

    # -- spawning ---------------------------------------------------------

    CACTUS_KINDS = ("small", "large", "triple")
    BIRD_BANDS = ("low", "mid", "high")

    def _spawn(self) -> None:
        if self.score >= BIRD_SCORE and random.random() < BIRD_CHANCE:
            self._spawn_bird()
        else:
            self._spawn_cactus()

    def _spawn_cactus(self) -> None:
        if not self._free_cactus:
            return
        kind = random.choices(self.CACTUS_KINDS, (0.5, 0.25, 0.25))[0]
        column = self.CACTUS_KINDS.index(kind)
        # Squash vertically so the same three sprites give a spread of heights.
        squash = CACTUS_SQUASH[kind]
        sprite = self._free_cactus.pop()
        sprite.visible = True
        sprite.animation = self.cactus_sheet.animation([(column, 0)], fps=1, loop=True)
        sprite.scale = (float(SCALE), float(SCALE * squash))
        self.obstacles.append(Obstacle(kind, W + 20, sprite, squash))

    def _spawn_bird(self) -> None:
        if not self._free_bird:
            return
        band = random.choices(self.BIRD_BANDS, (0.45, 0.35, 0.20))[0]
        sprite = self._free_bird.pop()
        sprite.visible = True
        sprite.animation = self.bird_sheet.animation(
            [(0, 0), (1, 0), (2, 0)], fps=12, loop=True
        )
        obstacle = Obstacle("bird", W + 20, sprite)
        obstacle.y_offset = float(BIRD_ALTITUDE[band] * SCALE)
        self.obstacles.append(obstacle)

    def _release(self, obstacle: Obstacle) -> None:
        obstacle.sprite.visible = False
        obstacle.sprite.animation = None
        if obstacle.kind == "bird":
            self._free_bird.append(obstacle.sprite)
        else:
            self._free_cactus.append(obstacle.sprite)
        self.obstacles.remove(obstacle)

    # -- audio ------------------------------------------------------------

    def _sfx(self, path: str) -> None:
        if self.audio is None:
            return
        try:
            self.audio.play_sound(path)
        except Exception:
            pass

    # -- input ------------------------------------------------------------

    JUMP_KEYS = ("space", "up", "w")
    DUCK_KEYS = ("down", "s")

    def _any_down(self, keys) -> bool:
        return any(self.input.is_key_down(key) for key in keys)

    def _jump_pressed(self) -> bool:
        """True on the frame any jump key goes down."""
        return any(self.input.is_key_pressed(key) for key in self.JUMP_KEYS)

    def _jump_held(self) -> bool:
        """True while any jump key is held (drives the variable jump height)."""
        return self._any_down(self.JUMP_KEYS)

    def _duck_held(self) -> bool:
        return self._any_down(self.DUCK_KEYS)

    # -- loop hooks -------------------------------------------------------

    def update(self, dt: float) -> None:
        if self.input.is_key_pressed("escape"):
            self.close()
            return

        if self.input.is_key_pressed("r"):
            self.reset()
            return

        if self.over:
            self._update_over(dt)
            return

        if not self.started:
            if self._jump_pressed():
                self.started = True
                self.banner.visible = False
                self.sub.visible = False
                self._start_jump()
            else:
                # Idle title screen: the clouds drift, the dino waits.
                for cloud in self.clouds:
                    cloud.update(dt, self.speed)
                self._update_dino_sprite(dt)
                return

        self.elapsed += dt
        self.speed = min(SPEED_MAX, SPEED_START + SPEED_RAMP * self.elapsed)
        self.distance += self.speed * dt
        self.score = int(self.distance / SCORE_DIVISOR)

        self._update_player(dt)
        self._update_world(dt)
        self._update_score()
        self._check_collisions()
        self._update_dino_sprite(dt)

    def _update_over(self, dt: float) -> None:
        self.over_timer += dt
        if self.over_timer < 0.45:
            return
        self.sub.text = "Press SPACE or R to run again"
        self.sub.visible = True
        if self._jump_pressed():
            self.reset()

    def _update_player(self, dt: float) -> None:
        was_ducking = self.ducking
        duck_held = self._duck_held()
        # Ducking only takes effect on the ground; in the air it fast-falls.
        self.ducking = duck_held and self.grounded
        if self.ducking and not was_ducking:
            self._sfx(self.duck_path)

        if self._jump_pressed() and self.grounded:
            self._start_jump()
        if self.vy < 0 and not self._jump_held():
            # Releasing early cuts the jump short, exactly like the original.
            self.vy += GRAVITY * JUMP_CUT * dt

        gravity = GRAVITY * (DUCK_FALL_BOOST if duck_held and not self.grounded else 1.0)
        self.vy = min(self.vy + gravity * dt, MAX_FALL)
        self.dino_y += self.vy * dt

        if self.dino_y >= GROUND_Y - DINO_H:
            self.dino_y = float(GROUND_Y - DINO_H)
            self.vy = 0.0
            self.grounded = True
        else:
            self.grounded = False

    def _start_jump(self) -> None:
        self.grounded = False
        self.vy = JUMP_VELOCITY
        self.ducking = False
        self._sfx(self.jump_path)

    def _update_world(self, dt: float) -> None:
        for cloud in self.clouds:
            cloud.update(dt, self.speed)

        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            self._spawn()
            # Tighter gaps the faster we go, plus a little variety.
            t = (self.speed - SPEED_START) / max(1.0, SPEED_MAX - SPEED_START)
            self.spawn_timer = random.uniform(
                GAP_MAX - t * (GAP_MAX - GAP_MIN), GAP_MAX + GAP_SLACK
            )

        for obstacle in list(self.obstacles):
            obstacle.update(dt, self.speed)
            if obstacle.offscreen:
                self._release(obstacle)

        self.ground_offset = (self.ground_offset + self.speed * dt) % GROUND_DASH

    def _update_dino_sprite(self, dt: float) -> None:
        """Pick the dino's pose from its state and push it to the sprite."""
        if self.over:
            self.dino.play_animation("crash")
        elif not self.started:
            self.dino.play_animation("stand")
        elif not self.grounded:
            self.dino.play_animation("jump")
        elif self.ducking:
            self.dino.play_animation("duck")
        else:
            self.dino.play_animation("run")
        self.dino.x = DINO_X
        self.dino.y = int(self.dino_y)
        self.dino.update(dt)

    def _update_score(self) -> None:
        self.score_label.text = str(self.score)
        if self.score > self.best:
            self.best = self.score
        self.best_label.text = f"HI {self.best}"

        want_night = (self.score // NIGHT_SCORE) % 2 == 1 and self.score > 0
        if want_night != self.night:
            self.night = want_night
            self._apply_palette()
            self._sfx(self.point_path)

    # -- collision --------------------------------------------------------

    def dino_rect(self) -> pydex_ge.Rect:
        """The dino's hitbox -- trimmed inside the art, and short when ducking.

        Margins are in art units so they scale with ``SCALE``.  Standing and
        jumping use the same box (the art is the same silhouette), while ducking
        uses the low, wide box that matches the crouching sprite.
        """
        if self.ducking:
            return pydex_ge.Rect(
                DINO_X + 2 * SCALE, GROUND_Y - DUCK_H, DINO_W - 4 * SCALE, DUCK_H
            )
        return pydex_ge.Rect(
            DINO_X + 4 * SCALE, self.dino_y + 4 * SCALE, DINO_W - 8 * SCALE, DINO_H - 5 * SCALE
        )

    def _check_collisions(self) -> None:
        if not self.started:
            return
        box = self.dino_rect()
        for obstacle in self.obstacles:
            # The highest pterodactyls fly clear over the dino's head.
            if obstacle.kind == "bird" and obstacle.y_offset >= BIRD_SAFE_ALTITUDE * SCALE:
                continue
            if box.overlaps(obstacle.rect):
                self._crash()
                return

    def _crash(self) -> None:
        self.over = True
        self.over_timer = 0.0
        self.vy = 0.0
        self.speed = 0.0
        self.banner.text = "GAME OVER"
        self.banner.visible = True
        self.sub.visible = False
        self._sfx(self.crash_path)

    # -- drawing ----------------------------------------------------------

    def draw(self) -> None:
        # Ground: a solid line plus the classic scrolling dash texture.
        fg = NIGHT_FG if self.night else DAY_FG
        self.renderer.draw.rect(0, GROUND_Y, W, 2, color=fg, filled=True)
        for x in range(-GROUND_DASH, W + GROUND_DASH, GROUND_DASH):
            self.renderer.draw.rect(
                int(x - self.ground_offset), GROUND_Y + 4, 22, 2, color=fg, filled=True
            )

        # NOTE: Sprite.draw() (not renderer.draw_sprite) is what honours the
        # active animation frame -- draw_sprite() would blit the whole sheet.
        for cloud in self.clouds:
            self.renderer.draw_sprite(cloud.sprite)

        for obstacle in self.obstacles:
            obstacle.sprite.y = int(obstacle.top)
            obstacle.sprite.draw(self.renderer)

        self.dino.draw(self.renderer)

        # Right-align the score and high score, Chrome-style.
        self.score_label.x = W - self.score_label.width - 24
        self.best_label.x = W - self.best_label.width - 24
        # Centre the hint along the bottom and the banner/sub down the middle.
        self.hint_label.x = (W - self.hint_label.width) // 2
        self.banner.x = (W - self.banner.width) // 2
        self.sub.x = (W - self.sub.width) // 2

        self.renderer.draw_label(self.score_label)
        self.renderer.draw_label(self.best_label)
        self.renderer.draw_label(self.hint_label)
        if self.banner.visible:
            self.renderer.draw_label(self.banner)
        if self.sub.visible:
            self.renderer.draw_label(self.sub)


def make_game() -> pydex_ge.Game:
    return DinoRunGame()


def main() -> None:
    print("PYDEX Chrome Dino - SPACE to jump, DOWN to duck, R to restart, ESC to quit.")
    make_game().run()
    print("DinoRunGame closed cleanly.")


if __name__ == "__main__":
    main()
