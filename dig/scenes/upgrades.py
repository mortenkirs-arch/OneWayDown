"""Branching upgrade tree screen."""
import math
import random
import time

import pygame

from ..config import GOLD, GOOD, BAD, H, MUTED, TEXT, W
from ..effects import Particle
from ..icons import draw_icon
from ..ui import Button, draw_panel, draw_text, wrap_text
from ..upgrades import BRANCHES, UPGRADES, UPGRADE_BY_KEY, is_maxed, is_unlocked, upgrade_cost
from ..util import fmt, shade
from .base import Scene

TREE_TIER_Y = [112, 224, 336, 448, 566]
PANEL_RECT = pygame.Rect(880, 104, 370, 556)
NODE_HIT_RADIUS = 36


def tree_col_x(col):
    return 120 + col * 210


def bezier(p0, p1, steps=24):
    """S-curve from p0 down to p1 (vertical tangents at both ends)."""
    (x0, y0), (x1, y1) = p0, p1
    my = (y0 + y1) / 2
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        pts.append((a * x0 + b * x0 + c * x1 + d * x1, a * y0 + b * my + c * my + d * y1))
    return pts


class UpgradeScene(Scene):
    simulate = False   # opening the tree pauses the game: no mining, income, enemies or timers

    def __init__(self, game):
        super().__init__(game)
        self.return_to = "menu"
        self.selected = "power"
        self.particles = []
        self.node_pos = {u["key"]: (tree_col_x(u["pos"][0]), TREE_TIER_Y[u["pos"][1]]) for u in UPGRADES}
        p = PANEL_RECT
        self.buy_button = Button((p.x + 20, p.bottom - 72, p.w - 40, 54), "", self.buy_selected,
                                 size=30, color=(60, 130, 80))
        self.back_button = Button((24, H - 66, 150, 48), "< Back", self.close, size=28, color=(70, 64, 90))

    # ----- actions --------------------------------------------------------
    def close(self):
        self.game.switch(self.return_to)

    def buy(self, up):
        if not self.world.buy(up):
            return
        x, y = self.node_pos[up["key"]]
        color = BRANCHES[up["branch"]]["color"]
        for _ in range(24):
            self.particles.append(Particle(x, y, random.choice([color, GOLD, (255, 255, 255)]), big=True))

    def buy_selected(self):
        self.buy(UPGRADE_BY_KEY[self.selected])

    def node_under_mouse(self, pos):
        for key, (x, y) in self.node_pos.items():
            if math.hypot(pos[0] - x, pos[1] - y) <= NODE_HIT_RADIUS:
                return key
        return None

    def node_state(self, up):
        lv = self.world.levels
        if not is_unlocked(up, lv):
            return "locked"
        if is_maxed(up, lv):
            return "maxed"
        return "owned" if lv[up["key"]] > 0 else "available"

    # ----- scene hooks ----------------------------------------------------
    def handle(self, event):
        if self.back_button.handle(event) or self.buy_button.handle(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            key = self.node_under_mouse(event.pos)
            if key:
                self.selected = key
                if event.button == 3:
                    self.buy(UPGRADE_BY_KEY[key])
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_u):
                self.close()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.buy_selected()

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, s):
        w = self.world
        f = self.fonts
        mouse = pygame.mouse.get_pos()
        t = time.time()
        hovered = self.node_under_mouse(mouse)

        draw_text(s, f, "UPGRADE TREE", 50, TEXT, (24, 24))
        draw_text(s, f, "Unlock paths, then merge them", 22, MUTED, (26, 62))
        badge = pygame.Rect(318, 26, 112, 30)   # pause indicator next to the title
        pygame.draw.rect(s, (60, 52, 30), badge, border_radius=8)
        pygame.draw.rect(s, GOLD, badge, 2, border_radius=8)
        for dx in (-41, -35):
            pygame.draw.rect(s, GOLD, (badge.centerx + dx, badge.centery - 7, 4, 14))
        draw_text(s, f, "PAUSED", 24, GOLD, (badge.centerx + 10, badge.centery), "center")
        gold_rect = draw_text(s, f, f"$ {fmt(w.gold)}", 44, GOLD, (W - 30, 26), "topright")
        draw_text(s, f, f"{fmt(w.gold_per_sec())} / sec", 22, MUTED,
                  (gold_rect.left - 14, gold_rect.centery), "midright")

        for col, branch in enumerate(("crew", "tools", "hands", "fortune")):
            color = BRANCHES[branch]["color"]
            draw_text(s, f, BRANCHES[branch]["name"].upper(), 20, shade(color, 0.8),
                      (tree_col_x(col), TREE_TIER_Y[1] - 50), "center")

        self.draw_edges(s, t)
        for up in UPGRADES:
            self.draw_node(s, up, hovered == up["key"], self.selected == up["key"], t)
        for p in self.particles:
            pygame.draw.rect(s, p.color, (int(p.x), int(p.y), p.size, p.size))

        self.draw_panel(s, UPGRADE_BY_KEY[hovered or self.selected], mouse)
        self.back_button.draw(s, f, mouse)
        draw_text(s, f, "Left-click: select   Right-click / Enter: buy", 20, MUTED,
                  (PANEL_RECT.centerx, PANEL_RECT.bottom + 22), "center")

    # ----- drawing helpers ------------------------------------------------
    def draw_edges(self, s, t):
        for up in UPGRADES:
            child = self.node_pos[up["key"]]
            color = BRANCHES[up["branch"]]["color"]
            for req_key, req_lv in up["requires"]:
                pts = bezier(self.node_pos[req_key], child)
                have = self.world.levels[req_key]
                if have >= req_lv:
                    pygame.draw.lines(s, shade(color, 0.35), False, pts, 10)
                    pygame.draw.lines(s, color, False, pts, 4)
                    for k in range(3):   # dots flowing along unlocked paths
                        u = (t * 0.5 + k / 3) % 1
                        idx = u * (len(pts) - 1)
                        i0 = int(idx)
                        i1 = min(i0 + 1, len(pts) - 1)
                        frac = idx - i0
                        px = pts[i0][0] + (pts[i1][0] - pts[i0][0]) * frac
                        py = pts[i0][1] + (pts[i1][1] - pts[i0][1]) * frac
                        pygame.draw.circle(s, (255, 255, 255), (px, py), 3)
                elif have > 0:
                    pygame.draw.lines(s, shade(color, 0.5), False, pts, 3)
                else:
                    pygame.draw.lines(s, (58, 52, 74), False, pts, 3)

    def draw_node(self, s, up, hovered, selected, t):
        x, y = self.node_pos[up["key"]]
        state = self.node_state(up)
        color = BRANCHES[up["branch"]]["color"]
        big = up["branch"] in ("mastery", "core")
        r = (36 if big else 30) + (3 if hovered else 0)
        lv = self.world.levels[up["key"]]

        if state == "locked":
            fill, border, icon = (36, 32, 48), (72, 66, 90), (88, 82, 106)
        elif state == "available":
            fill, border, icon = shade(color, 0.25), color, shade(color, 1.1)
        else:
            fill, border, icon = shade(color, 0.7), shade(color, 1.3), (255, 255, 255)

        if self.world.can_buy(up):
            pygame.draw.circle(s, color, (x, y), r + 7 + 3 * math.sin(t * 5), 2)
        if selected:
            pygame.draw.circle(s, (255, 255, 255), (x, y), r + 12, 2)
        pygame.draw.circle(s, (12, 10, 18), (x, y + 4), r)
        edge_col = GOLD if state == "maxed" else border
        edge_w = 4 if state == "maxed" else 3
        if big:   # hexagon for core/mastery nodes
            pts = [(x + math.cos(a) * r * 1.08, y + math.sin(a) * r * 1.08)
                   for a in (math.pi / 6 + i * math.pi / 3 for i in range(6))]
            pygame.draw.polygon(s, fill, pts)
            pygame.draw.polygon(s, edge_col, pts, edge_w)
        else:
            pygame.draw.circle(s, fill, (x, y), r)
            pygame.draw.circle(s, edge_col, (x, y), r, edge_w)
        draw_icon(s, up["icon"], (x, y), r * 0.62, icon)

        if state == "locked":   # little padlock
            lx, ly = x + r * 0.7, y + r * 0.6
            pygame.draw.arc(s, (170, 160, 190), (lx - 6, ly - 12, 12, 14), 0, math.pi, 2)
            pygame.draw.rect(s, (170, 160, 190), (lx - 8, ly - 5, 16, 12), border_radius=3)

        name_img = self.fonts[21].render(up["name"], True, TEXT if state != "locked" else MUTED)
        lv_text = "MAX" if state == "maxed" else (f"{lv}/{up['max']}" if up["max"] else f"Lv {lv}")
        lv_img = self.fonts[18].render(lv_text, True, GOLD if state == "maxed" else MUTED)
        box = pygame.Rect(0, 0, max(name_img.get_width(), lv_img.get_width()) + 12, 36)
        box.midtop = (x, y + r + 6)
        pygame.draw.rect(s, (20, 16, 28), box, border_radius=6)
        s.blit(name_img, name_img.get_rect(midtop=(x, box.y + 3)))
        s.blit(lv_img, lv_img.get_rect(midtop=(x, box.y + 20)))

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
        draw_text(s, f, f"{BRANCHES[up['branch']]['name']} path", 22, color, (p.x + 96, p.y + 50))

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
        if up["requires"]:
            draw_text(s, f, "Requires", 22, MUTED, (p.x + 20, y))
            y += 26
            for req_key, req_lv in up["requires"]:
                ok = w.levels[req_key] >= req_lv
                pygame.draw.circle(s, GOOD if ok else BAD, (p.x + 30, y + 9), 6)
                draw_text(s, f, f"{UPGRADE_BY_KEY[req_key]['name']}  Lv {req_lv}", 24,
                          TEXT if ok else MUTED, (p.x + 44, y))
                y += 26

        btn = self.buy_button
        if up["key"] != self.selected:
            btn.text, btn.enabled = "Click node to select", False
        elif state == "locked":
            btn.text, btn.enabled = "Locked", False
        elif state == "maxed":
            btn.text, btn.enabled = "MAXED", False
        else:
            cost = upgrade_cost(up, lv)
            btn.text = f"Buy  $ {fmt(cost)}"
            btn.enabled = w.gold >= cost
        btn.draw(s, f, mouse)
