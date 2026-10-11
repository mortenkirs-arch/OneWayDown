"""Base Camp: the shaft has come down at the bottom of an expedition, and the crew climb out to the camp.

The camp is a cavern at the bottom of the shaft, laid out like a mine layer - dark stone, trodden paths, glowing
mushrooms, an underground stream with a plank bridge - with five tents round a campfire, one per upgrade branch. Every tent starts plain white; its first upgrade is a hire: a character who joins every expedition
from then on (camp.HIRES). Hire one per visit, and the tent takes on its owner's colours. Then set off: a fresh
expedition starts beneath the camp.
"""
import math
import random
import time

import pygame

from ..camp import EXPEDITION_DEPTH, HIRES, ITEMS, TENTS, hireable, open_items
from ..config import GOLD, GOOD, H, MUTED, TEXT, W
from ..effects import Particle
from ..icons import draw_icon, draw_padlock
from ..iso import draw_cube, iso, origin_at, point_in_poly
from ..miners import CAMP_LOOKS, Miner
from ..sprites import (draw_banner, draw_banner_fringe, draw_desk_wing, draw_glaze_pots, draw_heirloom_pick,
                       draw_potters_wheel, draw_powder_keg, draw_brazier, draw_clay_pit, draw_collar_post, draw_divining_rod,
                       draw_tax_strongbox, draw_kiln, draw_ledger_desk, draw_lightning_rod, draw_miner,
                       draw_gear_addon, draw_pet_chest, draw_pocket_watch, draw_target_dummy, draw_toolkit)
from ..ui import Button, draw_glow, draw_panel, draw_text, wrap_text
from ..upgrades import BRANCHES
from ..util import fmt, shade
from .base import Scene

PANEL_RECT = pygame.Rect(W - 400, 104, 376, H - 196)
BOARD = 10                                  # the camp board is BOARD x BOARD tiles, like a mine layer
ORIGIN = (PANEL_RECT.x // 2 + 6, 214)       # where the board's back corner sits on screen
FIRE = (5.2, 5.0)
# an underground stream across the front corner (grid points, upstream first), this wide either side of its middle
RIVER = [(10.0, 5.6), (9.0, 6.4), (8.5, 7.5), (7.5, 8.2), (6.6, 8.9), (6.1, 10.0)]
RIVER_HALF = 0.5
BRIDGE = (7.95, 7.8)                        # a plank bridge over it, here
# giant glowing mushrooms round the edges of the cavern: (x, y, size, glow)
SHROOMS = [(0.5, 0.5, 1.3, "teal"), (1.5, 0.35, 0.8, "violet"), (0.4, 1.6, 0.9, "teal"), (3.9, 0.4, 1.1, "amber"),
           (8.4, 0.5, 1.0, "violet"), (9.5, 0.6, 1.4, "teal"), (9.55, 1.9, 0.7, "amber"), (0.4, 4.3, 1.0, "violet"),
           (0.45, 9.3, 1.2, "teal"), (0.4, 8.2, 0.8, "amber"), (3.6, 9.55, 0.9, "violet"), (9.6, 3.0, 0.8, "teal")]
SPROUTS = [(2.9, 4.4), (3.3, 6.9), (6.8, 3.3), (7.2, 5.9), (1.2, 3.6), (5.6, 2.9), (9.2, 5.0), (2.6, 8.7)]
STALAGMITES = [(2.8, 0.35, 1.0), (6.1, 0.4, 1.3), (0.35, 5.6, 0.9), (0.4, 7.1, 1.2)]
GLOWS = {"teal": ((90, 230, 210), (36, 120, 118)), "violet": ((190, 130, 255), (92, 60, 142)),
         "amber": ((255, 190, 90), (140, 90, 40))}
ITEM_SCALE = 1.6                            # the camp's items are drawn this much bigger than on the dig
ITEM_SIZE = {"ledger": 0.72, "rounding": 0.72, "brazier": 0.55, "explosive": 0.55}   # (any drawn smaller than that)
FITTED = {"gears": "toolkit", "rounding": "ledger", "pup": "chompers", "heirloom": "divining",   # items that are
          "fringe": "banner", "explosive": "brazier", "glaze": "kiln", "wheel": "claypit"}               # an upgrade to another:
                                            # drawn as part of it, once yours
HANGOUT = {"combat": (7.0, 7.45)}           # where a tent's owner potters about, if not by its door (Wren: the bridge)
PERCHED = {"rod", "watch"}                  # items up on the Tools Tent's ridge (at their `pos` along it), not the
HANGING = {"watch"}                         # ground - the Pocket Watch hanging off it, at the end over the door
RANGE_SHROOM = (3.6, 9.55)                  # the Target Dummy's range: the mushroom it clears away...
RANGE_BALES = [(1.72, 9.12, 0), (1.72, 9.72, 0), (1.72, 9.42, 1), (3.55, 9.5, 0)]   # ...and its straw bales: (x, y,
BALE_HALF, BALE_HIGH = (0.2, 0.28), 0.42    # stacked); the last, out front, a second target. A bale's size (tiles, blocks)
TENT_HALF = (0.8, 0.62)                     # a tent's footprint (half its length and width, in tiles)...
TENT_HIGH = 1.45                            # ...and the height of its ridge (in block heights)
PLAIN = (238, 234, 224)                     # an unclaimed tent's bare canvas
STYLES = {   # a tent once its hire has moved in: canvas, trim, the emblem on its side
    "crew":    dict(canvas=(64, 110, 196), trim=(250, 205, 70), icon="pick"),
    "tools":   dict(canvas=(150, 92, 56), trim=(255, 150, 60), icon="anvil"),
    "hands":   dict(canvas=(150, 90, 200), trim=(235, 210, 255), icon="hand"),
    "fortune": dict(canvas=(64, 140, 84), trim=(240, 200, 70), icon="coins", stripe=(232, 224, 190)),
    "combat":  dict(canvas=(182, 58, 52), trim=(240, 240, 235), icon="target"),
}
LORE = "The Void Maw's death-throes brought the shaft down - but the crew scrambled clear, into the cavern where you " \
       "made camp. One thing to take per visit."


VIEW_LORE = "The cavern where you made camp, at the bottom of the shaft. Your people go down with every " \
            "expedition; the tents still empty can take on a hire the next time the shaft comes down."
LOCKED_LORE = "Somewhere at the bottom of the shaft, past everything the deep can throw at you, there's a cavern big " \
              "enough to make camp in. Beat The Void Maw at 100m and you'll find it."


def item_spot(key):
    """Where an item is: (x, y, z) on the board, and its place in the drawing order (one up on a tent comes after
    the tent)."""
    x, y = ITEMS[key]["pos"]
    if key in PERCHED:
        cx, cy = TENTS[ITEMS[key]["tent"]]["pos"]
        return x, y, 1.0 + TENT_HIGH, cx + cy + 0.45
    return x, y, 1.0, x + y


def item_feet(key):
    """Where an item's picture is pinned, in its 80x80 art: its feet (or, hanging, the top of its chain)."""
    return (40, 12) if key in HANGING else (40, 66)


def hangout(tent):
    """Where a tent's owner potters about: by its door, or (HANGOUT) somewhere of their own."""
    return HANGOUT.get(tent) or door(tent)


def door(tent):
    """Where a tent's owner hangs about: just out from its door (the end facing the fire)."""
    cx, cy = TENTS[tent]["pos"]
    return cx + TENT_HALF[0] + 0.35, cy + 0.15


def smooth(points, steps=8):
    """A Catmull-Rom curve through `points` (so the stream bends instead of zig-zagging)."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(steps):
            q = k / steps
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * q + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * q * q
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * q ** 3) for j in (0, 1)))
    out.append(points[-1])
    return out


STREAM = smooth(RIVER)


def banks(width):
    """The stream's two edges (grid points), `width` either side of its middle, gently uneven."""
    left, right = [], []
    for i, (x, y) in enumerate(STREAM):
        ax, ay = STREAM[max(0, i - 1)]
        bx, by = STREAM[min(len(STREAM) - 1, i + 1)]
        n = math.hypot(bx - ax, by - ay) or 1.0
        nx, ny = -(by - ay) / n, (bx - ax) / n
        wob = width * (1 + 0.12 * math.sin(i * 1.7))
        inside = lambda v: min(float(BOARD), max(0.0, v))   # (kept to the board)
        left.append((inside(x + nx * wob), inside(y + ny * wob)))
        right.append((inside(x - nx * wob), inside(y - ny * wob)))
    return left, right


RIVER_CELLS = {(x, y) for x in range(BOARD) for y in range(BOARD)
               if min(math.hypot(x + 0.5 - px, y + 0.5 - py) for px, py in STREAM) < RIVER_HALF + 0.45}


def path_cells():
    """Dirt tracks worn from the campfire to each tent's door."""
    cells = set()
    for tent in TENTS:
        (x0, y0), (x1, y1) = FIRE, door(tent)
        for k in range(40):
            q = k / 39
            cells.add((int(x0 + (x1 - x0) * q), int(y0 + (y1 - y0) * q)))
    return cells - RIVER_CELLS


PATHS = path_cells()


class CampScene(Scene):
    simulate = False   # the dig waits while you're at camp

    def __init__(self, game):
        super().__init__(game)
        self.selected = "crew"
        self.hired = None          # who's been taken on this visit (one per visit)
        self.people = {}           # tent -> the character living there (a Miner, for drawing)
        self.particles = []
        self.tent_polys = {}       # tent -> its faces on screen (for the mouse)
        self.backdrop = None
        self.halos = {}            # (radius, colour, strength) -> a glow, cached
        p = PANEL_RECT
        self.hire_button = Button((p.x + 20, p.bottom - 70, p.w - 40, 52), "", self.choose, size=28,
                                  color=(60, 130, 80))
        self.go_button = Button((p.x, p.bottom + 14, p.w, 56), "", self.set_off, size=28, color=(70, 100, 160))
        self.dev_button = Button((p.x - 92, 22, 72, 34), "Dev", self.toggle_dev, size=20, color=(70, 66, 84))
        self.dev = False           # Dev: show every hire and item the camp can have (just to look at - nothing's taken)
        self.dev_people = {}       # (the hires you haven't got, standing in for the Dev view)
        self.mode = "visit"        # visit: the shaft just came down (hire, then set off) | view: a look round from the
                                   # dig | locked: you've never made camp - a glimpse of what's waiting at 100m

    def enter(self):
        w = self.world
        self.mode = "visit" if w.camp_ready else ("view" if w.expedition else "locked")
        self.hired = w.visit_hire if self.mode == "visit" else None   # (hired already, then the game was closed?)
        open_tents = [k for k, t in TENTS.items() if t["hire"] in hireable(w.camp)]
        items = open_items(w.camp, w.camp_items)
        self.selected = open_tents[0] if open_tents else (items[0] if items and self.mode == "visit" else "crew")
        self.people = {}
        for hire in w.camp:   # whoever's already with you, as they are in the crew
            them = next((m for m in w.miners if m.role == hire), None)
            self.move_in(HIRES[hire]["tent"], hire, them)
        self.particles = []

    def move_in(self, tent, hire, them=None):
        """A tent's character moves in, for the camp board (a copy of the crew member, or a fresh face)."""
        m = self.make_person(tent, hire, them)
        self.people[tent] = m
        return m

    def make_person(self, tent, hire, them=None):
        """A tent's character, standing at its door."""
        m = Miner(role=hire)
        m.apply_look(CAMP_LOOKS[hire])
        if them:
            m.apply_saved(them.to_dict())
        m.x, m.y = hangout(tent)
        m.draw_z, m.hp, m.max_hp, m.anim = 1.0, 1.0, 1.0, 0.0
        m.seed = random.uniform(0, 10)
        return m

    def toggle_dev(self):
        """Dev: show every hire in their tent and every item on the board, or just what you've really got."""
        self.dev = not self.dev
        self.dev_people = {k: self.make_person(k, t["hire"]) for k, t in TENTS.items() if t["hire"]} if self.dev else {}
        self.dev_button.color = (200, 120, 50) if self.dev else (70, 66, 84)

    def shown_people(self):
        """The characters on the board: the camp's people (and in the Dev view, everyone it could have)."""
        return {**self.dev_people, **self.people} if self.dev else self.people

    # ----- actions --------------------------------------------------------------------------------------------
    def choosing(self):
        """Still to make this visit's pick (a hire, or one of the items)?"""
        w = self.world
        return self.mode == "visit" and not self.hired and bool(hireable(w.camp) or open_items(w.camp, w.camp_items))

    def choose(self):
        if self.selected in ITEMS:
            self.take_item()
        else:
            self.hire()

    def take_item(self):
        key, w = self.selected, self.world
        if self.mode != "visit" or self.hired or key not in open_items(w.camp, w.camp_items):
            return
        self.hired = key
        w.take_camp_item(key)
        self.game.save()   # (yours for good: closing the game before setting off can't lose it)
        with origin_at(ORIGIN):
            px, py = iso(*item_spot(key)[:3])
        if key in HANGING:
            py += 50
        color = BRANCHES[ITEMS[key]["tent"]]["color"]
        for _ in range(40):   # a puff as it becomes real
            self.particles.append(Particle(px, py - 14, random.choice([GOLD, (255, 255, 255), color]), big=True))
        self.game.toast = (f"The {ITEMS[key]['name']} is yours - for good!", 3.5)

    def hire(self):
        tent = TENTS[self.selected]
        if self.mode != "visit" or self.hired or tent["hire"] not in hireable(self.world.camp):
            return
        self.hired = tent["hire"]
        self.world.hire_at_camp(self.hired)
        self.game.save()   # (theirs for good: closing the game before setting off can't lose them)
        m = self.move_in(self.selected, self.hired)
        with origin_at(ORIGIN):
            px, py = iso(m.x, m.y, 1.0)
        for _ in range(40):   # a puff as they move in (and the tent changes colours)
            self.particles.append(Particle(px, py - 20, random.choice([GOLD, (255, 255, 255),
                                                                       BRANCHES[self.selected]["color"]]), big=True))
        self.game.toast = (f"{m.name} the {HIRES[self.hired]['title']} joins you - for good!", 3.5)

    def set_off(self):
        if self.mode != "visit":   # (just looking round: back to the dig)
            self.game.switch("play")
            return
        w = self.world
        self.game.world = type(w).next_expedition(w)
        self.game.save()
        self.game.bg_key, self.game.bg_prev, self.game.bg_fade = "topsoil", None, 1.0
        self.game.switch("play")

    def handle(self, event):
        if self.hire_button.handle(event) or self.go_button.handle(event):
            return
        if self.mode != "locked" and self.dev_button.handle(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pick = self.item_under(event.pos) or self.tent_under(event.pos)
            if pick:
                self.selected = pick
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.set_off()
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_b) and self.mode != "visit":
            self.game.switch("play")

    def shown_items(self):
        """{item: faded?} - the camp's items on the board: yours, solid; while you're choosing, the ones you could
        take, faded (gone again once you've chosen)."""
        w = self.world
        if self.dev:   # (everything, as if it were yours)
            return {k: False for k in ITEMS}
        shown = {k: False for k in w.camp_items}
        if self.choosing():
            shown.update({k: True for k in open_items(w.camp, w.camp_items)})
        return shown

    def item_under(self, pos):
        shown = self.shown_items()
        for key in sorted(shown, key=lambda k: not shown[k]):   # (one you could take first: it may be fitted to yours)
            with origin_at(ORIGIN):
                x, y = iso(*item_spot(key)[:3])
            top, bottom = (y - 4, y + 56) if key in HANGING else (y - 70, y + 12)
            if abs(pos[0] - x) < 32 and top < pos[1] < bottom:
                return key
        return None

    def has_range(self):
        """The Target Dummy's range is up (it's yours - or it's the Dev view)."""
        return self.dev or "dummy" in self.world.camp_items

    def shrooms(self):
        """The cavern's mushrooms (less the one the dummy's range was built over)."""
        return [m for m in SHROOMS if not (self.has_range() and m[:2] == RANGE_SHROOM)]

    def tent_under(self, pos):
        for tent, polys in self.tent_polys.items():
            if any(point_in_poly(pos, poly) for poly in polys):
                return tent
        for tent, m in self.shown_people().items():   # (or the character standing outside it)
            with origin_at(ORIGIN):
                x, y = iso(m.x, m.y, 1.0)
            if abs(pos[0] - x) < 14 and y - 44 < pos[1] < y + 4:
                return tent
        return None

    # ----- the camp going about its evening ---------------------------------------------------------------------
    def update(self, dt):
        t = time.time()
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        with origin_at(ORIGIN):
            fx, fy = iso(FIRE[0], FIRE[1], 1.0)
            if random.random() < dt * 14:   # sparks off the campfire
                self.particles.append(Particle(fx + random.uniform(-8, 8), fy - 14,
                                               random.choice([(255, 200, 90), (255, 140, 50), (255, 240, 180)])))
            if random.random() < dt * 6:   # glowing spores drifting off the mushrooms
                x, y, size, glow = random.choice(self.shrooms())
                px, py = iso(x, y, 1.0)
                self.particles.append(Particle(px + random.uniform(-14, 14) * size, py - 30 * size, GLOWS[glow][0]))
            if "tools" in self.shown_people() and random.random() < dt * 4:   # the forge's chimney smoking
                cx, cy = TENTS["tools"]["pos"]
                sx, sy = iso(cx - 0.3, cy - 0.2, 1.0 + TENT_HIGH + 0.45)
                self.particles.append(Particle(sx, sy, random.choice([(120, 116, 120), (90, 88, 94)])))
        for tent, m in self.shown_people().items():   # pottering about outside their tent
            hx, hy = hangout(tent)
            k = m.seed
            nx, ny = hx + 0.35 * math.sin(t * 0.5 + k), hy + 0.45 * math.sin(t * 0.31 + k * 2)
            if (nx - m.x) - (ny - m.y) > 0.002:
                m.facing = 1
            elif (nx - m.x) - (ny - m.y) < -0.002:
                m.facing = -1
            m.x, m.y = nx, ny
            busy = math.sin(t * 0.8 + k) > 0.55   # every so often: at their trade
            m.anim = (1.0 if (t * 4) % 1 < 0.5 else 0.2) if busy and m.role in ("engineer", "taxman") else 0.0
            if m.role == "archer":
                m.anim = max(0.0, math.sin(t * 1.3 + k)) if busy else 0.0
            m.task = "forging" if busy and m.role == "engineer" else "idle"
            if m.role == "claygolem":   # (out of the Kiln, and glazed, as on the dig)
                m.fired = "kiln" in self.world.camp_items or self.dev
                m.glazed = "glaze" in self.world.camp_items or self.dev
            if m.role == "claygolem":   # (practising its slam on the turf, fists up and down)
                m.task, m.anim = ("leaping", (t * 0.7) % 1) if busy else ("idle", 0.0)

    # ----- drawing -------------------------------------------------------------------------------------------
    def draw(self, s):
        w, f = self.world, self.fonts
        t = time.time()
        mouse = pygame.mouse.get_pos()
        hovered = self.item_under(mouse) or self.tent_under(mouse)
        s.blit(self.get_backdrop(), (0, 0))
        draw_text(s, f, "BASE CAMP", 54, GOLD, (24, 18))
        if self.mode == "locked":
            sub, lore = "Locked  -  at the bottom of the shaft, 100m down", LOCKED_LORE
        elif self.mode == "view":
            camped = EXPEDITION_DEPTH * w.expedition
            sub, lore = f"Your camp at {camped}m  -  back here at {camped + EXPEDITION_DEPTH}m", VIEW_LORE
        else:
            sub, lore = f"The bottom of expedition {w.expedition + 1}  -  {w.display_depth}m", LORE
        draw_text(s, f, sub, 24, MUTED, (28, 70))
        for i, line in enumerate(wrap_text(f[20], lore, PANEL_RECT.x - 60)):
            draw_text(s, f, line, 20, TEXT, (28, 98 + i * 20))
        with origin_at(ORIGIN):
            self.draw_board(s, t, hovered)
        for p in self.particles:
            pygame.draw.rect(s, p.color, (int(p.x), int(p.y), p.size, p.size))
        if self.mode == "locked":
            self.draw_locked(s, t)
            return
        self.draw_labels(s, hovered)
        self.draw_panel(s, mouse, t)
        self.dev_button.draw(s, f, mouse)

    def draw_locked(self, s, t):
        """Never made camp: the cavern lies in shadow, the tents dark shapes, a padlock over it all - and the
        panel hints at who's waiting down there."""
        w, f = self.world, self.fonts
        shadow = pygame.Surface((PANEL_RECT.x - 10, H), pygame.SRCALPHA)
        shadow.fill((6, 4, 10, 150))
        s.blit(shadow, (0, 0), (0, 150, shadow.get_width(), H))   # (over the cavern, not the title)
        s.blit(shadow, (0, 150))
        with origin_at(ORIGIN):
            cx, cy = iso(BOARD / 2, BOARD / 2, 1.0)
        bob = math.sin(t * 2) * 3
        draw_padlock(s, (cx, cy - 40 + bob), 40, (230, 200, 120))
        draw_text(s, f, "LOCKED", 48, (230, 200, 120), (cx, cy + 34), "center")
        draw_text(s, f, "Defeat The Void Maw at 100m to make camp", 24, TEXT, (cx, cy + 70), "center")
        p = PANEL_RECT
        draw_panel(s, p)
        draw_text(s, f, "Five tents await", 32, TEXT, (p.x + 22, p.y + 16))
        draw_text(s, f, "Each one a hire who stays with you for good", 18, GOLD, (p.x + 24, p.y + 52))
        y = p.y + 84
        for tent, spec in TENTS.items():   # who's waiting: silhouettes only
            color = BRANCHES[tent]["color"]
            img = self.portrait(spec["hire"])
            img = pygame.transform.scale(img, (40, 50))
            img.fill((28, 24, 36), special_flags=pygame.BLEND_RGB_MIN)
            s.blit(img, (p.x + 20, y - 4))
            draw_text(s, f, "? ? ?", 26, TEXT, (p.x + 72, y + 2))
            draw_text(s, f, spec["name"], 18, color, (p.x + 72, y + 26))
            y += 62
        deepest = max(w.lifetime.get("deepest", 0), w.display_depth)
        draw_text(s, f, f"Deepest so far: {deepest}m of 100m", 20, MUTED, (p.x + 22, y + 6))
        bar = pygame.Rect(p.x + 22, y + 32, p.w - 44, 12)
        pygame.draw.rect(s, (40, 34, 52), bar, border_radius=6)
        fill = bar.copy()
        fill.w = int(bar.w * min(1.0, deepest / EXPEDITION_DEPTH))
        if fill.w:
            pygame.draw.rect(s, GOLD, fill, border_radius=6)
        mouse = pygame.mouse.get_pos()
        self.go_button.text = "Back to the dig (B)"
        self.go_button.draw(s, f, mouse)

    def get_backdrop(self):
        """The cavern: rock walls fading into the dark, stalactites hanging from the roof, a few far-off glows."""
        if self.backdrop is None:
            b = self.backdrop = pygame.Surface((W, H))
            for y in range(H):
                q = y / H
                b.fill((int(16 + 10 * q), int(13 + 8 * q), int(20 + 8 * q)), (0, y, W, 1))
            rng = random.Random(7)
            for _ in range(26):   # boulders and rock shelves round the walls
                x, y = rng.uniform(-60, W), rng.uniform(150, H)
                r = rng.uniform(30, 90)
                col = (26 + rng.randint(0, 10), 22 + rng.randint(0, 8), 32 + rng.randint(0, 10))
                pts = [(x + math.cos(a) * r * rng.uniform(0.7, 1.1), y + math.sin(a) * r * 0.55 * rng.uniform(0.7, 1.1))
                       for a in (k / 8 * math.tau for k in range(8))]
                pygame.draw.polygon(b, col, pts)
            pygame.draw.rect(b, (12, 10, 16), (0, 0, W, 34))
            x = -10
            while x < W:   # the roof, and the stalactites hanging off it
                wdt, ln = rng.uniform(14, 34), rng.uniform(20, 90)
                col = (30 + rng.randint(0, 10), 26 + rng.randint(0, 8), 36 + rng.randint(0, 10))
                pygame.draw.polygon(b, col, [(x, 30), (x + wdt, 30), (x + wdt * rng.uniform(0.3, 0.7), 30 + ln)])
                x += wdt * rng.uniform(0.6, 1.4)
            for _ in range(40):   # far-off glows in the dark: mushrooms and crystals
                gx, gy = rng.uniform(0, PANEL_RECT.x), rng.uniform(170, H)
                col = rng.choice([g[0] for g in GLOWS.values()])
                halo = pygame.Surface((24, 24), pygame.SRCALPHA)
                pygame.draw.circle(halo, (*col, 40), (12, 12), 11)
                b.blit(halo, (gx - 12, gy - 12))
                pygame.draw.circle(b, shade(col, 0.8), (int(gx), int(gy)), 2)
        return self.backdrop

    def draw_board(self, s, t, hovered):
        # the floor: dark stone, trodden paths, the stream's wet bed
        for x in range(BOARD):
            for y in range(BOARD):
                if (x, y) in RIVER_CELLS:
                    draw_cube(s, x, y, 1.0, (46, 46, 56), (58, 58, 70), seed=x * 31 + y)
                elif (x, y) in PATHS:
                    draw_cube(s, x, y, 1.0, (86, 70, 58), (104, 86, 70), seed=x * 31 + y)
                else:
                    k = 0.9 + 0.1 * ((x * 7 + y * 13) % 3) / 2
                    draw_cube(s, x, y, 1.0, shade((64, 60, 72), k), (84, 80, 94), seed=x * 31 + y)
        self.draw_stream(s, t)
        # everything standing on it, back to front
        items = [(x + y, "shroom", (x, y, size, glow)) for x, y, size, glow in self.shrooms()]
        if self.has_range():
            items += [(x + y + 0.01 * up, "bale", (x, y, up, k == len(RANGE_BALES) - 1))
                      for k, (x, y, up) in enumerate(RANGE_BALES)]
        items += [(x + y, "sprout", (x, y)) for x, y in SPROUTS]
        items += [(x + y, "stalagmite", (x, y, size)) for x, y, size in STALAGMITES]
        items.append((FIRE[0] + FIRE[1], "fire", None))
        for tent, spec in TENTS.items():
            cx, cy = spec["pos"]
            items.append((cx + cy + 0.4, "tent", tent))
        for tent, m in self.shown_people().items():
            items.append((m.x + m.y, "person", m))
        for key, faded in self.shown_items().items():
            if key in FITTED and not faded:   # (yours: it's part of what it was fitted to now)
                continue
            items.append((item_spot(key)[3] + (0.01 if key in FITTED else 0.0), "item", (key, faded)))
        items.sort(key=lambda it: it[0])
        self.tent_polys = {}
        for _, kind, data in items:
            if kind == "shroom":
                self.draw_mushroom(s, *data, t)
            elif kind == "sprout":
                self.draw_sprouts(s, *data, t)
            elif kind == "stalagmite":
                self.draw_stalagmite(s, *data)
            elif kind == "bale":
                self.draw_bale(s, *data)
            elif kind == "fire":
                if self.mode != "locked":   # (no fire lit till you make camp)
                    self.draw_fire(s, t)
            elif kind == "tent":
                self.draw_tent(s, data, t, hovered == data, self.selected == data)
            elif kind == "item":
                self.draw_item(s, *data, t, hovered == data[0], self.selected == data[0])
            else:
                draw_miner(s, self.fonts, data, 0.0, t)

    def fitted(self, key):
        """The items fitted to this one (shown as part of it) that are yours - or, in the Dev view, all of them."""
        return {other for other, base in FITTED.items() if base == key and (other in self.world.camp_items or self.dev)}

    def draw_pup_ride(self, s, x, y, t, faded):
        """The Mimic Pup, riding on Chompers' lid (Chompers' feet at x, y) - bounced up whenever its parent yawns,
        and now and then hopping for the fun of it."""
        yawn = 0.0 if faded else max(0.0, math.sin(t * 0.6)) ** 6   # (Chompers' yawn: see item_art)
        lid = 14 + 8 * yawn + abs(math.sin(t * 3 + 5)) * 1.5
        hop = 0.0 if faded else 10 * yawn + 6 * max(0.0, math.sin(t * 1.7)) ** 12
        gape = 0.0 if faded else max(0.0, math.sin(t * 0.6 + 2.2)) ** 6
        draw_pet_chest(s, x + 2, y - lid, t, gape, facing=1, lift=hop, size=0.62)

    def item_art(self, s, key, x, y, t, faded, board=False):
        """One of the camp's items, standing at (x, y) on screen (its feet). `board`: on the camp board, where an
        item that's fitted to another is just its own parts (over the other)."""
        if key == "chompers":   # dozing by the tent - and now and then, a big yawn (bouncing its pup)
            yawn = 0.0 if faded else max(0.0, math.sin(t * 0.6)) ** 6
            draw_pet_chest(s, x, y, t, yawn, facing=-1, spiked="collar" in self.world.camp_items or self.dev)
            if "pup" in self.fitted("chompers"):
                self.draw_pup_ride(s, x, y, t, faded)
        elif key == "dummy":
            draw_target_dummy(s, x, y, t)
        elif key == "pup":   # (riding on its parent)
            if not board:
                draw_pet_chest(s, x, y, t, 0.0, facing=-1, spiked="collar" in self.world.camp_items or self.dev)
            self.draw_pup_ride(s, x, y, t, faded)
        elif key == "collar":
            draw_collar_post(s, x, y, t)
        elif key == "taxes":
            draw_tax_strongbox(s, x, y, t, lit=not faded)
        elif key == "rounding":   # (fitted to the ledger desk)
            if board:
                draw_desk_wing(s, x, y, t, live=not faded)
            else:
                draw_ledger_desk(s, x, y, t, wing=True)
        elif key == "divining":
            draw_divining_rod(s, x, y, t, live=not faded, pick="heirloom" in self.fitted("divining"))
        elif key == "banner":
            draw_banner(s, x, y, t, fringe="fringe" in self.fitted("banner"))
        elif key == "heirloom":   # (driven into the rod's stump)
            if board:
                draw_heirloom_pick(s, x, y, t)
            else:
                draw_divining_rod(s, x, y, t, pick=True)
        elif key == "fringe":   # (sewn on the banner)
            if board:
                draw_banner_fringe(s, x, y, t)
            else:
                draw_banner(s, x, y, t, fringe=True)
        elif key == "brazier":
            draw_brazier(s, x, y, t, lit=not faded, explosive="explosive" in self.fitted("brazier"))
        elif key == "explosive":   # (fitted to the brazier)
            if board:
                draw_powder_keg(s, x, y, t, lit=not faded)
            else:
                draw_brazier(s, x, y, t, explosive=True)
        elif key == "rod":
            draw_lightning_rod(s, x, y, t, live=not faded, perched=True)
        elif key == "toolkit":
            draw_toolkit(s, x, y, t, wound=not faded, geared="gears" in self.fitted("toolkit"))
        elif key == "watch":
            draw_pocket_watch(s, x, y, t, running=not faded, hanging=True)
        elif key == "gears":
            if board:   # (fitted to the toolkit: just the gears, over it)
                draw_gear_addon(s, x, y, t, running=not faded)
            else:
                draw_toolkit(s, x, y, t, geared=True)
        elif key == "kiln":
            draw_kiln(s, x, y, t, lit=not faded)
            if "glaze" in self.fitted("kiln"):
                draw_glaze_pots(s, x, y, t)
        elif key == "claypit":
            draw_clay_pit(s, x, y, t, alive=not faded)
            if "wheel" in self.fitted("claypit"):
                draw_potters_wheel(s, x, y, t, live=not faded)
        elif key == "glaze":   # (fitted to the kiln)
            if not board:
                draw_kiln(s, x, y, t)
            draw_glaze_pots(s, x, y, t)
        elif key == "wheel":   # (fitted to the clay pit)
            if not board:
                draw_clay_pit(s, x, y, t)
            draw_potters_wheel(s, x, y, t, live=not faded)
        else:
            draw_ledger_desk(s, x, y, t, lit=not faded, wing="rounding" in self.fitted("ledger"))

    def draw_item(self, s, key, faded, t, hovered, selected):
        """A camp item: yours, drawn as it is; one you could take, a faded ghost of it on a glowing ring."""
        x, y = iso(*item_spot(key)[:3])
        color = BRANCHES[ITEMS[key]["tent"]]["color"]
        if faded or selected:
            ring = pygame.Rect(0, 0, 76 * ITEM_SIZE.get(key, 1.0), 28 * ITEM_SIZE.get(key, 1.0))
            ring.center = (x, y + (34 if key in HANGING else 0))
            pulse = 0.5 + 0.5 * math.sin(t * 3)
            pygame.draw.ellipse(s, shade(color, 0.6 + 0.4 * pulse) if faded else color, ring, 2)
        art = pygame.Surface((80, 80), pygame.SRCALPHA)   # (drawn on its own, scaled up - and if it's not yours
        fx, fy = item_feet(key)                            # yet, faded right back)
        self.item_art(art, key, fx, fy, t, faded, board=True)
        k = ITEM_SCALE * ITEM_SIZE.get(key, 1.0)
        art = pygame.transform.scale(art, (int(80 * k), int(80 * k)))
        if faded:
            art.set_alpha(190 if hovered or selected else int(95 + 30 * math.sin(t * 2.5)))
        s.blit(art, (x - fx * k, y - fy * k))
        if key == "brazier" and not faded:   # (its firelight on the tent's door)
            self.halo(s, (int(x), int(y - 28)), 34, (255, 150, 70), 60)

    def draw_bale(self, s, x, y, up, target):
        """A straw bale for the Target Dummy's range, tied with twine (`up`: stacked on another). The one out front
        has a target painted on, facing down-right."""
        hx, hy = BALE_HALF
        z0 = 1.0 + up * BALE_HIGH
        z1 = z0 + BALE_HIGH
        x0, x1, y0, y1 = x - hx, x + hx, y - hy, y + hy
        straw = (226, 194, 108)
        faces = [([iso(x0, y1, z0), iso(x1, y1, z0), iso(x1, y1, z1), iso(x0, y1, z1)], 0.8),
                 ([iso(x1, y0, z0), iso(x1, y1, z0), iso(x1, y1, z1), iso(x1, y0, z1)], 0.64),
                 ([iso(x0, y0, z1), iso(x1, y0, z1), iso(x1, y1, z1), iso(x0, y1, z1)], 1.0)]
        if not up:
            pygame.draw.polygon(s, (30, 26, 34), [iso(x0 - 0.05, y0, 1.0), iso(x1 + 0.1, y0, 1.0),
                                                  iso(x1 + 0.1, y1 + 0.1, 1.0), iso(x0 - 0.05, y1 + 0.1, 1.0)])
        for poly, k in faces:
            pygame.draw.polygon(s, shade(straw, k), poly)
            pygame.draw.polygon(s, shade(straw, 0.5), poly, 1)
        for k in range(5):   # loose straw on its faces
            a, b = (k * 0.37) % 1, (k * 0.61 + 0.2) % 1
            pygame.draw.line(s, shade(straw, 0.62), iso(x0 + (x1 - x0) * a, y1, z0 + BALE_HIGH * b),
                             iso(x0 + (x1 - x0) * min(1, a + 0.3), y1, z0 + BALE_HIGH * b), 1)
            pygame.draw.line(s, shade(straw, 0.5), iso(x1, y0 + (y1 - y0) * b, z0 + BALE_HIGH * a),
                             iso(x1, y0 + (y1 - y0) * min(1, b + 0.25), z0 + BALE_HIGH * a), 1)
        for q in (0.3, 0.7):   # twine round it
            ty = y0 + (y1 - y0) * q
            pygame.draw.line(s, (130, 92, 50), iso(x0, ty, z1), iso(x1, ty, z1), 1)
            pygame.draw.line(s, (130, 92, 50), iso(x1, ty, z1), iso(x1, ty, z0), 1)
        if target:   # rings painted on its end, facing the archers
            cx, cy = iso(x1, y, (z0 + z1) / 2)
            across = (iso(x1, y + 1, 0)[0] - iso(x1, y, 0)[0], iso(x1, y + 1, 0)[1] - iso(x1, y, 0)[1])
            n = (across[0] ** 2 + across[1] ** 2) ** 0.5
            ux, uy = across[0] / n, across[1] / n
            for r, col in ((8, (240, 240, 235)), (6, (200, 50, 46)), (4, (240, 240, 235)), (2, (200, 50, 46))):
                pts = [(cx + ux * r * math.cos(a), cy + uy * r * math.cos(a) - r * math.sin(a))
                       for a in (k * math.tau / 16 for k in range(16))]
                pygame.draw.polygon(s, col, pts)
            pygame.draw.line(s, (150, 110, 60), (cx + 1, cy - 1), (cx - 9, cy - 7), 2)   # an arrow in it
            pygame.draw.line(s, (240, 240, 235), (cx - 9, cy - 7), (cx - 12, cy - 9), 2)

    def draw_stream(self, s, t):
        """The underground stream: one smooth ribbon of dark water between wet banks, ripples running down it,
        and a plank bridge across."""
        z = 1.0
        left, right = banks(RIVER_HALF + 0.14)   # wet, dark rock along its edges
        pygame.draw.polygon(s, (34, 34, 42), [iso(x, y, z) for x, y in left + right[::-1]])
        left, right = banks(RIVER_HALF)
        water = [iso(x, y, z - 0.1) for x, y in left + right[::-1]]
        pygame.draw.polygon(s, (22, 52, 66), water)
        left, right = banks(RIVER_HALF * 0.45)   # the deeper, brighter run down the middle
        pygame.draw.polygon(s, (30, 72, 88), [iso(x, y, z - 0.1) for x, y in left + right[::-1]])
        n = len(STREAM)
        for k in range(14):   # ripples drifting downstream
            pos = (t * 0.35 + k / 14) % 1 * (n - 1)
            i = int(pos)
            (ax, ay), (bx, by) = STREAM[i], STREAM[min(n - 1, i + 1)]
            q = pos - i
            side = math.sin(k * 2.3) * RIVER_HALF * 0.6
            dx, dy = bx - ax, by - ay
            d = math.hypot(dx, dy) or 1.0
            cx, cy = ax + dx * q - dy / d * side, ay + dy * q + dx / d * side
            p0, p1 = iso(cx, cy, z - 0.1), iso(cx + dx / d * 0.25, cy + dy / d * 0.25, z - 0.1)
            fade = math.sin((t * 0.35 + k / 14) % 1 * math.pi)
            col = (int(70 + 80 * fade), int(130 + 70 * fade), int(150 + 60 * fade))
            pygame.draw.line(s, col, p0, p1, 1)
        ex = STREAM[-1][0]   # where it reaches the edge, it spills over: a little waterfall down the side
        for k in range(5):
            q = k / 4
            x0 = ex - RIVER_HALF + q * RIVER_HALF * 2
            top, bottom = iso(x0, BOARD, z - 0.1), iso(x0, BOARD, 0.0)
            shimmer = (t * 3 + k * 0.37) % 1
            pygame.draw.line(s, (40 + int(60 * shimmer), 92 + int(50 * shimmer), 110 + int(50 * shimmer)), top, bottom, 4)
        foam = iso(ex, BOARD, 0.0)
        pygame.draw.ellipse(s, (150, 190, 205), (foam[0] - 16, foam[1] - 3, 32, 7), 1)
        bx, by = BRIDGE   # a plank bridge, square across the flow
        i = min(range(n), key=lambda j: math.hypot(STREAM[j][0] - bx, STREAM[j][1] - by))
        (ax, ay), (cx, cy) = STREAM[max(0, i - 1)], STREAM[min(n - 1, i + 1)]
        d = math.hypot(cx - ax, cy - ay) or 1.0
        fx, fy = (cx - ax) / d, (cy - ay) / d          # along the flow...
        nx, ny = -fy, fx                               # ...and across it
        span, wide = RIVER_HALF + 0.35, 0.3
        corners = [(bx + nx * span + fx * wide, by + ny * span + fy * wide), (bx - nx * span + fx * wide, by - ny * span + fy * wide),
                   (bx - nx * span - fx * wide, by - ny * span - fy * wide), (bx + nx * span - fx * wide, by + ny * span - fy * wide)]
        pygame.draw.polygon(s, (112, 80, 52), [iso(x, y, z + 0.08) for x, y in corners])
        for k in range(1, 7):   # the planks
            q = k / 7
            a = (corners[0][0] + (corners[1][0] - corners[0][0]) * q, corners[0][1] + (corners[1][1] - corners[0][1]) * q)
            b = (corners[3][0] + (corners[2][0] - corners[3][0]) * q, corners[3][1] + (corners[2][1] - corners[3][1]) * q)
            pygame.draw.line(s, (84, 58, 38), iso(*a, z + 0.08), iso(*b, z + 0.08), 1)
        pygame.draw.polygon(s, (70, 48, 30), [iso(x, y, z + 0.08) for x, y in corners], 1)

    def halo(self, s, pos, radius, color, strength):
        """A soft glow added onto whatever's there (mushrooms, the fire, lamplight)."""
        key = (radius, color, strength)
        img = self.halos.get(key)
        if img is None:
            img = pygame.Surface((radius * 2, radius * 2))
            for r in range(radius, 0, -2):
                q = (1 - r / radius) ** 1.6 * strength / 255
                pygame.draw.circle(img, tuple(int(c * q) for c in color), (radius, radius), r)
            self.halos[key] = img
        s.blit(img, (pos[0] - radius, pos[1] - radius), special_flags=pygame.BLEND_RGB_ADD)

    def draw_mushroom(self, s, x, y, size, glow, t):
        """A giant glowing mushroom: a pale stalk, a broad cap lit from within, spots on top."""
        bright, dim = GLOWS[glow]
        bx, by = iso(x, y, 1.0)
        pulse = 0.85 + 0.15 * math.sin(t * 1.3 + x * 2 + y)
        self.halo(s, (bx, by - 30 * size), int(46 * size), bright, int(70 * pulse))
        pygame.draw.ellipse(s, (20, 18, 26), (bx - 12 * size, by - 4 * size, 24 * size, 8 * size))
        stalk = [(bx - 4 * size, by), (bx + 4 * size, by), (bx + 3 * size, by - 26 * size), (bx - 3 * size, by - 26 * size)]
        pygame.draw.polygon(s, (214, 206, 190), stalk)
        cap = pygame.Rect(0, 0, 40 * size, 18 * size)
        cap.midbottom = (bx, by - 22 * size)
        pygame.draw.ellipse(s, dim, cap.move(0, 3 * size))
        pygame.draw.ellipse(s, tuple(int(c * pulse) for c in bright), cap)
        for k, (dx, dy) in enumerate(((-0.25, 0.35), (0.15, 0.25), (0.3, 0.55), (-0.05, 0.6))):
            pygame.draw.circle(s, (250, 250, 240), (int(cap.x + cap.w * (0.5 + dx)), int(cap.y + cap.h * dy)),
                               max(1, int(2 * size)))

    def draw_sprouts(self, s, x, y, t):
        """A little clump of glowing mushrooms."""
        bx, by = iso(x, y, 1.0)
        bright = GLOWS[("teal", "violet", "amber")[int(x * 3 + y) % 3]][0]
        self.halo(s, (bx, by - 6), 16, bright, 60)
        for dx, h in ((-5, 7), (0, 10), (5, 6)):
            pygame.draw.line(s, (210, 204, 190), (bx + dx, by), (bx + dx, by - h), 2)
            pygame.draw.ellipse(s, bright, (bx + dx - 4, by - h - 3, 8, 5))

    def draw_stalagmite(self, s, x, y, size):
        bx, by = iso(x, y, 1.0)
        pygame.draw.polygon(s, (56, 52, 62), [(bx - 11 * size, by), (bx + 11 * size, by), (bx + 2 * size, by - 46 * size)])
        pygame.draw.polygon(s, (78, 74, 86), [(bx - 11 * size, by), (bx - 2 * size, by), (bx + 2 * size, by - 46 * size)])

    def draw_fire(self, s, t):
        x, y = iso(FIRE[0], FIRE[1], 1.0)
        self.halo(s, (x, y - 10), 190, (255, 140, 60), int(60 + 10 * math.sin(t * 5)))
        glow = pygame.Surface((220, 120), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 150, 60, int(46 + 18 * math.sin(t * 6))), glow.get_rect())
        s.blit(glow, (x - 110, y - 56))
        for k in range(8):   # a ring of stones
            a = k / 8 * math.tau
            pygame.draw.circle(s, (110, 106, 104), (int(x + math.cos(a) * 16), int(y + math.sin(a) * 7)), 4)
        for d in (-12, 12):   # logs
            pygame.draw.line(s, (100, 66, 40), (x - d, y + 4), (x + d, y - 4), 6)
        for k, (col, h) in enumerate((((255, 120, 40), 30), ((255, 190, 70), 22), ((255, 245, 190), 12))):
            flick = math.sin(t * (9 + k * 3)) * 3
            pygame.draw.polygon(s, col, [(x - 12 + k * 4, y), (x + flick, y - h), (x + 12 - k * 4, y)])
        for a in (2.2, 4.0):   # logs to sit on round it
            lx, ly = iso(FIRE[0] + math.cos(a) * 1.1, FIRE[1] + math.sin(a) * 1.1, 1.0)
            pygame.draw.ellipse(s, (110, 76, 48), (lx - 14, ly - 6, 28, 10))
            pygame.draw.ellipse(s, (160, 120, 80), (lx + 8, ly - 5, 7, 8))

    def draw_tent(self, s, tent, t, hovered, selected):
        """An A-frame canvas tent, its door at the end facing the fire. Plain white until its hire moves in;
        then in their colours, with their things about it."""
        spec = TENTS[tent]
        cx, cy = spec["pos"]
        hx, hy = TENT_HALF
        x0, x1, y0, y1, z = cx - hx, cx + hx, cy - hy, cy + hy, 1.0
        top = z + TENT_HIGH
        claimed = tent in self.shown_people()
        style = STYLES[tent]
        canvas = style["canvas"] if claimed else ((58, 54, 66) if self.mode == "locked" else PLAIN)
        back = [iso(x0, y0, z), iso(x1, y0, z), iso(x1, cy, top), iso(x0, cy, top)]
        front = [iso(x0, y1, z), iso(x1, y1, z), iso(x1, cy, top), iso(x0, cy, top)]
        gable = [iso(x1, y0, z), iso(x1, y1, z), iso(x1, cy, top)]
        shadow = [iso(x0 - 0.1, y0 - 0.1, z), iso(x1 + 0.2, y0 - 0.1, z), iso(x1 + 0.2, y1 + 0.2, z), iso(x0 - 0.1, y1 + 0.2, z)]
        pygame.draw.polygon(s, (52, 74, 42), shadow)
        if claimed and tent == "tools":   # a stovepipe chimney through the back slope
            a, b = iso(cx - 0.3, cy - 0.2, top - 0.25), iso(cx - 0.3, cy - 0.2, top + 0.45)
            pygame.draw.line(s, (70, 70, 76), a, b, 6)
        pygame.draw.polygon(s, shade(canvas, 0.78), back)
        pygame.draw.polygon(s, shade(canvas, 0.92), front)
        if claimed and style.get("stripe"):   # awning stripes down the front slope
            for k in range(0, 8, 2):
                q0, q1 = k / 8, (k + 1) / 8
                strip = [iso(x0 + (x1 - x0) * q0, y1, z), iso(x0 + (x1 - x0) * q1, y1, z),
                         iso(x0 + (x1 - x0) * q1, cy, top), iso(x0 + (x1 - x0) * q0, cy, top)]
                pygame.draw.polygon(s, shade(style["stripe"], 0.92), strip)
        pygame.draw.polygon(s, canvas, gable)
        for poly in (front, gable):
            pygame.draw.polygon(s, shade(canvas, 0.6), poly, 2)
        # the door: a dark opening, flaps tied back
        d0, d1, dt_ = iso(x1, cy - 0.28, z), iso(x1, cy + 0.28, z), iso(x1, cy, z + TENT_HIGH * 0.62)
        pygame.draw.polygon(s, (40, 30, 30) if claimed else (90, 86, 80), [d0, d1, dt_])
        if claimed:   # lamplight inside
            self.halo(s, (int((d0[0] + d1[0]) / 2), int((d0[1] + d1[1]) / 2) - 8), 34, (255, 200, 120), 70)
            pygame.draw.circle(s, (255, 214, 140), (int((d0[0] + d1[0]) / 2), int((d0[1] + d1[1]) / 2) - 8), 3)
        pygame.draw.line(s, shade(canvas, 0.55), d0, dt_, 2)
        pygame.draw.line(s, shade(canvas, 0.55), d1, dt_, 2)
        ridge0, ridge1 = iso(x0 - 0.12, cy, top), iso(x1 + 0.12, cy, top)
        pygame.draw.line(s, (110, 80, 50), ridge0, ridge1, 3)
        for end in (x0 - 0.12, x1 + 0.12):   # guy ropes to pegs
            a = iso(end, cy, top)
            peg = iso(end + (0.35 if end > cx else -0.35), cy, z)
            pygame.draw.line(s, (200, 190, 170), a, peg, 1)
        if claimed:
            self.draw_tent_dressing(s, tent, style, (x0, x1, y0, y1, z, top), t)
        elif self.mode != "locked":   # a hand-painted sign: they're hiring
            sx, sy = iso(x1 + 0.5, y1 + 0.05, z)
            pygame.draw.line(s, (100, 70, 44), (sx, sy), (sx, sy - 26), 3)
            board = pygame.Rect(0, 0, 50, 18)
            board.midbottom = (sx, sy - 22)
            pygame.draw.rect(s, (150, 112, 70), board, border_radius=2)
            pygame.draw.rect(s, (100, 70, 44), board, 1, border_radius=2)
            text = "HIRING" if spec["hire"] else "SOON"
            img = self.fonts[14].render(text, True, (60, 36, 20))
            s.blit(img, img.get_rect(center=board.center))
        if hovered or selected:
            color = (255, 255, 255) if selected else BRANCHES[tent]["color"]
            pygame.draw.polygon(s, color, front, 2)
            pygame.draw.polygon(s, color, gable, 2)
        self.tent_polys[tent] = [back, front, gable]

    def draw_tent_dressing(self, s, tent, style, box, t):
        """A claimed tent: a pennant on its pole, its emblem on the canvas, and its owner's things outside."""
        x0, x1, y0, y1, z, top = box
        cx, cy = TENTS[tent]["pos"]
        pole = iso(x1 + 0.12, cy, top)
        pygame.draw.line(s, (110, 80, 50), pole, (pole[0], pole[1] - 18), 2)
        wave = math.sin(t * 4 + cx) * 3
        pygame.draw.polygon(s, style["trim"], [(pole[0], pole[1] - 18), (pole[0] + 16, pole[1] - 14 + wave),
                                               (pole[0], pole[1] - 10)])
        mid = iso((x0 + x1) / 2, (cy + y1) / 2, (z + top) / 2)
        pygame.draw.circle(s, shade(style["canvas"], 0.6), (int(mid[0]), int(mid[1])), 11)
        draw_icon(s, style["icon"], mid, 8, style["trim"])
        if tent == "tools":   # an anvil and a glowing forge
            fx, fy = iso(x1 + 0.4, y0 - 0.1, z)
            glow = pygame.Surface((50, 30), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 140, 50, int(70 + 40 * math.sin(t * 7))), glow.get_rect())
            s.blit(glow, (fx - 25, fy - 18))
            pygame.draw.rect(s, (80, 76, 80), (fx - 9, fy - 12, 18, 12), border_radius=2)
            pygame.draw.rect(s, (255, 150, 60), (fx - 6, fy - 10, 12, 4))
            ax, ay = iso(x1 + 0.8, y0 + 0.2, z)
            pygame.draw.polygon(s, (64, 64, 74), [(ax - 9, ay - 10), (ax + 9, ay - 10), (ax + 5, ay - 6), (ax + 5, ay),
                                                  (ax - 5, ay), (ax - 5, ay - 6)])
        elif tent == "combat":   # an archery butt on an easel
            bx, by = iso(x1 + 0.9, y1 + 0.3, z)
            pygame.draw.line(s, (110, 80, 50), (bx - 6, by), (bx, by - 26), 2)
            pygame.draw.line(s, (110, 80, 50), (bx + 6, by), (bx, by - 26), 2)
            for r, col in ((10, (240, 240, 235)), (7, (200, 50, 46)), (4, (240, 240, 235)), (2, (240, 200, 70))):
                pygame.draw.circle(s, col, (bx, by - 20), r)
            pygame.draw.line(s, (150, 110, 60), (bx + 1, by - 21), (bx + 12, by - 27), 2)
        elif tent == "fortune" and "taxes" not in self.shown_items():   # a little desk, coins stacked on it (the
                                                                         # strongbox stands there once it's yours)
            dx, dy = iso(x1 + 0.6, y1 + 0.15, z)
            pygame.draw.rect(s, (120, 84, 52), (dx - 12, dy - 12, 24, 6))
            for d in (-9, 9):
                pygame.draw.line(s, (96, 66, 42), (dx + d, dy - 6), (dx + d, dy), 2)
            for k in range(4):
                pygame.draw.ellipse(s, GOLD, (dx - 7 + (k % 2) * 7, dy - 15 - (k // 2) * 3, 7, 4))
        elif tent == "hands":   # a heap of wet clay, a handprint pressed into it
            hx, hy = iso(x1 + 0.6, y0 + 0.05, z)
            pygame.draw.ellipse(s, (132, 80, 50), (hx - 14, hy - 12, 28, 14))
            pygame.draw.ellipse(s, (186, 116, 74), (hx - 12, hy - 14, 24, 12))
            for k in range(4):
                pygame.draw.line(s, (132, 80, 50), (hx - 4 + k * 3, hy - 11), (hx - 5 + k * 3, hy - 7), 2)
        elif tent == "crew":   # a pick rack, and a lantern on a post
            rx, ry = iso(x1 + 0.55, y0 - 0.05, z)
            for d in (-1, 1):
                pygame.draw.line(s, (120, 82, 44), (rx + d * 7, ry), (rx - d * 5, ry - 22), 2)
                pygame.draw.line(s, (200, 205, 216), (rx - d * 9, ry - 20), (rx - d * 1, ry - 24), 3)
            lx, ly = iso(x1 + 0.5, y1 + 0.35, z)
            pygame.draw.line(s, (90, 66, 44), (lx, ly), (lx, ly - 30), 2)
            halo = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 210, 120, 70), (20, 20), 18)
            s.blit(halo, (lx - 20, ly - 50))
            pygame.draw.circle(s, (255, 226, 150), (lx, ly - 30), 4)

    def draw_labels(self, s, hovered):
        """Each open tent's name on a little plate under it, while there's a hire to choose (a tent that's been
        taken has its owner's colours to go by instead). Once this visit's hire is made, or just looking round from
        the dig, only the tent under the mouse keeps its plate."""
        f = self.fonts
        choosing = self.mode == "locked" or self.choosing()
        plates = []
        for tent, spec in TENTS.items():
            if tent != hovered and (not choosing or tent in self.shown_people()):
                continue
            cx, cy = spec["pos"]
            plates.append((tent, spec["name"], BRANCHES[tent]["color"], (cx + 0.6, cy + 0.7)))   # (board point)
        for key, faded in self.shown_items().items():   # (the items you could take, too)
            if key == hovered or (faded and choosing):
                x, y, z, _ = item_spot(key)
                with origin_at(ORIGIN):   # (one up on a tent: by it, not on the ground under it)
                    at = iso(x, y, z) if key in PERCHED else iso(x + 0.25, y + 0.25, z)
                if key in HANGING:
                    at = (at[0], at[1] + 52)
                elif key in FITTED:   # (over what it's fitted to, so as not to cover the plates round it)
                    at = (at[0] - 8, at[1] - 34 - 66 * ITEM_SCALE * ITEM_SIZE.get(key, 1.0))
                plates.append((key, ITEMS[key]["name"], BRANCHES[ITEMS[key]["tent"]]["color"], at))
        for key, name, color, at in plates:
            if key in TENTS:
                with origin_at(ORIGIN):
                    at = iso(*at, 1.0)
            x, y = at
            img = f[20].render(name, True, (255, 255, 255) if key in (hovered, self.selected) else TEXT)   # (20px: the font frays smaller)
            box = img.get_rect(midtop=(x, y + 4)).inflate(12, 4)
            pygame.draw.rect(s, (20, 16, 28), box, border_radius=6)
            pygame.draw.rect(s, color, box, 1, border_radius=6)
            s.blit(img, img.get_rect(center=box.center))

    # ----- the panel ------------------------------------------------------------------------------------------
    def portrait(self, hire, m=None):
        """A big picture of a character, drawn from their sprite."""
        if m is None:
            m = Miner(role=hire)
            m.apply_look(CAMP_LOOKS[hire])
            m.hp = m.max_hp = 1.0
        m = _Sitter(m)
        img = pygame.Surface((64, 80), pygame.SRCALPHA)
        with origin_at((32, 74)):
            draw_miner(img, self.fonts, m, 0.0, time.time())
        return pygame.transform.scale(img, (96, 120))

    def draw_panel(self, s, mouse, t):
        w, f = self.world, self.fonts
        p = PANEL_RECT
        draw_panel(s, p)
        btn = self.hire_button
        if self.selected in ITEMS:
            self.draw_item_panel(s, t)
            btn.draw(s, f, mouse)
            self.draw_footer(s, mouse, t)
            return
        tent = self.selected
        spec = TENTS[tent]
        color = BRANCHES[tent]["color"]
        pygame.draw.rect(s, color, (p.x, p.y + 14, 5, 60))
        draw_text(s, f, spec["name"], 32, TEXT, (p.x + 22, p.y + 16))
        draw_text(s, f, f"{BRANCHES[tent]['name']}  -  {BRANCHES[tent]['blurb']}", 18, color, (p.x + 24, p.y + 52))
        hire = spec["hire"]
        btn = self.hire_button
        y = p.y + 84
        if hire is None:
            for line in wrap_text(f[22], "This tent's hire hasn't been decided yet. It stands ready.", p.w - 40):
                draw_text(s, f, line, 22, MUTED, (p.x + 20, y))
                y += 24
            btn.text, btn.enabled = "Coming soon", False
        else:
            info = HIRES[hire]
            here = self.people.get(tent)
            s.blit(self.portrait(hire, here), (p.x + 18, y - 8))
            name = CAMP_LOOKS[hire]["name"]
            draw_text(s, f, name, 28, TEXT, (p.x + 130, y + 14))
            draw_text(s, f, info["title"], 22, color, (p.x + 130, y + 42))
            status = ("Just hired!" if hire == self.hired else f"With you - level {here.level}") if here                 else "Looking for work"
            draw_text(s, f, status, 20, GOOD if here else MUTED, (p.x + 130, y + 68))
            y += 120
            for line in wrap_text(f[20], info["blurb"], p.w - 40):
                draw_text(s, f, line, 20, MUTED, (p.x + 20, y))
                y += 21
            y += 8
            y = self.draw_bullets(s, info["does"] + ["Knocked out, never killed"], p.x + 24, y, p.w - 44)
            if here:
                btn.text, btn.enabled = f"{name} is with you", False
            elif self.mode == "view":
                camped = EXPEDITION_DEPTH * (w.expedition + 1)
                btn.text, btn.enabled = f"Hire at your next visit ({camped}m)", False
            elif self.hired:
                btn.text, btn.enabled = "One new pick per visit", False
            else:
                btn.text, btn.enabled = f"Hire {name}", True
                draw_glow(s, btn.rect, t)
        btn.draw(s, f, mouse)
        self.draw_footer(s, mouse, t)

    def draw_item_panel(self, s, t):
        """The panel for one of the camp's items: what it is, what it does, and the button to take it."""
        w, f = self.world, self.fonts
        p, key = PANEL_RECT, self.selected
        item = ITEMS[key]
        tent = item["tent"]
        color = BRANCHES[tent]["color"]
        owner = CAMP_LOOKS[TENTS[tent]["hire"]]["name"]
        pygame.draw.rect(s, color, (p.x, p.y + 14, 5, 60))
        draw_text(s, f, item["name"], 32, TEXT, (p.x + 22, p.y + 16))
        draw_text(s, f, f"{TENTS[tent]['name']}  -  {owner}'s", 18, color, (p.x + 24, p.y + 52))
        y = p.y + 84
        art = pygame.Surface((64, 60), pygame.SRCALPHA)   # (a big picture of it)
        self.item_art(art, key, 32, 8 if key in HANGING else 52, t, False)
        s.blit(pygame.transform.scale(art, (128, 120)), (p.x + 4, y - 14))
        ours = key in w.camp_items
        could = key in open_items(w.camp, w.camp_items)   # (the Dev view shows things you can't have yet)
        status = ("Just taken!" if key == self.hired else "Yours") if ours else "Up for grabs" if could else "Not yet"
        draw_text(s, f, status, 22, GOOD if ours else MUTED, (p.x + 140, y + 40))
        y += 120
        for line in wrap_text(f[20], item["blurb"], p.w - 40):
            draw_text(s, f, line, 20, MUTED, (p.x + 20, y))
            y += 21
        y += 8
        y = self.draw_bullets(s, item["does"], p.x + 24, y, p.w - 44)
        btn = self.hire_button
        if ours:
            btn.text, btn.enabled = "Yours, for good", False
        elif not could:
            needs = ITEMS[item["requires"]]["name"] if item.get("requires") in ITEMS and TENTS[tent]["hire"] in w.camp                 else HIRES[TENTS[tent]["hire"]]["title"]
            btn.text, btn.enabled = f"Needs the {needs}", False
        elif self.mode != "visit":
            btn.text, btn.enabled = "Take it at your next visit", False
        elif self.hired:
            btn.text, btn.enabled = "One new pick per visit", False
        else:
            btn.text, btn.enabled = f"Take the {item['name']}", True
            draw_glow(s, btn.rect, t)

    def draw_bullets(self, s, lines, x, y, width):
        """A list of "- " points, each wrapping onto more lines (indented under its text) when it's too long for
        `width`. Returns the y below it."""
        f = self.fonts
        indent = f[20].size("- ")[0]
        for item in lines:
            for i, line in enumerate(wrap_text(f[20], item, width - indent)):
                draw_text(s, f, line if i else f"- {line}", 20, TEXT, (x + (indent if i else 0), y))
                y += 22
        return y

    def draw_footer(self, s, mouse, t):
        """Under the panel: the lifetime record, and the button to set off (or go back to the dig)."""
        w, f = self.world, self.fonts
        p = PANEL_RECT
        self.draw_record(s)
        go = self.go_button
        if self.mode == "view":
            go.text = "Back to the dig (B)"
            go.draw(s, f, mouse)
            return
        go.text = f"Set off: expedition {w.expedition + 2}, from {w.display_depth + 1}m"
        if not self.choosing():
            draw_glow(s, go.rect, t)
        go.draw(s, f, mouse)
        draw_text(s, f, "The same 100m again - no tougher - with your camp along", 18, MUTED,
                  (p.centerx, go.rect.bottom + 8), "midtop")

    def draw_record(self, s):
        """Bottom left: the lifetime record."""
        w, f = self.world, self.fonts
        life = w.lifetime
        done = w.expedition + (1 if self.mode == "visit" else 0)   # (looking round mid-expedition: not done yet)
        parts = [f"{done} expedition{'s' if done != 1 else ''} finished",
                 f"deepest {max(life['deepest'], w.display_depth)}m", f"{fmt(life['blocks'])} blocks",
                 f"{fmt(life['gold'])} gold", f"{fmt(life['monsters'])} monsters", f"{life['bosses']} bosses",
                 f"{len(w.graveyard)} fallen remembered"]
        box = pygame.Rect(16, H - 118, 330, 104)
        draw_panel(s, box)
        x, y = box.x + 14, box.y + 8
        draw_text(s, f, "Lifetime", 20, GOLD, (x, y))
        for i, row in enumerate((parts[:2], parts[2:4], parts[4:6], parts[6:])):
            draw_text(s, f, "   ".join(row), 18, MUTED, (x, y + 20 + i * 18))


class _Sitter:
    """A character posed for their portrait: standing still at the origin, facing you."""

    def __init__(self, m):
        self._m = m

    def __getattr__(self, name):
        if name in ("x", "y"):
            return 0.0
        if name == "draw_z":
            return 0.0
        if name == "state":
            return "working"
        return getattr(self._m, name)
