"""PYDEX field-test: Pac-Man (maze chase/arcade classic).

Exercises smooth tile-grid movement with a queued-turn input buffer and
instant 180-degree reversals, four chasing ghosts (Blinky/Pinky/Inky/Clyde)
with scatter/chase/frightened/eaten modes, BFS pathfinding for the eyes,
power pellets, scoring (10/50/200*2^n), three lives, win/game-over, and
fully procedural art + WAV sound effects (no asset files).

Controls
--------
* **Arrows** — steer Pac-Man (buffer a turn, or reverse instantly)
* **R** — restart the run
* **ESC** — quit

Run with:  python games/pacman.py
"""

from __future__ import annotations

import math
import os
import random
import tempfile

from _gen import blank, cell_rows, melody, solid_pixels, stamp, tone, wav_bytes

import pydex_ge

# -- maze -----------------------------------------------------------------

TILE = 20
COLS, ROWS = 26, 24
HUD_H = 46
W, H = COLS * TILE, HUD_H + ROWS * TILE
START_LIVES = 3

# Symmetric layout validated by flood fill (every pellet reachable).
#  '#' wall  '.' dot  'o' power pellet  ' ' open/tunnel  'P' spawn  'D' gate  'G' ghost house.
MAZE = [
    "##########################",
    "#.......o........o.......#",
    "#.####.....####.....####.#",
    "#.####.###.####.###.####.#",
    "#.####.###.####.###.####.#",
    "#.####.###......###.####.#",
    "#......###......###......#",
    "#......###......###......#",
    "#........................#",
    "#.###.###........###.###.#",
    "#.###.######DD######.###.#",
    "#.###.####GGGGGG####.###.#",
    "#........#GGGGGG#........#",
    "#....###.#G####G#.###....#",
    " ....###.########.###.... ",
    "..o.###...####...###.o..  ",
    "#.##..................##.#",
    "#.##.##............##.##.#",
    "#.##.##............##.##.#",
    "#....##......P.....##....#",
    "#....##............##....#",
    "#....##...######...##....#",
    "#.........######.........#",
    "##########################",
]

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
OPP = {d: (-d[0], -d[1]) for d in DIRS}
PLAYER_SPAWN = (13, 19)      # (col, row)
DOOR_CELLS = {(12, 10), (13, 10)}
EXIT_CELL = (9, 13)
HOME_CELLS = [(11, 10), (11, 15), (12, 14), (12, 11), (13, 10), (13, 15)]

GHOST_META = [
    ("blinky", (255, 40, 40), (COLS - 1, 0), 1.0),
    ("pinky", (255, 150, 190), (0, 0), 2.5),
    ("inky", (60, 220, 240), (COLS - 1, ROWS - 1), 4.0),
    ("clyde", (255, 170, 60), (0, ROWS - 1), 5.5),
]
PLAYER_SPEED = 4.05
GHOST_SPEED = 3.6
FRIGHT_SPEED = 2.3
EYES_SPEED = 6.4
HOUSE_SPEED = 2.2
MODE_SCHEDULE = [(7.0, "scatter"), (20.0, "chase"), (7.0, "scatter"),
                 (20.0, "chase"), (5.0, "scatter")]
FRIGHT_SECONDS = 7.0
READY_SECONDS = 1.5


def _cell(col: int, row: int) -> str:
    return MAZE[row][col % COLS]


def walkable(col: int, row: int) -> bool:
    return 0 <= row < ROWS and _cell(col, row) != "#"


def player_blocked(col: int, row: int) -> bool:
    return row < 0 or row >= ROWS or _cell(col, row) in "#DG"


def ghost_blocked(col: int, row: int, gate: bool) -> bool:
    if row < 0 or row >= ROWS:
        return True
    ch = _cell(col, row)
    if ch == "#":
        return True
    if ch == "D" and not gate:
        return True
    return False


def _dist2(c1: int, r1: int, c2: int, r2: int) -> int:
    return (c1 - c2) * (c1 - c2) + (r1 - r2) * (r1 - r2)


# -- pixel art (procedural, ~16px cells) ----------------------------------


def _cell_to_bytes(cell) -> bytes:
    return b"".join(cell_rows(cell))


def _ellipse(cell, cx, cy, rx, ry, color) -> None:
    for row in range(len(cell)):
        for col in range(len(cell[row])):
            dx = (col - cx) / rx
            dy = (row - cy) / ry
            if dx * dx + dy * dy <= 1.0:
                cell[row][col] = color


def _circle(cell, cx, cy, radius, color) -> None:
    for row in range(len(cell)):
        for col in range(len(cell[row])):
            dx = col - cx
            dy = row - cy
            if dx * dx + dy * dy <= radius * radius:
                cell[row][col] = color


def _in_wedge(dx, dy, d, half_angle) -> bool:
    if d == (0, 0) or (dx == 0 and dy == 0):
        return False
    cos = (dx * d[0] + dy * d[1]) / math.hypot(dx, dy)
    return cos >= math.cos(half_angle)


def pac_frame(size: int, mouth_open: bool, d: tuple[int, int]) -> bytes:
    body, outline = (255, 216, 0, 255), (205, 120, 0, 255)
    cell = blank(size)
    cx = cy = (size - 1) / 2.0
    r_out, r_in = size / 2 - 0.4, size / 2 - 1.1
    for row in range(size):
        for col in range(size):
            dx, dy = col - cx, row - cy
            d2 = dx * dx + dy * dy
            if d2 > r_out * r_out:
                continue
            if mouth_open and _in_wedge(dx, dy, d, 0.62):
                continue
            cell[row][col] = outline if d2 > r_in * r_in else body
    return _cell_to_bytes(cell)


def ghost_silhouette(color: tuple, frame: int):
    size = 16
    color = (*color[:3], 255) if len(color) < 4 else color
    edge = tuple(max(0, v - 60) for v in color[:3]) + (255,)
    cell = blank(size)
    _circle(cell, 7.5, 5.8, 7.5, edge)
    _circle(cell, 7.5, 5.8, 6.5, color)
    for row in range(6, size):
        for col in range(size):
            cell[row][col] = color
    for col in range(size):
        if (col + frame) % 3 == 0:
            cell[size - 1][col] = (0, 0, 0, 0)
    return cell


def _eyes(cell, d) -> None:
    for ex in (4.2, 9.8):
        _ellipse(cell, ex, 6.0, 2.3, 2.7, (255, 255, 255, 255))
    px, py = d[0] * 2, d[1] * 2
    for ox in (4.2, 9.8):
        _circle(cell, ox + px, 6.0 + py, 1.4, (60, 90, 220, 255))
        _circle(cell, ox + px, 6.0 + py, 0.8, (30, 30, 140, 255))


def ghost_normal_frame(color: tuple, d: tuple[int, int], frame: int) -> bytes:
    cell = ghost_silhouette(color, frame)
    _eyes(cell, d)
    return _cell_to_bytes(cell)


def ghost_fright_frame(flash: bool, frame: int) -> bytes:
    color = (205, 205, 250, 255) if flash else (60, 95, 230, 255)
    cell = ghost_silhouette(color, frame)
    stamp(cell, 3, 8, 3, 3, (255, 255, 255, 255))
    stamp(cell, 4, 12, 3, 2, (255, 255, 255, 255))
    stamp(cell, 10, 8, 3, 3, (255, 255, 255, 255))
    stamp(cell, 11, 12, 3, 2, (255, 255, 255, 255))
    return _cell_to_bytes(cell)


def eyes_frame(d: tuple[int, int]) -> bytes:
    cell = blank(16)
    _eyes(cell, d)
    return _cell_to_bytes(cell)


# -- pathfinding ----------------------------------------------------------


def bfs_next(start: tuple[int, int], target: tuple[int, int], gate: bool):
    """First step of a BFS toward ``target`` over the ghost graph."""
    if start == target:
        return (0, 0)
    prev = {start: None}
    frontier = [start]
    found = False
    while frontier and not found:
        nxt = []
        for (r, c) in frontier:
            for dr, dc in DIRS:
                nr, nc = r + dr, c + dc
                if (nr, nc) in prev or nr < 0 or nr >= ROWS:
                    continue
                if ghost_blocked(nc, nr, gate):
                    continue
                prev[(nr, nc)] = (r, c)
                if (nr, nc) == target:
                    found = True
                    break
                nxt.append((nr, nc))
            if found:
                break
        frontier = nxt
    if not found:
        return (0, 0)
    cur = target
    while prev[cur] != start:
        cur = prev[cur]
    return (cur[1] - start[1], cur[0] - start[0])


# -- entities -------------------------------------------------------------


class Walker:
    """Cell-to-cell smooth movement; turns happen only at cell centers."""

    def __init__(self, col: int, row: int, speed: float) -> None:
        self.col, self.row = col, row
        self.dir: tuple[int, int] = (0, 0)
        self.progress: float = 0.0
        self.speed: float = speed
        self.moving: bool = False
        self.visible: bool = True

    def center(self) -> tuple[float, float]:
        if self.moving:
            return (
                self.col + 0.5 + self.dir[0] * self.progress,
                self.row + 0.5 + self.dir[1] * self.progress,
            )
        return (self.col + 0.5, self.row + 0.5)

    def next_cell(self) -> tuple[int, int]:
        return ((self.col + self.dir[0]) % COLS, self.row + self.dir[1])

    def _check_next(self, d: tuple[int, int]) -> bool:
        nr = self.row + d[1]
        if nr < 0 or nr >= ROWS:
            return False
        return not self._blocked((self.col + d[0]) % COLS, nr)

    def _blocked(self, col: int, row: int) -> bool:
        raise NotImplementedError

    def _decide(self) -> tuple[int, int]:
        raise NotImplementedError

    def reverse_now(self) -> None:
        if not self.moving or self.dir == (0, 0):
            return
        self.col, self.row = self.next_cell()
        self.dir = OPP[self.dir]
        self.progress = 1.0 - self.progress

    def update(self, dt: float) -> None:
        guard = 0
        if self.moving:
            self.progress += self.speed * dt
        while self.moving and self.progress >= 1.0:
            self.col, self.row = self.next_cell()
            self.progress -= 1.0
            if not self._pick_next():
                self.moving = False
                self.progress = 0.0
            guard += 1
            if guard > 16:
                break
        if not self.moving and self._pick_next():
            self.moving = True

    def _pick_next(self) -> bool:
        d = self._decide()
        if d == (0, 0) or not self._check_next(d):
            keep = self.dir
            if keep == (0, 0) or not self._check_next(keep):
                self.dir = (0, 0)
                return False
            d = keep
        self.dir = d
        return True


class Player(Walker):
    def __init__(self, col: int, row: int) -> None:
        super().__init__(col, row, PLAYER_SPEED)
        self.pending: list[tuple[int, int]] = []

    def _blocked(self, col: int, row: int) -> bool:
        return player_blocked(col, row)

    def _decide(self) -> tuple[int, int]:
        while self.pending:
            intent = self.pending.pop(0)
            if intent != self.dir and intent != OPP.get(self.dir, (0, 0)):
                return intent
        return self.dir

    def queue_turn(self, d: tuple[int, int]) -> None:
        last = self.pending[-1] if self.pending else self.dir
        if d == last or d == OPP.get(last, (0, 0)):
            return
        if len(self.pending) < 2:
            self.pending.append(d)


class Ghost(Walker):
    HOUSE, ACTIVE, FRIGHTENED, EYES = "house", "active", "frightened", "eyes"

    def __init__(self, name, color, col, row, scatter, release_at, game) -> None:
        super().__init__(col, row, HOUSE_SPEED)
        self.name = name
        self.color = color
        self.scatter_target = scatter
        self.release_at = release_at
        self.game = game
        self.state = self.HOUSE
        self.lounge_index = random.randrange(len(HOME_CELLS))

    def _blocked(self, col: int, row: int) -> bool:
        gate = self.state in (self.HOUSE, self.EYES)
        return ghost_blocked(col, row, gate)

    def _decide(self) -> tuple[int, int]:
        if self.state == self.HOUSE:
            return self._house_step()
        if self.state == self.EYES:
            return self._eyes_step()
        if self.state == self.FRIGHTENED:
            options = [d for d in DIRS if self._check_next(d)]
            if len(options) > 1:
                back = OPP.get(self.dir, (0, 0))
                if back in options:
                    options.remove(back)
            return random.choice(options) if options else self.dir
        return self._chase_step()

    def _house_step(self) -> tuple[int, int]:
        if self._can_exit():
            return bfs_next((self.row, self.col), EXIT_CELL, True)
        target = HOME_CELLS[self.lounge_index]
        if target == (self.row, self.col):
            self.lounge_index = (self.lounge_index + 1) % len(HOME_CELLS)
            target = HOME_CELLS[self.lounge_index]
        step = bfs_next((self.row, self.col), target, True)
        return step

    def _can_exit(self) -> bool:
        if self.game.time < self.release_at:
            return False
        return not any(
            g is not self and ((g.row, g.col) == EXIT_CELL or (g.col, g.row) in DOOR_CELLS)
            for g in self.game.ghosts
        )

    def _eyes_step(self) -> tuple[int, int]:
        return bfs_next((self.row, self.col), (13, 10), True)

    def _target_cell(self) -> tuple[int, int]:
        if self.game.mode == "scatter":
            return self.scatter_target
        p = self.game.player
        if self.name == "blinky":
            return (p.col, p.row)
        last = p.dir or (1, 0)
        pr, pc = p.row + last[1] * 4, p.col + last[0] * 4
        pc %= COLS
        if self.name == "pinky":
            return (pc, pr)
        if self.name == "inky":
            blinky = self.game.ghosts[0]
            tr, tc = p.row + last[1] * 2, (p.col + last[0] * 2) % COLS
            tc = (2 * tc - blinky.col) % COLS or 0
            tr = max(0, min(ROWS - 1, 2 * tr - blinky.row))
            return (tc, tr)
        dr = abs(self.row - p.row) + abs(self.col - p.col)
        return (p.col, p.row) if dr > 8 else self.scatter_target

    def _chase_step(self) -> tuple[int, int]:
        tc, tr = self._target_cell()
        options = [d for d in DIRS if self._check_next(d) and d != OPP.get(self.dir)]
        if not options:
            options = [d for d in DIRS if self._check_next(d)]
        if not options:
            return self.dir
        return min(options, key=lambda d: _dist2(
            (self.col + d[0]) % COLS, self.row + d[1], tc, tr))

    def speed_for(self) -> float:
        if self.state == self.HOUSE:
            return HOUSE_SPEED
        if self.state == self.EYES:
            return EYES_SPEED
        if self.state == self.FRIGHTENED:
            return FRIGHT_SPEED
        return GHOST_SPEED * self.game.level_speed


# -- game -----------------------------------------------------------------


class PacmanGame(pydex_ge.Game):
    def __init__(self) -> None:
        super().__init__("PYDEX Pac-Man", W, H, fps=60)
        self.background = (6, 8, 22)
        self.font = pydex_ge.Font(size=18)
        self.small_font = pydex_ge.Font(size=13)
        self.big_font = pydex_ge.Font(size=26)

        self.score_label = pydex_ge.Label(
            "SCORE 0", font=self.font, position=(10, HUD_H // 2 - 14),
            color=(255, 210, 90),
        )
        self.level_label = pydex_ge.Label(
            "LV 1", font=self.font, position=(W - 74, HUD_H // 2 - 14),
            color=(90, 200, 255),
        )
        self.lives_label = pydex_ge.Label(
            "", font=self.font, position=(W // 2 - 60, HUD_H // 2 - 14),
            color=(120, 230, 150),
        )
        self.banner = pydex_ge.Label(
            "", font=self.big_font, position=(W // 2 - 70, H // 2 - 14),
            color=(255, 230, 120),
        )

        self._runtime_assets()
        self._build_sprites()
        self.reset()

    def _runtime_assets(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name

        def write_wav(name: str, samples) -> str:
            path = os.path.join(base, name)
            with open(path, "wb") as handle:
                handle.write(wav_bytes(samples))
            return path

        waka_up = tone(300, 0.05) + tone(520, 0.06)
        waka_down = tone(460, 0.05) + tone(280, 0.06)
        self.wav = {
            "waka": write_wav("waka.wav", waka_down),
            "waka2": write_wav("waka2.wav", waka_up),
            "power": write_wav("power.wav",
                tone(180, 0.08) + tone(300, 0.08) + tone(480, 0.14)),
            "eat": write_wav("eat.wav",
                melody([(880, 0.07), (990, 0.07), (1320, 0.14)])),
            "death": write_wav("death.wav",
                sum((tone(f, 0.09, decay=False) for f in
                     range(900, 100, -70)), start=[])),
            "win": write_wav("win.wav",
                melody([(523, 0.14), (659, 0.14), (784, 0.14), (1046, 0.30)])),
        }
        try:
            self.audio = pydex_ge.Audio()
        except Exception:  # no audio backend (e.g. headless null backend)
            self.audio = None
        self._waka_toggle = False
        self._last_waka = 0.0

    def _sfx(self, name: str) -> None:
        if self.audio is not None:
            self.audio.play_sound(self.wav[name])

    # -- sprites -----------------------------------------------------------

    def _build_sprites(self) -> None:
        def spr(data: bytes, size: int) -> pydex_ge.Sprite:
            return pydex_ge.Sprite.from_pixels(size, size, data)

        self.pac_sprites: dict[tuple[int, int, bool], pydex_ge.Sprite] = {}
        for d in DIRS:
            for mouth in (False, True):
                self.pac_sprites[(d[0], d[1], mouth)] = spr(
                    pac_frame(16, mouth, d), 16)

        self.ghost_sprites: dict[str, dict[tuple[int, int, int], pydex_ge.Sprite]] = {}
        for name, color, _, _ in GHOST_META:
            self.ghost_sprites[name] = {
                (d[0], d[1], f): spr(ghost_normal_frame(color, d, f), 16)
                for d in DIRS for f in (0, 1)
            }

        self.fright_sprites = {
            (flash, f): spr(ghost_fright_frame(flash, f), 16)
            for flash in (False, True) for f in (0, 1)
        }
        self.eyes_sprites = {
            (d[0], d[1]): spr(eyes_frame(d), 16) for d in DIRS
        }
        self.heart_sprite = spr(
            _cell_to_bytes(_pac_heart()), 16)

        self.dot_sprite = spr(solid_pixels(5, 5, (255, 205, 120)), 5)
        self.pellet_sprite = spr(
            _cell_to_bytes(_pellet_cell(16)), 16)
        self.pellet_glow = spr(
            _cell_to_bytes(_pellet_cell(16, True)), 16)

    # -- run lifecycle -----------------------------------------------------

    def reset(self) -> None:
        self.score = 0
        self.lives = START_LIVES
        self.level = 1
        self.level_speed = 1.0
        self._start_level()
        self.update_labels()

    def _start_level(self) -> None:
        self.dots: set[tuple[int, int]] = set()
        self.pellets: set[tuple[int, int]] = set()
        for r in range(ROWS):
            for c in range(COLS):
                ch = _cell(c, r)
                if ch == ".":
                    self.dots.add((c, r))
                elif ch == "o":
                    self.pellets.add((c, r))
                elif ch == "P":
                    self.dots.discard((c, r))
        self.player = Player(*PLAYER_SPAWN)
        self.player.pending.append((-1, 0))
        self.player.dir = (-1, 0)
        self.ghosts: list[Ghost] = []
        spawns = [(13, 11), (12, 11), (13, 12), (12, 12)]
        for (name, color, scatter, release), (gc, gr) in zip(GHOST_META, spawns):
            self.ghosts.append(Ghost(name, color, gc, gr, scatter, release, self))
        self.mode = "scatter"
        self.mode_index = 0
        self.mode_timer = 0.0
        self.fright_timer = 0.0
        self.time = 0.0
        self.anim_time = 0.0
        self.phase = "ready"
        self.phase_timer = READY_SECONDS
        self.eaten_chain = 0
        self.banner.visible = True
        self.banner.text = "READY!"

    def update_labels(self) -> None:
        self.score_label.text = f"SCORE {self.score}"
        self.level_label.text = f"LV {self.level}"
        self.lives_label.text = "LIVES " + "P" * self.lives

    # -- frame loop --------------------------------------------------------

    def update(self, dt: float) -> None:
        self.anim_time += dt
        if self.input.is_key_pressed("escape"):
            self.close()
            return
        if self.input.is_key_pressed("r"):
            self.reset()
            return
        if self.phase == "game_over":
            return

        self._read_input()

        if self.phase == "ready":
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                self.phase = "play"
                self.banner.visible = False
            return

        if self.phase == "dying":
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                if self.lives > 0:
                    self._start_level()
                else:
                    self.phase = "game_over"
                    self.banner.visible = True
                    self.banner.text = "GAME OVER"
            return

        if self.phase == "won":
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                self.level += 1
                self.level_speed = min(1.35, 1.0 + 0.07 * (self.level - 1))
                self._start_level()
            return

        self.time += dt
        self.player.speed = PLAYER_SPEED * self.level_speed
        self.player.update(dt)
        for ghost in self.ghosts:
            ghost.speed = ghost.speed_for()
            ghost.update(dt)
            if ghost.state == Ghost.EYES and (ghost.col, ghost.row) in DOOR_CELLS:
                ghost.state = Ghost.HOUSE
                ghost.col, ghost.row = 13, 12
                ghost.dir = (0, 0)
                ghost.progress = 0.0
                ghost.moving = False
                ghost.release_at = self.time + 3.0
            elif ghost.state == Ghost.HOUSE and (ghost.row, ghost.col) == EXIT_CELL:
                ghost.state = Ghost.ACTIVE

        self._update_mode(dt)
        self._eat_cell()
        self._ghost_contact()

        if not self.dots and not self.pellets:
            self._win_level()

    def _read_input(self) -> None:
        pressed = {
            "up": (0, -1), "down": (0, 1),
            "left": (-1, 0), "right": (1, 0),
        }
        for key, iv in pressed.items():
            if self.input.is_key_pressed(key):
                if iv == OPP.get(self.player.dir, (0, 0)) and self.player.moving:
                    self.player.pending = []
                    self.player.reverse_now()
                else:
                    self.player.queue_turn(iv)

    def _update_mode(self, dt: float) -> None:
        if self.fright_timer > 0:
            self.fright_timer -= dt
            if self.fright_timer <= 0:
                for ghost in self.ghosts:
                    if ghost.state == Ghost.FRIGHTENED:
                        ghost.state = Ghost.ACTIVE
                        ghost.reverse_now()
                self.eaten_chain = 0
            return
        if self.mode_index >= len(MODE_SCHEDULE):
            return
        self.mode_timer += dt
        while self.mode_index < len(MODE_SCHEDULE) and self.mode_timer >= MODE_SCHEDULE[self.mode_index][0]:
            self.mode_timer -= MODE_SCHEDULE[self.mode_index][0]
            self.mode_index += 1
        new_mode = MODE_SCHEDULE[self.mode_index][1] if self.mode_index < len(MODE_SCHEDULE) else "chase"
        if new_mode != self.mode:
            self.mode = new_mode
            for ghost in self.ghosts:
                if ghost.state == Ghost.ACTIVE:
                    ghost.reverse_now()

    def _eat_cell(self) -> None:
        cx, cy = self.player.center()
        col = round(cx - 0.5) % COLS
        row = round(cy - 0.5)
        if not walkable(col, row):
            return
        if (col, row) in self.pellets:
            if self.audio is not None:
                self._sfx("power")
            self.pellets.discard((col, row))
            self.score += 50
            self.eaten_chain = 0
            for ghost in self.ghosts:
                if ghost.state == Ghost.ACTIVE:
                    ghost.state = Ghost.FRIGHTENED
                elif ghost.state == Ghost.HOUSE:
                    ghost.release_at = 0.0
            self.fright_timer = FRIGHT_SECONDS
            self.update_labels()
        elif (col, row) in self.dots:
            now = self.anim_time
            if now - self._last_waka > 0.08:
                self._sfx("waka" if not self._waka_toggle else "waka2")
                self._waka_toggle = not self._waka_toggle
                self._last_waka = now
            self.dots.discard((col, row))
            self.score += 10
            self.update_labels()

    def _ghost_contact(self) -> None:
        if self.phase != "play":
            return
        px, py = self.player.center()
        for ghost in self.ghosts:
            if ghost.state == Ghost.HOUSE:
                continue
            gx, gy = ghost.center()
            if (gx - px) ** 2 + (gy - py) ** 2 < 0.25:
                if ghost.state == Ghost.FRIGHTENED:
                    value = 200 * (2 ** self.eaten_chain)
                    self.eaten_chain += 1
                    self.score += value
                    ghost.state = Ghost.EYES
                    ghost.speed = EYES_SPEED
                    self._sfx("eat")
                    self.update_labels()
                elif ghost.state != Ghost.EYES:
                    self._player_dies()
                    return

    def _player_dies(self) -> None:
        self.lives -= 1
        if self.lives <= 0:
            self.lives = 0
        self.phase = "dying"
        self.phase_timer = 1.6
        self.banner.visible = True
        self.banner.text = "" if self.lives > 0 else "GAME OVER"
        self._sfx("death")
        self.player.visible = False
        self.update_labels()

    def _win_level(self) -> None:
        self.phase = "won"
        self.phase_timer = 2.2
        self.banner.visible = True
        self.banner.text = "LEVEL CLEAR!"
        self.score += 1000
        self._sfx("win")
        self.update_labels()

    # -- drawing -----------------------------------------------------------

    def draw(self) -> None:
        self._draw_maze()
        self._draw_food()
        self._draw_entities()
        self.renderer.draw_label(self.score_label)
        self.renderer.draw_label(self.level_label)
        self.renderer.draw_label(self.lives_label)
        if self.banner.visible:
            self.banner.position = (W // 2 - len(self.banner.text) * 9, H // 2 - 14)
            self.renderer.draw_label(self.banner)

    def _draw_maze(self) -> None:
        for r in range(ROWS):
            for c in range(COLS):
                ch = _cell(c, r)
                if ch != "#":
                    continue
                x = c * TILE
                y = HUD_H + r * TILE
                self.renderer.draw.rect(x, y, TILE, TILE, (28, 44, 112), filled=True)
                self.renderer.draw.rect(x + 3, y + 3, TILE - 6, TILE - 6, (58, 92, 190), filled=True)

    def _draw_food(self) -> None:
        for (c, r) in self.dots:
            self.dot_sprite.position = (c * TILE + 7, HUD_H + r * TILE + 8)
            self.renderer.draw_sprite(self.dot_sprite)
        glow = int(self.anim_time * 3.0) % 2 == 0
        for (c, r) in self.pellets:
            sprite = self.pellet_glow if glow else self.pellet_sprite
            sprite.position = (c * TILE + 2, HUD_H + r * TILE + 2)
            self.renderer.draw_sprite(sprite)

    def _draw_entities(self) -> None:
        if self.phase == "dying":
            self._draw_death_pop()
        else:
            mouth = self.phase == "play" and int(self.anim_time * 7.0) % 2 == 0
            self._draw_player(mouth)
        for ghost in self.ghosts:
            self._draw_ghost(ghost)

    def _draw_death_pop(self) -> None:
        cx, cy = self.player.center()
        x, y = int(cx * TILE), int(HUD_H + cy * TILE)
        sprite = self.pac_sprites[(-1, 0, True)]
        sprite.position = (x - 8, y - 8)
        self.renderer.draw_sprite(sprite)
        t = 1.0 - max(0.0, self.phase_timer) / 1.6
        r = 4 + t * 22
        self.renderer.draw.circle(x, y, int(r), (255, 255, 255), filled=False)
        self.renderer.draw.circle(x, y, max(1, int(r * 0.65)), (255, 235, 150), filled=False)

    def _draw_player(self, mouth: bool) -> None:
        d = self.player.dir if self.player.dir != (0, 0) else (-1, 0)
        sprite = self.pac_sprites[(d[0], d[1], mouth)]
        cx, cy = self.player.center()
        sprite.position = (int(cx * TILE - 8), int(HUD_H + cy * TILE - 8))
        self.renderer.draw_sprite(sprite)

    def _draw_ghost(self, ghost: Ghost) -> None:
        gx, gy = ghost.center()
        frame = int(self.anim_time * 6.0) % 2
        if ghost.state == Ghost.HOUSE and self.fright_timer > 0:
            flash = self.fright_timer < 2.0 and int(self.anim_time * 6.0) % 2 == 0
            sprite = self.fright_sprites[(flash, frame)]
        elif ghost.state in (Ghost.ACTIVE, Ghost.HOUSE):
            d = ghost.dir if ghost.dir != (0, 0) else (0, 1)
            sprite = self.ghost_sprites[ghost.name][(d[0], d[1], frame)]
        elif ghost.state == Ghost.FRIGHTENED:
            flash = self.fright_timer < 2.0 and int(self.anim_time * 6.0) % 2 == 0
            sprite = self.fright_sprites[(flash, frame)]
        else:
            d = ghost.dir if ghost.dir != (0, 0) else (0, 0)
            sprite = self.eyes_sprites[(d[0], d[1])]
        sprite.position = (int(gx * TILE - 8), int(HUD_H + gy * TILE - 8))
        self.renderer.draw_sprite(sprite)


# -- little pixel helpers -------------------------------------------------


def _pellet_cell(size: int, bright: bool = False):
    cell = blank(size)
    core = (255, 255, 255, 255) if bright else (255, 230, 90, 255)
    mid = (255, 190, 70, 255) if bright else (255, 150, 30, 255)
    glow = (255, 220, 120, 255) if bright else (255, 205, 120, 255)
    _circle(cell, (size - 1) / 2, (size - 1) / 2, size / 2 - 0.5, glow)
    _circle(cell, (size - 1) / 2, (size - 1) / 2, size / 2 - 2, mid)
    _circle(cell, (size - 1) / 2, (size - 1) / 2, size / 2 - 4, core)
    return cell


def _pac_heart():
    cell = blank(16)
    _circle(cell, 5.0, 6.0, 4.0, (255, 216, 0, 255))
    _circle(cell, 11.0, 6.0, 4.0, (255, 216, 0, 255))
    for row in range(8, 15):
        for col in range(3, 13):
            if len(cell) > row and len(cell[row]) > col:
                cell[row][col] = (255, 216, 0, 255)
    return cell


def make_game() -> pydex_ge.Game:
    return PacmanGame()


def main() -> None:
    print("PYDEX Pac-Man - arrows, power pellets, eat the ghosts.")
    make_game().run()
    print("PacmanGame closed cleanly.")


if __name__ == "__main__":
    main()