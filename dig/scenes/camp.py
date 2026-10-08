"""Base Camp: the shaft has come down at the bottom of an expedition. Build one thing at camp, then dig on.

The camp is laid out round a campfire: the five core buildings in a ring (one per upgrade branch), the items built
onto each branching outward from it. Click one to see it; Build raises it and starts the next expedition.
"""
import math
import random
import time

import pygame

from ..camp import CAMP, CORES, CYCLE_GROWTH, EXPEDITION_DEPTH, buildable
from ..config import GOLD, GOOD, H, MUTED, TEXT, W
from ..effects import Particle
from ..icons import draw_icon
from ..ui import Button, draw_glow, draw_panel, draw_text, wrap_text
from ..upgrades import BRANCHES, TABS
from ..util import fmt, shade
from .base import Scene

PANEL_RECT = pygame.Rect(W - 400, 104, 376, H - 164)
CENTRE = ((PANEL_RECT.x - 12) // 2, H // 2 + 70)
RINGS = (90, 195, 295)    # how far out the core buildings, their items, and the items beyond sit
SQUASH = 0.85              # (the camp is seen at an angle: rings are flattened ellipses)
SPREAD = 19                # degrees either side of a core its two items sit at
NODE_R = 28
LORE = ["The Void Maw's death-throes bring the shaft down. The crew escape up the last rope and the gear is",
        "buried - but the relics you found are set into the foundations of a camp at the bottom. Build one thing."]


def layout():
    """Screen position of every camp node: cores in a ring, their items fanning out behind them."""
    pos = {}
    for i, tab in enumerate(TABS):
        core = next(k for k in CORES if CAMP[k]["branch"] == tab)
        base = math.radians(i * 72 - 90)
        place = lambda key, ang, r: pos.__setitem__(key, (CENTRE[0] + math.cos(ang) * r,
                                                          CENTRE[1] + math.sin(ang) * r * SQUASH))
        place(core, base, RINGS[0])
        kids = [k for k, c in CAMP.items() if c["parent"] == core]
        for side, kid in zip((-1, 1), kids):
            ang = base + math.radians(SPREAD * side)
            place(kid, ang, RINGS[1])
            for grand in (k for k, c in CAMP.items() if c["parent"] == kid):
                place(grand, ang + math.radians(3 * side), RINGS[2])
    return pos


class CampScene(Scene):
    simulate = False   # the dig waits while you build

    def __init__(self, game):
        super().__init__(game)
        self.pos = layout()
        self.selected = None
        self.particles = []
        p = PANEL_RECT
        self.build_button = Button((p.x + 20, p.bottom - 72, p.w - 40, 54), "", self.build, size=30,
                                   color=(60, 130, 80))

    def enter(self):
        options = buildable(self.world.camp)
        self.selected = options[0] if options else None

    def node_under_mouse(self, pos):
        for key, (x, y) in self.pos.items():
            if math.hypot(pos[0] - x, pos[1] - y) <= NODE_R + 4:
                return key
        return None

    def build(self):
        w = self.world
        if not self.selected or self.selected not in buildable(w.camp):
            return
        built = CAMP[self.selected]
        self.game.world = type(w).next_expedition(w, self.selected)
        self.game.save()
        self.game.bg_key, self.game.bg_prev, self.game.bg_fade = "topsoil", None, 1.0
        self.game.toast = (f"{built['name']} built at Base Camp!", 4.0)
        self.game.switch("play")

    def handle(self, event):
        if self.build_button.handle(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.node_under_mouse(event.pos)
            if key:
                self.selected = key
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.build()

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        if random.random() < dt * 14:   # sparks rising off the campfire
            self.particles.append(Particle(CENTRE[0] + random.uniform(-10, 10), CENTRE[1] - 14,
                                           random.choice([(255, 200, 90), (255, 140, 50), (255, 240, 180)])))

    # ----- drawing ----------------------------------------------------------------------------------------------
    def draw(self, s):
        w, f = self.world, self.fonts
        t = time.time()
        mouse = pygame.mouse.get_pos()
        hovered = self.node_under_mouse(mouse)
        built, options = set(w.camp), set(buildable(w.camp))

        draw_text(s, f, "BASE CAMP", 54, GOLD, (24, 20))
        draw_text(s, f, f"The bottom of expedition {w.expedition + 1}  -  {w.display_depth}m", 24, MUTED, (28, 70))
        for i, line in enumerate(LORE):
            draw_text(s, f, line, 20, TEXT, (28, 100 + i * 20))

        self.draw_ground(s, t)
        for key, node in CAMP.items():   # paths: campfire to the cores, each item to what it's built onto
            start = CENTRE if node["parent"] is None else self.pos[node["parent"]]
            color = BRANCHES[node["branch"]]["color"]
            lit = key in built
            pygame.draw.line(s, shade(color, 0.8) if lit else (58, 52, 74), start, self.pos[key], 4 if lit else 2)
        self.draw_fire(s, t)
        for key in CAMP:
            self.draw_node(s, key, key in built, key in options, key == hovered, key == self.selected, t)
        for p in self.particles:
            pygame.draw.rect(s, p.color, (int(p.x), int(p.y), p.size, p.size))
        self.draw_panel(s, hovered or self.selected, mouse, built, options, t)
        self.draw_record(s)

    def draw_ground(self, s, t):
        ground = pygame.Surface((RINGS[2] * 2 + 120, int((RINGS[2] + 60) * 2 * SQUASH)), pygame.SRCALPHA)
        pygame.draw.ellipse(ground, (40, 32, 26, 200), ground.get_rect())
        pygame.draw.ellipse(ground, (70, 56, 44, 200), ground.get_rect(), 3)
        s.blit(ground, ground.get_rect(center=CENTRE))

    def draw_fire(self, s, t):
        x, y = CENTRE
        glow = pygame.Surface((160, 100), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 150, 60, int(50 + 20 * math.sin(t * 6))), glow.get_rect())
        s.blit(glow, (x - 80, y - 46))
        for d in (-12, 12):   # logs
            pygame.draw.line(s, (100, 66, 40), (x - d, y + 6), (x + d, y - 2), 6)
        for k, (col, h) in enumerate((((255, 120, 40), 30), ((255, 190, 70), 22), ((255, 245, 190), 12))):
            flick = math.sin(t * (9 + k * 3)) * 3
            pygame.draw.polygon(s, col, [(x - 12 + k * 4, y), (x + flick, y - h), (x + 12 - k * 4, y)])

    def draw_node(self, s, key, built, option, hovered, selected, t):
        node = CAMP[key]
        x, y = self.pos[key]
        color = BRANCHES[node["branch"]]["color"]
        core = node["parent"] is None
        r = NODE_R + (6 if core else 0) + (3 if hovered else 0)
        if built:
            fill, edge, icon = shade(color, 0.7), shade(color, 1.3), (255, 255, 255)
            halo = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(halo, (*color, 60), (r * 2, r * 2), r * 2)
            s.blit(halo, (x - r * 2, y - r * 2))
        elif option:
            fill, edge, icon = shade(color, 0.25), color, shade(color, 1.1)
            pygame.draw.circle(s, color, (int(x), int(y)), int(r + 6 + 3 * math.sin(t * 5)), 2)
        else:
            fill, edge, icon = (36, 32, 48), (72, 66, 90), (88, 82, 106)
        if selected:
            pygame.draw.circle(s, (255, 255, 255), (int(x), int(y)), r + 11, 2)
        pygame.draw.circle(s, (12, 10, 18), (int(x), int(y + 4)), r)
        if core:   # the core buildings: a roof over them
            pts = [(x - r, y + r * 0.7), (x - r, y - r * 0.2), (x, y - r * 1.05), (x + r, y - r * 0.2), (x + r, y + r * 0.7)]
            pygame.draw.polygon(s, fill, pts)
            pygame.draw.polygon(s, GOLD if built else edge, pts, 3)
        else:
            pygame.draw.circle(s, fill, (int(x), int(y)), r)
            pygame.draw.circle(s, edge, (int(x), int(y)), r, 3)
        draw_icon(s, node["icon"], (x, y + (4 if core else 0)), r * 0.55, icon)
        img = self.fonts[18].render(node["name"], True, TEXT if (built or option) else MUTED)
        box = img.get_rect(midtop=(x, y + r + 5)).inflate(10, 4)
        pygame.draw.rect(s, (20, 16, 28), box, border_radius=5)
        s.blit(img, img.get_rect(center=box.center))

    def draw_record(self, s):
        """Bottom left: the lifetime record, and the fallen on the memorial."""
        w, f = self.world, self.fonts
        life = w.lifetime
        parts = [f"{w.expedition + 1} expedition{'s' if w.expedition else ''} finished",
                 f"deepest {max(life['deepest'], w.display_depth)}m", f"{fmt(life['blocks'])} blocks",
                 f"{fmt(life['gold'])} gold", f"{fmt(life['monsters'])} monsters", f"{life['bosses']} bosses",
                 f"{len(w.graveyard)} fallen remembered"]
        x, y = PANEL_RECT.x + 20, PANEL_RECT.bottom - 92 - 20 * 4   # (in the panel, above the Build button)
        pygame.draw.line(s, (78, 66, 104), (x, y - 8), (PANEL_RECT.right - 20, y - 8), 1)
        draw_text(s, f, "Lifetime", 20, GOLD, (x, y))
        for i, row in enumerate((parts[:2], parts[2:4], parts[4:6], parts[6:])):
            draw_text(s, f, "   ".join(row), 19, MUTED, (x, y + 20 + i * 19))

    def draw_panel(self, s, key, mouse, built, options, t):
        w, f = self.world, self.fonts
        p = PANEL_RECT
        draw_panel(s, p)
        nxt = w.expedition + 2
        draw_text(s, f, f"Next: expedition {nxt}, from {w.display_depth + 1}m", 22, MUTED, (p.x + 20, p.y - 34))
        btn = self.build_button
        btn.gold = None
        if not key:
            btn.text, btn.enabled = "Every building is up!", False
            btn.draw(s, f, mouse)
            return
        node = CAMP[key]
        color = BRANCHES[node["branch"]]["color"]
        pygame.draw.rect(s, color, (p.x, p.y + 14, 5, 60))
        pygame.draw.circle(s, shade(color, 0.7), (p.x + 52, p.y + 44), 28)
        draw_icon(s, node["icon"], (p.x + 52, p.y + 44), 18, (255, 255, 255))
        draw_text(s, f, node["name"], 32, TEXT, (p.x + 94, p.y + 18))
        kind = "Core building" if node["parent"] is None else f"Built onto the {CAMP[node['parent']]['name']}"
        draw_text(s, f, f"{BRANCHES[node['branch']]['name']}  -  {kind}", 20, color, (p.x + 96, p.y + 52))
        y = p.y + 96
        for line in wrap_text(f[24], node["desc"], p.w - 40):
            draw_text(s, f, line, 24, MUTED, (p.x + 20, y))
            y += 24
        y += 16
        draw_text(s, f, "For every expedition after:", 20, MUTED, (p.x + 20, y))
        y += 24
        for line in wrap_text(f[26], node["bonus"], p.w - 40):
            draw_text(s, f, line, 26, GOOD, (p.x + 20, y))
            y += 26
        y += 20
        for line in wrap_text(f[20], f"The next expedition's blocks and monsters are {round(100 * (CYCLE_GROWTH - 1))}% "
                                     f"tougher - and pay {round(100 * (CYCLE_GROWTH - 1))}% more.", p.w - 40):
            draw_text(s, f, line, 20, MUTED, (p.x + 20, y))
            y += 20
        if key in built:
            btn.text, btn.enabled = "Already built", False
        elif key in options:
            btn.text, btn.enabled = "Build", True
            draw_glow(s, btn.rect, t)
        else:
            btn.text, btn.enabled = f"Build the {CAMP[node['parent']]['name']} first", False
        btn.draw(s, f, mouse)
