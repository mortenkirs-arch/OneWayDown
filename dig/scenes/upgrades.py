"""Upgrades: a star map of every upgrade, five branches in sectors round a core, paths crossing between them.

Drag with either mouse button (or WASD / the arrow keys) to move about, the wheel (or Q / E, + / -) to zoom.
"""
import math
import random
import time

import pygame

from ..config import BAD, GOLD, GOOD, H, MUTED, TEXT, W
from ..effects import CoinFly, Particle
from ..icons import draw_icon
from ..render import draw_flying_coins
from ..ui import Button, draw_callout, draw_glow, draw_gold, draw_panel, draw_pointer, draw_text, wrap_text
from ..upgrades import (BRANCHES, RING_IN, RING_STEP, SECTOR_DEG, TABS, UPGRADES, UPGRADES_BY_TAB, UPGRADE_BY_KEY,
                        is_maxed, sector_angle, star_pos, star_xy, tree_requires)
from ..util import fmt, shade
from .base import Scene

# The detail panel hugs the right edge; the map fills the rest of the screen, under the header.
PANEL_RECT = pygame.Rect(W - 400, 104, 376, H - 164)
VIEW = pygame.Rect(0, 0, PANEL_RECT.x - 12, H)
HEADER_H = 72
CHIP_Y, CHIP_H = 82, 30
MAP_EDGE = RING_IN + 5.4 * RING_STEP        # how far out the map goes (the camera stays inside)
ZOOM_MIN, ZOOM_MAX = 0.3, 1.5
ZOOM_STEP = 1.15                            # per wheel notch
KEY_ZOOM_RATE = 1.9                         # zoom factor per second holding Q / E
PAN_SPEED = 750                             # screen px per second holding WASD / the arrows
DRAG_START = 6                              # px the mouse has to move with a button down before it's a drag
NODE_HIT_RADIUS = 36                        # (at zoom 1)
LABEL_ZOOM = 0.5                            # names under the stars from this zoom in
CORE_R = 46
NEB_SCALE = 0.2                             # the nebulae are painted at this fraction of map size
RADAR_R = 62
PAN_KEYS = {pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
            pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1)}


def home_zoom():
    """Zoom that frames the core and the first ring round it."""
    return max(ZOOM_MIN, min(1.0, min(VIEW.w, VIEW.h - HEADER_H) / (2 * (RING_IN + 1.3 * RING_STEP))))


def _lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def _soft_disc(radius, color, alpha):
    """A blurry blob: stacked translucent circles, strongest in the middle."""
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for k in range(8, 0, -1):
        pygame.draw.circle(surf, (*color, int(alpha * (1 - k / 9) ** 1.5) + 2), (radius, radius), int(radius * k / 8))
    return surf


class UpgradeScene(Scene):
    simulate = False   # opening the map pauses the game: no mining, income, enemies or timers

    def __init__(self, game):
        super().__init__(game)
        self.return_to = "menu"
        self.selected = "miners"
        self.cam = [0.0, -RING_IN * 0.3]   # map point at the middle of the view
        self.zoom = home_zoom()
        self.goal = None                    # (x, y, zoom) the camera is gliding to, if any
        self.press = None                   # (button, start pos, camera then) while a mouse button is held
        self.dragging = False
        self.particles = []
        self.coins = []                     # spent coins flying from the gold counter to an upgrade
        self.bursts = []                    # [seconds until the coins land, key, colour]
        self.counter_coin = (W - 200, 46)
        self.star = {u["key"]: star_pos(u) for u in UPGRADES}
        self.roots = [u for u in UPGRADES if not u["requires"]]
        self.chips = {}                     # branch: rect of its jump-to chip in the header
        self.screen_pos = {}                # key: where its star was drawn this frame
        self.glows = {}
        self.backdrop = self.make_backdrop()
        self.nebula = self.make_nebula()
        self.neb_cache = (None, None)
        p = PANEL_RECT
        self.buy_button = Button((p.x + 20, p.bottom - 72, p.w - 40, 54), "", self.buy_selected,
                                 size=30, color=(60, 130, 80))
        self.back_button = Button((24, H - 50, 130, 40), "< Back", self.close, size=26, color=(70, 64, 90))
        self.radar_c = (24 + RADAR_R, H - 70 - RADAR_R)

    # ----- the sky ----------------------------------------------------------------------------------------------
    @staticmethod
    def make_backdrop():
        """Deep space, and three tiles of stars that drift at different speeds as the map moves."""
        sky = pygame.Surface(VIEW.size)
        for y in range(VIEW.h):
            k = y / VIEW.h
            sky.fill(_lerp((14, 10, 26), (5, 4, 12), k), (0, y, VIEW.w, 1))
        rng = random.Random(11)
        layers = []
        for depth, count, size, bright in ((0.15, 160, 1, 120), (0.35, 90, 1, 190), (0.6, 40, 2, 235)):
            tile = pygame.Surface((512, 512), pygame.SRCALPHA)
            for _ in range(count):
                c = bright + rng.randint(-30, 20)
                tint = rng.choice(((c, c, c), (c, c - 20, c + 15), (c + 10, c, c - 30)))
                pygame.draw.circle(tile, (*[max(0, min(255, v)) for v in tint], 255),
                                   (rng.randint(0, 511), rng.randint(0, 511)), size)
            layers.append((depth, tile))
        return sky, layers

    def make_nebula(self):
        """Each branch's sector glows its colour: soft clouds painted small, scaled up when drawn."""
        side = int(2 * MAP_EDGE * NEB_SCALE)
        neb = pygame.Surface((side, side), pygame.SRCALPHA)
        rng = random.Random(5)
        for tab in TABS:
            color = BRANCHES[tab]["color"]
            for _ in range(7):
                deg = sector_angle(tab) + rng.uniform(-24, 24)
                x, y = star_xy(deg, rng.uniform(0.6, 4.2))
                r = int(rng.uniform(150, 290) * NEB_SCALE)
                blob = _soft_disc(r, shade(color, 0.7), rng.randint(40, 70))
                neb.blit(blob, (side / 2 + x * NEB_SCALE - r, side / 2 + y * NEB_SCALE - r))
        return neb

    def draw_sky(self, s, t):
        sky, layers = self.backdrop
        s.blit(sky, VIEW.topleft)
        for depth, tile in layers:   # parallax: far stars barely move
            ox = int(-self.cam[0] * self.zoom * depth) % 512
            oy = int(-self.cam[1] * self.zoom * depth) % 512
            for x in range(ox - 512, VIEW.w, 512):
                for y in range(oy - 512, VIEW.h, 512):
                    s.blit(tile, (VIEW.x + x, VIEW.y + y))
        key = (round(self.cam[0], 1), round(self.cam[1], 1), round(self.zoom, 4))
        if self.neb_cache[0] != key:   # (only re-scaled when the view moves)
            self.neb_cache = (key, self.scaled_nebula())
        if self.neb_cache[1]:
            img, pos = self.neb_cache[1]
            s.blit(img, pos)

    def scaled_nebula(self):
        """The part of the nebula under the view, scaled to it: (image, where) or None."""
        side = self.nebula.get_width()
        k = NEB_SCALE / self.zoom   # nebula px per screen px
        x0, y0 = self.to_map(VIEW.topleft)
        src = pygame.Rect(int(side / 2 + x0 * NEB_SCALE), int(side / 2 + y0 * NEB_SCALE),
                          int(VIEW.w * k) + 2, int(VIEW.h * k) + 2)
        clipped = src.clip(self.nebula.get_rect())
        if clipped.w < 1 or clipped.h < 1:
            return None
        img = pygame.transform.smoothscale(self.nebula.subsurface(clipped),
                                           (int(clipped.w / k) + 1, int(clipped.h / k) + 1))
        return img, (VIEW.x + (clipped.x - src.x) / k, VIEW.y + (clipped.y - src.y) / k)

    # ----- camera -----------------------------------------------------------------------------------------------
    def to_screen(self, p):
        return (VIEW.centerx + (p[0] - self.cam[0]) * self.zoom,
                VIEW.centery + HEADER_H / 2 + (p[1] - self.cam[1]) * self.zoom)

    def to_map(self, pos):
        return ((pos[0] - VIEW.centerx) / self.zoom + self.cam[0],
                (pos[1] - VIEW.centery - HEADER_H / 2) / self.zoom + self.cam[1])

    def clamp_cam(self):
        d = math.hypot(*self.cam)
        if d > MAP_EDGE * 0.85:
            self.cam = [c * MAP_EDGE * 0.85 / d for c in self.cam]

    def zoom_at(self, pos, factor):
        """Zoom by `factor`, keeping the map point under `pos` where it is."""
        before = self.to_map(pos)
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom * factor))
        after = self.to_map(pos)
        self.cam[0] += before[0] - after[0]
        self.cam[1] += before[1] - after[1]
        self.clamp_cam()
        self.goal = None

    def focus(self, point, zoom):
        self.goal = (point[0], point[1], zoom)

    def focus_branch(self, tab):
        """Glide over to a branch's sector and select its first upgrade."""
        self.focus(star_xy(sector_angle(tab), 1.6), max(self.zoom, home_zoom() * 0.9))
        first = min((u for u in UPGRADES_BY_TAB[tab] if not tree_requires(u)), key=lambda u: u["depth"])
        self.select(first["key"])

    def home(self):
        self.focus((0.0, -RING_IN * 0.3), home_zoom())

    def enter(self):
        if self.world.lv("miners") == 0:   # (a fresh start: begin on the core, where Hire Miner is)
            self.cam, self.zoom, self.goal = [0.0, -RING_IN * 0.3], home_zoom(), None
            self.select("miners")

    # ----- actions ----------------------------------------------------------------------------------------------
    def close(self):
        self.game.switch(self.return_to)

    def select(self, key):
        self.selected = key

    def buy(self, up):
        """Spend: coins pour out of the gold counter into the upgrade's star, which bursts when they land."""
        if not self.world.buy(up):
            return
        x, y = self.to_screen(self.star[up["key"]])
        for i in range(12):
            self.coins.append(CoinFly(self.counter_coin, (x, y), delay=i * 0.025, duration=0.45, size=7,
                                      lift=(0, 18)))
        self.bursts.append([0.5, up["key"], BRANCHES[up["branch"]]["color"]])

    def buy_selected(self):
        self.buy(UPGRADE_BY_KEY[self.selected])

    def node_under_mouse(self, pos):
        if not VIEW.collidepoint(pos) or pos[1] < HEADER_H:
            return None
        reach = max(14, NODE_HIT_RADIUS * self.zoom)
        best = None
        for key, (x, y) in self.screen_pos.items():
            d = math.hypot(pos[0] - x, pos[1] - y)
            if d <= reach and (best is None or d < best[0]):
                best = (d, key)
        return best and best[1]

    def chip_under_mouse(self, pos):
        return next((tab for tab, rect in self.chips.items() if rect.collidepoint(pos)), None)

    def radar_hit(self, pos):
        return math.hypot(pos[0] - self.radar_c[0], pos[1] - self.radar_c[1]) <= RADAR_R

    def affordable_in(self, tab):
        return sum(1 for u in UPGRADES_BY_TAB[tab] if self.world.can_buy(u))

    def node_state(self, up):
        lv = self.world.levels
        if not self.world.available(up):
            return "locked"
        if is_maxed(up, lv):
            return "maxed"
        return "owned" if lv[up["key"]] > 0 else "available"

    # ----- scene hooks ------------------------------------------------------------------------------------------
    def handle(self, event):
        if self.back_button.handle(event) or self.buy_button.handle(event):
            return
        if event.type == pygame.MOUSEWHEEL:
            pos = pygame.mouse.get_pos()
            if VIEW.collidepoint(pos):
                self.zoom_at(pos, ZOOM_STEP ** event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            chip = self.chip_under_mouse(event.pos)
            if chip and event.button == 1:
                self.focus_branch(chip)
            elif self.radar_hit(event.pos):   # jump to that part of the map
                k = MAP_EDGE / RADAR_R
                self.focus(((event.pos[0] - self.radar_c[0]) * k, (event.pos[1] - self.radar_c[1]) * k), self.zoom)
            elif VIEW.collidepoint(event.pos):
                self.press, self.dragging = (event.button, event.pos, list(self.cam)), False
        elif event.type == pygame.MOUSEMOTION and self.press:
            button, start, cam = self.press
            dx, dy = event.pos[0] - start[0], event.pos[1] - start[1]
            if not self.dragging and math.hypot(dx, dy) > DRAG_START:
                self.dragging, self.goal = True, None
            if self.dragging:   # the map follows the mouse
                self.cam = [cam[0] - dx / self.zoom, cam[1] - dy / self.zoom]
                self.clamp_cam()
        elif event.type == pygame.MOUSEBUTTONUP and self.press and event.button == self.press[0]:
            if not self.dragging:   # a click, not a drag: left selects, right buys
                key = self.node_under_mouse(event.pos)
                if key:
                    self.select(key)
                    if event.button == 3:
                        self.buy(UPGRADE_BY_KEY[key])
            self.press, self.dragging = None, False
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_u):
                self.close()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.buy_selected()
            elif pygame.K_1 <= event.key <= pygame.K_1 + len(TABS) - 1:
                self.focus_branch(TABS[event.key - pygame.K_1])
            elif event.key == pygame.K_TAB:
                here = UPGRADE_BY_KEY[self.selected]["branch"]
                step = -1 if event.mod & pygame.KMOD_SHIFT else 1
                self.focus_branch(TABS[(TABS.index(here) + step) % len(TABS)])
            elif event.key in (pygame.K_HOME, pygame.K_h, pygame.K_0):
                self.home()
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.zoom_at(VIEW.center, ZOOM_STEP)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.zoom_at(VIEW.center, 1 / ZOOM_STEP)

    def update(self, dt):
        keys = pygame.key.get_pressed()
        dx = sum(d[0] for k, d in PAN_KEYS.items() if keys[k])
        dy = sum(d[1] for k, d in PAN_KEYS.items() if keys[k])
        if dx or dy:
            norm = math.hypot(dx, dy)
            self.cam[0] += dx / norm * PAN_SPEED * dt / self.zoom
            self.cam[1] += dy / norm * PAN_SPEED * dt / self.zoom
            self.clamp_cam()
            self.goal = None
        if keys[pygame.K_q] != keys[pygame.K_e]:
            self.zoom_at(VIEW.center, KEY_ZOOM_RATE ** (dt if keys[pygame.K_e] else -dt))
        if self.goal:   # glide there
            gx, gy, gz = self.goal
            k = min(1.0, dt * 6)
            self.cam[0] += (gx - self.cam[0]) * k
            self.cam[1] += (gy - self.cam[1]) * k
            self.zoom += (gz - self.zoom) * k
            if math.hypot(gx - self.cam[0], gy - self.cam[1]) < 1 and abs(gz - self.zoom) < 0.002:
                self.goal = None
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for c in self.coins:
            c.update(dt)
        self.coins = [c for c in self.coins if not c.arrived]
        for b in self.bursts:   # the star bursts as the spent coins land in it
            b[0] -= dt
            if b[0] <= 0:
                x, y = self.to_screen(self.star[b[1]])
                for _ in range(24):
                    self.particles.append(Particle(x, y, random.choice([b[2], GOLD, (255, 255, 255)]), big=True))
        self.bursts = [b for b in self.bursts if b[0] > 0]

    # ----- drawing ----------------------------------------------------------------------------------------------
    def draw(self, s):
        mouse = pygame.mouse.get_pos()
        t = time.time()
        self.screen_pos = {k: self.to_screen(p) for k, p in self.star.items()}
        hovered = None if self.dragging else self.node_under_mouse(mouse)

        s.set_clip(VIEW)
        self.draw_sky(s, t)
        self.draw_sectors(s)
        self.draw_core(s, t)
        self.draw_edges(s, t)
        for up in UPGRADES:
            self.draw_node(s, up, hovered == up["key"], self.selected == up["key"], t)
        for p in self.particles:
            pygame.draw.rect(s, p.color, (int(p.x), int(p.y), p.size, p.size))
        s.set_clip(None)

        self.draw_header(s, mouse)
        self.draw_radar(s)
        self.draw_panel(s, UPGRADE_BY_KEY[hovered or self.selected], mouse)
        self.back_button.draw(s, self.fonts, mouse)
        for i, hint in enumerate(("Drag / WASD / arrows: move   Wheel / Q E: zoom",
                                  "Click: select   Right-click / Enter: buy   1-5: jump")):
            draw_text(s, self.fonts, hint, 19, MUTED, (PANEL_RECT.centerx, PANEL_RECT.bottom + 16 + i * 19), "center")
        draw_flying_coins(s, self.coins)
        self.draw_first_hire_guide(s, t)

    def draw_header(self, s, mouse):
        w, f = self.world, self.fonts
        shade_bar = pygame.Surface((W, HEADER_H + CHIP_H + 20), pygame.SRCALPHA)
        for y in range(shade_bar.get_height()):   # the map fades out under the header
            a = 235 if y < HEADER_H else int(235 * (1 - (y - HEADER_H) / (CHIP_H + 20)))
            shade_bar.fill((10, 8, 18, a), (0, y, W, 1))
        s.blit(shade_bar, (0, 0))
        title = draw_text(s, f, "UPGRADES", 50, TEXT, (24, 22))
        badge = pygame.Rect(title.right + 18, 26, 112, 30)   # pause indicator next to the title
        pygame.draw.rect(s, (60, 52, 30), badge, border_radius=8)
        pygame.draw.rect(s, GOLD, badge, 2, border_radius=8)
        for dx in (-41, -35):
            pygame.draw.rect(s, GOLD, (badge.centerx + dx, badge.centery - 7, 4, 14))
        draw_text(s, f, "PAUSED", 24, GOLD, (badge.centerx + 10, badge.centery), "center")
        gold_rect = draw_gold(s, f, fmt(w.gold), 44, GOLD, (W - 30, 22), "topright")
        self.counter_coin = (gold_rect.x + 13, gold_rect.centery - 1)   # where spent coins fly from
        draw_text(s, f, f"{fmt(w.gold_per_sec())} gold / sec", 22, MUTED,
                  (gold_rect.left - 14, gold_rect.centery), "midright")
        x = 24   # a chip per branch: click (or 1-5) to fly to it
        for i, tab in enumerate(TABS):
            color = BRANCHES[tab]["color"]
            label = f[22].render(f"{i + 1} {BRANCHES[tab]['name']}", True, TEXT)
            rect = pygame.Rect(x, CHIP_Y, label.get_width() + 26, CHIP_H)
            self.chips[tab] = rect
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(s, shade(color, 0.45 if hover else 0.3), rect, border_radius=15)
            pygame.draw.rect(s, color, rect, 2, border_radius=15)
            s.blit(label, label.get_rect(center=rect.center))
            if any(u["key"] in w.new_unlocks for u in UPGRADES_BY_TAB[tab]):
                pill = pygame.Rect(rect.x - 4, rect.y - 9, 36, 15)
                pygame.draw.rect(s, GOLD, pill, border_radius=7)
                draw_text(s, f, "NEW", 15, (60, 40, 10), pill.center, "center")
            count = self.affordable_in(tab)
            if count:
                pygame.draw.circle(s, BAD, (rect.right - 2, rect.y + 2), 10)
                draw_text(s, f, str(count), 18, TEXT, (rect.right - 2, rect.y + 2), "center")
            x = rect.right + 12

    def draw_sectors(self, s):
        """Faint borders between the branches, and each one's name out past its last ring."""
        z = self.zoom
        for i, tab in enumerate(TABS):
            edge = sector_angle(tab) - SECTOR_DEG / 2
            for k in range(16):   # dashed
                a = star_xy(edge, -0.6 + k * 0.36)
                b = star_xy(edge, -0.6 + k * 0.36 + 0.18)
                pygame.draw.line(s, (46, 40, 66), self.to_screen(a), self.to_screen(b), 1)
            color = BRANCHES[tab]["color"]
            size = max(22, min(60, int(46 * z)))
            lines = [self.fonts[size].render(BRANCHES[tab]["name"].upper(), True, shade(color, 0.85))]
            if z >= 0.45:   # what the branch is about, tucked under its name (once it's readable)
                lines.append(self.fonts[max(16, size // 2)].render(BRANCHES[tab]["blurb"], True, shade(color, 0.6)))
            bw, bh = max(img.get_width() for img in lines), sum(img.get_height() + 2 for img in lines)
            a = math.radians(sector_angle(tab))   # (the block sits out beyond the point, never back over the stars)
            x, y = self.to_screen(star_xy(sector_angle(tab), 5.0))
            x, y = x + math.sin(a) * bw / 2, y - math.cos(a) * bh / 2 - bh / 2
            for img in lines:
                s.blit(img, img.get_rect(midtop=(x, y)))
                y += img.get_height() + 2

    def draw_core(self, s, t):
        """The dig at the heart of the map, with faint spokes out to where each branch begins."""
        z = self.zoom
        cx, cy = self.to_screen((0, 0))
        for up in self.roots + [UPGRADE_BY_KEY["power"]]:
            pygame.draw.line(s, shade(BRANCHES[up["branch"]]["color"], 0.4), (cx, cy), self.screen_pos[up["key"]], 2)
        r = CORE_R * z
        pulse = 0.5 + 0.5 * math.sin(t * 2)
        s.blit(self.glow((255, 200, 90), int(r * 2.2 + 6 * pulse)), (cx - int(r * 2.2 + 6 * pulse), cy - int(r * 2.2 + 6 * pulse)))
        pygame.draw.circle(s, (60, 40, 20), (cx, cy), r)
        pygame.draw.circle(s, GOLD, (cx, cy), r, max(2, int(4 * z)))
        draw_icon(s, "pick", (cx, cy - r * 0.12), r * 0.55, (255, 235, 180))
        if z >= LABEL_ZOOM:
            draw_text(s, self.fonts, f"{self.world.depth}m", max(14, int(22 * z)), GOLD, (cx, cy + r * 0.55), "center")

    def glow(self, color, radius):
        radius = max(2, int(radius))
        key = (color, radius)
        if key not in self.glows:
            if len(self.glows) > 300:
                self.glows.clear()
            self.glows[key] = _soft_disc(radius, color, 110)
        return self.glows[key]

    def draw_edges(self, s, t):
        w = self.world
        z = self.zoom
        for up in UPGRADES:
            child = self.screen_pos[up["key"]]
            open_ = w.available(up)   # the upgrade this path leads to can actually be bought
            for req_key, req_lv in up["requires"]:
                start = self.screen_pos[req_key]
                if not (VIEW.clipline(start, child)):
                    continue
                c0 = BRANCHES[UPGRADE_BY_KEY[req_key]["branch"]]["color"]
                c1 = BRANCHES[up["branch"]]["color"]
                have = w.levels[req_key]
                if have >= req_lv and not open_:   # done, but something else still holds it back
                    self.path(s, start, child, c0, c1, 0.75, max(2, int(3 * z)))
                elif have >= req_lv:
                    self.path(s, start, child, c0, c1, 0.35, max(4, int(10 * z)))
                    self.path(s, start, child, c0, c1, 1.0, max(2, int(4 * z)))
                    for k in range(3):   # dots flowing along open paths
                        u = (t * 0.5 + k / 3) % 1
                        pygame.draw.circle(s, (255, 255, 255), (start[0] + (child[0] - start[0]) * u,
                                                                start[1] + (child[1] - start[1]) * u), max(2, 3 * z))
                elif have > 0:
                    self.path(s, start, child, c0, c1, 0.5, max(2, int(3 * z)))
                else:
                    pygame.draw.line(s, (58, 52, 74), start, child, max(1, int(3 * z)))

    @staticmethod
    def path(s, a, b, c0, c1, bright, width):
        """A straight path from a to b, its colour shading from one branch's to the other's on a crossing."""
        if c0 == c1:
            pygame.draw.line(s, shade(c0, bright), a, b, width)
            return
        steps = 10
        for i in range(steps):
            p, q = i / steps, (i + 1) / steps
            col = shade(_lerp(c0, c1, (p + q) / 2), bright)
            pygame.draw.line(s, col, (a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p),
                             (a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q), width)

    def draw_node(self, s, up, hovered, selected, t):
        x, y = self.screen_pos[up["key"]]
        z = self.zoom
        big = len(tree_requires(up)) != 1   # roots and merge points are hexagons
        r = max(9, (34 if big else 28) * z) + (3 if hovered else 0)
        if not VIEW.inflate(r * 4, r * 6).collidepoint(x, y):
            return
        state = self.node_state(up)
        color = BRANCHES[up["branch"]]["color"]
        lv = self.world.levels[up["key"]]
        if state == "locked":
            fill, border, icon = (36, 32, 48), (72, 66, 90), (88, 82, 106)
        elif state == "available":
            fill, border, icon = shade(color, 0.25), color, shade(color, 1.1)
        else:
            fill, border, icon = shade(color, 0.7), shade(color, 1.3), (255, 255, 255)
            g = self.glow(color, r * 1.9)   # owned stars shine
            s.blit(g, (x - g.get_width() // 2, y - g.get_height() // 2))
        if self.world.can_buy(up):
            pygame.draw.circle(s, color, (x, y), r + 7 * z + 3 * math.sin(t * 5), 2)
        if selected:
            pygame.draw.circle(s, (255, 255, 255), (x, y), r + 12 * z + 2, 2)
        pygame.draw.circle(s, (12, 10, 18), (x, y + 4 * z), r)
        edge_col = GOLD if state == "maxed" else border
        edge_w = max(2, int((4 if state == "maxed" else 3) * min(1, z + 0.2)))
        if big:   # hexagon for roots and merge points
            pts = [(x + math.cos(a) * r * 1.08, y + math.sin(a) * r * 1.08)
                   for a in (math.pi / 6 + i * math.pi / 3 for i in range(6))]
            pygame.draw.polygon(s, fill, pts)
            pygame.draw.polygon(s, edge_col, pts, edge_w)
        else:
            pygame.draw.circle(s, fill, (x, y), r)
            pygame.draw.circle(s, edge_col, (x, y), r, edge_w)
        draw_icon(s, up["icon"], (x, y), r * 0.62, icon)
        if state == "locked" and z >= LABEL_ZOOM:   # little padlock
            lx, ly = x + r * 0.7, y + r * 0.6
            pygame.draw.arc(s, (170, 160, 190), (lx - 6, ly - 12, 12, 14), 0, math.pi, 2)
            pygame.draw.rect(s, (170, 160, 190), (lx - 8, ly - 5, 16, 12), border_radius=3)
        if up["key"] in self.world.new_unlocks:   # just opened up by a depth milestone
            if hovered or selected:
                self.world.new_unlocks.discard(up["key"])
            else:
                pill = pygame.Rect(0, 0, 42, 18)
                pill.midleft = (x + r - 6, y - r + 4)
                pygame.draw.rect(s, GOLD, pill, border_radius=9)
                draw_text(s, self.fonts, "NEW", 18, (60, 40, 10), pill.center, "center")
        if z < LABEL_ZOOM and not (hovered or selected):
            return
        size = max(15, min(28, int(24 * z)))
        name_img = self.fonts[size].render(up["name"], True, TEXT if state != "locked" else MUTED)
        if self.world.depth < up["depth"]:   # milestone not reached yet: the depth to dig to instead of the level
            lv_text, lv_color = f"at {up['depth']}m", (240, 150, 90)
        else:
            lv_text = "MAX" if state == "maxed" else (f"{lv}/{up['max']}" if up["max"] else f"Lv {lv}")
            lv_color = GOLD if state == "maxed" else MUTED
        lv_img = self.fonts[max(14, size - 3)].render(lv_text, True, lv_color)
        box = pygame.Rect(0, 0, max(name_img.get_width(), lv_img.get_width()) + 12,
                          name_img.get_height() + lv_img.get_height() + 6)
        box.midtop = (x, y + r + 5)
        pygame.draw.rect(s, (20, 16, 28), box, border_radius=6)
        s.blit(name_img, name_img.get_rect(midtop=(x, box.y + 3)))
        s.blit(lv_img, lv_img.get_rect(midtop=(x, box.y + 3 + name_img.get_height())))

    def draw_radar(self, s):
        """A little overview of the whole map, with the part on screen boxed: click it to go there."""
        cx, cy = self.radar_c
        k = RADAR_R / MAP_EDGE
        disc = pygame.Surface((RADAR_R * 2 + 4, RADAR_R * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(disc, (12, 10, 22, 220), (RADAR_R + 2, RADAR_R + 2), RADAR_R)
        s.blit(disc, (cx - RADAR_R - 2, cy - RADAR_R - 2))
        pygame.draw.circle(s, (78, 66, 104), (cx, cy), RADAR_R, 2)
        for up in UPGRADES:
            x, y = self.star[up["key"]]
            state = self.node_state(up)
            color = BRANCHES[up["branch"]]["color"]
            col = (70, 64, 90) if state == "locked" else color if state == "available" else shade(color, 1.3)
            pygame.draw.circle(s, col, (cx + x * k, cy + y * k), 2 if state == "locked" else 3)
        pygame.draw.circle(s, GOLD, (cx, cy), 3)
        x0, y0 = self.to_map((VIEW.x, HEADER_H))
        x1, y1 = self.to_map(VIEW.bottomright)
        box = pygame.Rect(cx + x0 * k, cy + y0 * k, (x1 - x0) * k, (y1 - y0) * k)
        if box.contains((cx - RADAR_R, cy - RADAR_R, RADAR_R * 2, RADAR_R * 2)):   # (the whole map is in view)
            return
        old = s.get_clip()
        s.set_clip(pygame.Rect(cx - RADAR_R, cy - RADAR_R, RADAR_R * 2, RADAR_R * 2))
        pygame.draw.rect(s, (220, 215, 235), box, 1)
        s.set_clip(old)

    def draw_first_hire_guide(self, s, t):
        """No miners yet and one is affordable: lead the way to Hire Miner > Buy."""
        w = self.world
        if w.lv("miners") > 0 or not w.can_buy(UPGRADE_BY_KEY["miners"]):
            return
        f = self.fonts
        x, y = self.screen_pos["miners"]
        r = max(9, 34 * self.zoom)
        draw_pointer(s, (x - r - 12, y), "right", t)
        if self.selected != "miners":
            draw_callout(s, f, [("Click Hire Miner", GOLD)], (x - r - 66, y), "midright")
            return
        draw_callout(s, f, [("Hire your first miner!", GOLD), ("Press Buy", TEXT)], (x - r - 66, y), "midright")
        draw_glow(s, self.buy_button.rect, t)

    def draw_panel(self, s, up, mouse):
        w = self.world
        f = self.fonts
        p = PANEL_RECT
        draw_panel(s, p)
        color = BRANCHES[up["branch"]]["color"]
        state = self.node_state(up)
        lv = w.levels[up["key"]]

        pygame.draw.rect(s, color, (p.x, p.y + 14, 5, 60))
        pygame.draw.circle(s, shade(color, 0.7), (p.x + 52, p.y + 44), 28)
        draw_icon(s, up["icon"], (p.x + 52, p.y + 44), 18, (255, 255, 255))
        draw_text(s, f, up["name"], 34, TEXT, (p.x + 94, p.y + 18))
        draw_text(s, f, BRANCHES[up["branch"]]["name"], 22, color, (p.x + 96, p.y + 50))

        y = p.y + 96
        for line in wrap_text(f[24], up["desc"], p.w - 40):
            draw_text(s, f, line, 24, MUTED, (p.x + 20, y))
            y += 24
        y += 14
        draw_text(s, f, f"Level {lv}" + (f" / {up['max']}" if up["max"] else ""), 28, TEXT, (p.x + 20, y))
        if up["max"]:   # level pips
            pip_w = min(18, (p.w - 40) // up["max"] - 3)
            for i in range(up["max"]):
                rect = (p.x + 20 + i * (pip_w + 3), y + 28, pip_w, 8)
                pygame.draw.rect(s, color if i < lv else (60, 54, 76), rect, border_radius=3)
            y += 14
        y += 40
        draw_text(s, f, "Now", 22, MUTED, (p.x + 20, y))
        draw_text(s, f, up["effect"](lv), 26, TEXT, (p.x + 80, y - 2))
        if state != "maxed":
            y += 30
            draw_text(s, f, "Next", 22, MUTED, (p.x + 20, y))
            draw_text(s, f, up["effect"](lv + 1), 26, GOOD, (p.x + 80, y - 2))
        y += 44
        needs = []
        for k, n in up["requires"]:
            req = UPGRADE_BY_KEY[k]
            other = req["branch"] != up["branch"]   # (a path crossing over from a neighbouring branch)
            needs.append((f"{req['name']}  Lv {n}", w.levels[k] >= n,
                          BRANCHES[req["branch"]]["color"] if other else None))
        if up["depth"]:
            needs.append((f"Reach depth {up['depth']}m  (you: {w.depth}m)", w.depth >= up["depth"], None))
        if needs:
            draw_text(s, f, "Requires", 22, MUTED, (p.x + 20, y))
            y += 26
            for text, ok, branch_col in needs:
                pygame.draw.circle(s, GOOD if ok else BAD, (p.x + 30, y + 9), 6)
                rect = draw_text(s, f, text, 24, TEXT if ok else MUTED, (p.x + 44, y))
                if branch_col:
                    pygame.draw.circle(s, branch_col, (rect.right + 10, y + 9), 5)
                y += 26

        btn = self.buy_button
        btn.gold = None
        if up["key"] != self.selected:
            btn.text, btn.enabled = "Click a star to select it", False
        elif state == "locked":
            btn.text, btn.enabled = "Locked", False
        elif state == "maxed":
            btn.text, btn.enabled = "MAXED", False
        else:
            cost = w.cost(up)
            btn.text, btn.gold = "Buy", fmt(cost)
            btn.enabled = w.gold >= cost
        btn.draw(s, f, mouse)
