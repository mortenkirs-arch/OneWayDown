"""Upgrade menus: five tabs (Crew, Tools, Hands, Fortune, Combat), each its own branching tree."""
import math
import random
import time

import pygame

from ..config import GOLD, GOOD, BAD, H, MUTED, TEXT, W
from ..effects import CoinFly, Particle
from ..icons import draw_icon
from ..render import draw_flying_coins
from ..ui import Button, draw_callout, draw_glow, draw_gold, draw_panel, draw_pointer, draw_text, wrap_text
from ..upgrades import (BRANCHES, TABS, UPGRADES, UPGRADES_BY_TAB, UPGRADE_BY_KEY, is_maxed, is_unlocked,
                        tree_requires)
from ..util import fmt, shade
from .base import Scene

# Layout scales with the window: the detail panel hugs the right edge, the tree fills the rest.
PANEL_RECT = pygame.Rect(W - 400, 104, 376, H - 164)
TREE_LEFT, TREE_RIGHT = 24, PANEL_RECT.x - 16
TIER_GAP = 107 + (H - 720) // 5
TREE_TIER_Y = [176 + i * TIER_GAP for i in range(5)]
NODE_HIT_RADIUS = 36
TAB_H, TAB_GAP, TAB_Y = 46, 8, 84
TAB_W = (TREE_RIGHT - TREE_LEFT - 4 * TAB_GAP) // 5


def tree_col_x(col):
    """Columns 0..3 spread across the tree area (most trees use 0.5 / 1.5 / 2.5)."""
    centre = (TREE_LEFT + TREE_RIGHT) / 2
    spacing = min(300, (TREE_RIGHT - TREE_LEFT) / 4.2)
    return centre + (col - 1.5) * spacing


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
        self.tab = TABS[0]
        # each tab remembers its own selected node; starts on the tab's root
        roots = {tab: [u for u in UPGRADES_BY_TAB[tab] if not tree_requires(u)] for tab in TABS}
        # each tab opens on its earliest root (Hands: Golden Touch, until Power Gloves opens at 2m)
        self.selected_in = {tab: min(roots[tab], key=lambda u: u["depth"])["key"] for tab in TABS}
        self.particles = []
        self.coins = []                  # spent coins flying from the gold counter to an upgrade
        self.bursts = []                 # [seconds until the coins land, x, y, colour]
        self.counter_coin = (W - 200, 46)
        self.node_pos = {u["key"]: (tree_col_x(u["pos"][0]), TREE_TIER_Y[u["pos"][1]]) for u in UPGRADES}
        self.tab_rects = {tab: pygame.Rect(TREE_LEFT + i * (TAB_W + TAB_GAP), TAB_Y, TAB_W, TAB_H)
                          for i, tab in enumerate(TABS)}
        p = PANEL_RECT
        self.buy_button = Button((p.x + 20, p.bottom - 72, p.w - 40, 54), "", self.buy_selected,
                                 size=30, color=(60, 130, 80))
        self.back_button = Button((24, H - 50, 130, 40), "< Back", self.close, size=26, color=(70, 64, 90))

    @property
    def selected(self):
        return self.selected_in[self.tab]

    @selected.setter
    def selected(self, key):
        self.selected_in[self.tab] = key

    # ----- actions --------------------------------------------------------
    def close(self):
        self.game.switch(self.return_to)

    def switch_tab(self, tab):
        self.tab = tab
        self.particles = []
        self.coins = []
        self.bursts = []

    def buy(self, up):
        """Spend: coins pour out of the gold counter into the upgrade, which bursts when they land."""
        if not self.world.buy(up):
            return
        x, y = self.node_pos[up["key"]]
        for i in range(12):
            # low arc: the counter is at the top of the screen, so a high one would fly off it
            self.coins.append(CoinFly(self.counter_coin, (x, y), delay=i * 0.025, duration=0.45, size=7,
                                      lift=(0, 18)))
        self.bursts.append([0.5, x, y, BRANCHES[up["branch"]]["color"]])

    def burst(self, x, y, color):
        for _ in range(24):
            self.particles.append(Particle(x, y, random.choice([color, GOLD, (255, 255, 255)]), big=True))

    def buy_selected(self):
        self.buy(UPGRADE_BY_KEY[self.selected])

    def node_under_mouse(self, pos):
        for up in UPGRADES_BY_TAB[self.tab]:
            x, y = self.node_pos[up["key"]]
            if math.hypot(pos[0] - x, pos[1] - y) <= NODE_HIT_RADIUS:
                return up["key"]
        return None

    def tab_under_mouse(self, pos):
        return next((tab for tab, rect in self.tab_rects.items() if rect.collidepoint(pos)), None)

    def affordable_in(self, tab):
        return sum(1 for u in UPGRADES_BY_TAB[tab] if self.world.can_buy(u))

    def node_state(self, up):
        lv = self.world.levels
        if not self.world.available(up):
            return "locked"
        if is_maxed(up, lv):
            return "maxed"
        return "owned" if lv[up["key"]] > 0 else "available"

    # ----- scene hooks ----------------------------------------------------
    def handle(self, event):
        if self.back_button.handle(event) or self.buy_button.handle(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            tab = self.tab_under_mouse(event.pos)
            if tab and event.button == 1:
                self.switch_tab(tab)
                return
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
            elif pygame.K_1 <= event.key <= pygame.K_1 + len(TABS) - 1:
                self.switch_tab(TABS[event.key - pygame.K_1])
            elif event.key == pygame.K_TAB:
                step = -1 if event.mod & pygame.KMOD_SHIFT else 1
                self.switch_tab(TABS[(TABS.index(self.tab) + step) % len(TABS)])

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for c in self.coins:
            c.update(dt)
        self.coins = [c for c in self.coins if not c.arrived]
        for b in self.bursts:   # the upgrade bursts as the spent coins land in it
            b[0] -= dt
            if b[0] <= 0:
                self.burst(*b[1:])
        self.bursts = [b for b in self.bursts if b[0] > 0]

    def draw(self, s):
        if self.tab == "combat":   # (the first boss's "get some combat upgrades" tip has done its job)
            self.world.combat_tip_done = True
        w = self.world
        f = self.fonts
        mouse = pygame.mouse.get_pos()
        t = time.time()
        hovered = self.node_under_mouse(mouse)

        title = draw_text(s, f, "UPGRADES", 50, TEXT, (24, 22))
        badge = pygame.Rect(title.right + 18, 26, 112, 30)   # pause indicator next to the title
        pygame.draw.rect(s, (60, 52, 30), badge, border_radius=8)
        pygame.draw.rect(s, GOLD, badge, 2, border_radius=8)
        for dx in (-41, -35):
            pygame.draw.rect(s, GOLD, (badge.centerx + dx, badge.centery - 7, 4, 14))
        draw_text(s, f, "PAUSED", 24, GOLD, (badge.centerx + 10, badge.centery), "center")
        draw_text(s, f, BRANCHES[self.tab]["blurb"], 24, shade(BRANCHES[self.tab]["color"], 0.9),
                  (badge.right + 20, badge.centery), "midleft")
        gold_rect = draw_gold(s, f, fmt(w.gold), 44, GOLD, (W - 30, 22), "topright")
        self.counter_coin = (gold_rect.x + 13, gold_rect.centery - 1)   # where spent coins fly from
        draw_text(s, f, f"{fmt(w.gold_per_sec())} gold / sec", 22, MUTED,
                  (gold_rect.left - 14, gold_rect.centery), "midright")

        self.draw_tabs(s, mouse)
        tab_ups = UPGRADES_BY_TAB[self.tab]
        self.draw_edges(s, t, tab_ups)
        for up in tab_ups:
            self.draw_node(s, up, hovered == up["key"], self.selected == up["key"], t)
        for p in self.particles:
            pygame.draw.rect(s, p.color, (int(p.x), int(p.y), p.size, p.size))

        self.draw_panel(s, UPGRADE_BY_KEY[hovered or self.selected], mouse)
        self.back_button.draw(s, f, mouse)
        draw_text(s, f, "Click: select   Right-click / Enter: buy   1-5 / Tab: switch menu", 20, MUTED,
                  (PANEL_RECT.centerx, PANEL_RECT.bottom + 22), "center")
        draw_flying_coins(s, self.coins)
        self.draw_first_hire_guide(s, t)

    def draw_first_hire_guide(self, s, t):
        """No miners yet and one is affordable: lead the way to Crew > Hire Miner > Buy."""
        w = self.world
        hire = UPGRADE_BY_KEY["miners"]
        if w.lv("miners") > 0 or not w.can_buy(hire):
            return
        f = self.fonts
        if self.tab != "crew":
            tab = self.tab_rects["crew"]
            draw_glow(s, tab, t)
            draw_pointer(s, (tab.centerx, tab.bottom + 6), "up", t)
            draw_callout(s, f, [("Your first miner is in the Crew menu", GOLD)], (tab.centerx + 40, tab.bottom + 52),
                         "midtop")
            return
        x, y = self.node_pos["miners"]
        draw_pointer(s, (x - 46, y), "right", t)
        if self.selected != "miners":
            draw_callout(s, f, [("Click Hire Miner", GOLD)], (x - 100, y), "midright")
            return
        draw_callout(s, f, [("Hire your first miner!", GOLD), ("Press Buy", TEXT)], (x - 100, y), "midright")
        draw_glow(s, self.buy_button.rect, t)

    # ----- drawing helpers ------------------------------------------------
    def draw_tabs(self, s, mouse):
        f = self.fonts
        pygame.draw.line(s, (70, 60, 92), (TREE_LEFT, TAB_Y + TAB_H), (TREE_RIGHT, TAB_Y + TAB_H), 2)
        for i, tab in enumerate(TABS):
            rect = self.tab_rects[tab]
            color = BRANCHES[tab]["color"]
            active = tab == self.tab
            hover = rect.collidepoint(mouse)
            if active:
                body = shade(color, 0.45)
            else:
                body = (48, 42, 62) if hover else (34, 30, 46)
            pygame.draw.rect(s, body, rect.inflate(0, 6 if active else 0).move(0, -3 if active else 0),
                             border_top_left_radius=10, border_top_right_radius=10)
            pygame.draw.rect(s, color, (rect.x + 8, rect.y + (-3 if active else 0), rect.w - 16, 4),
                             border_radius=2)
            label = f"{i + 1}  {BRANCHES[tab]['name']}"
            draw_text(s, f, label, 28, TEXT if active else shade(color, 0.9), rect.center, "center")
            if any(u["key"] in self.world.new_unlocks for u in UPGRADES_BY_TAB[tab]):
                pill = pygame.Rect(rect.x + 6, rect.y - 9, 38, 16)
                pygame.draw.rect(s, GOLD, pill, border_radius=8)
                draw_text(s, f, "NEW", 16, (60, 40, 10), pill.center, "center")
            count = self.affordable_in(tab)
            if count:
                badge = (rect.right - 12, rect.y + 6)
                pygame.draw.circle(s, BAD, badge, 11)
                draw_text(s, f, str(count), 20, TEXT, badge, "center")

    def draw_edges(self, s, t, ups):
        for up in ups:
            child = self.node_pos[up["key"]]
            color = BRANCHES[up["branch"]]["color"]
            open_ = self.world.available(up)   # the upgrade this path leads to can actually be bought
            for req_key, req_lv in tree_requires(up):
                pts = bezier(self.node_pos[req_key], child)
                have = self.world.levels[req_key]
                if have >= req_lv and not open_:
                    # this requirement is done, but the upgrade is still locked (depth milestone or
                    # another prerequisite): a lit line, but no glow or flowing dots
                    pygame.draw.lines(s, shade(color, 0.75), False, pts, 3)
                elif have >= req_lv:
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
        big = len(tree_requires(up)) != 1   # roots and merge points are hexagons
        r = (34 if big else 28) + (3 if hovered else 0)
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
        depth_locked = self.world.depth < up["depth"]
        if depth_locked:   # milestone not reached yet: show the depth to dig to instead of the level
            lv_text, lv_color = f"at {up['depth']}m", (240, 150, 90)
        else:
            lv_text = "MAX" if state == "maxed" else (f"{lv}/{up['max']}" if up["max"] else f"Lv {lv}")
            lv_color = GOLD if state == "maxed" else MUTED
        lv_img = self.fonts[18].render(lv_text, True, lv_color)
        box = pygame.Rect(0, 0, max(name_img.get_width(), lv_img.get_width()) + 12, 36)
        box.midtop = (x, y + r + 6)
        pygame.draw.rect(s, (20, 16, 28), box, border_radius=6)
        s.blit(name_img, name_img.get_rect(midtop=(x, box.y + 3)))
        s.blit(lv_img, lv_img.get_rect(midtop=(x, box.y + 20)))
        if up["key"] in self.world.new_unlocks:   # just opened up by a depth milestone
            if hovered or selected:
                self.world.new_unlocks.discard(up["key"])
            else:
                pill = pygame.Rect(0, 0, 42, 18)
                pill.midleft = (x + r - 6, y - r + 4)   # top-right of the node, clear of the node above
                pygame.draw.rect(s, GOLD, pill, border_radius=9)
                draw_text(s, self.fonts, "NEW", 18, (60, 40, 10), pill.center, "center")

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
        draw_text(s, f, f"{BRANCHES[up['branch']]['name']} menu", 22, color, (p.x + 96, p.y + 50))

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
        needs = [(f"{UPGRADE_BY_KEY[k]['name']}  Lv {n}", w.levels[k] >= n) for k, n in up["requires"]]
        if up["depth"]:
            needs.append((f"Reach depth {up['depth']}m  (you: {w.depth}m)", w.depth >= up["depth"]))
        if needs:
            draw_text(s, f, "Requires", 22, MUTED, (p.x + 20, y))
            y += 26
            for text, ok in needs:
                pygame.draw.circle(s, GOOD if ok else BAD, (p.x + 30, y + 9), 6)
                draw_text(s, f, text, 24, TEXT if ok else MUTED, (p.x + 44, y))
                y += 26

        btn = self.buy_button
        btn.gold = None
        if up["key"] != self.selected:
            btn.text, btn.enabled = "Click node to select", False
        elif state == "locked":
            btn.text, btn.enabled = "Locked", False
        elif state == "maxed":
            btn.text, btn.enabled = "MAXED", False
        else:
            cost = w.cost(up)
            btn.text, btn.gold = "Buy", fmt(cost)
            btn.enabled = w.gold >= cost
        btn.draw(s, f, mouse)
