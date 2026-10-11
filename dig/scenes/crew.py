"""Crew page: lifetime stats for every miner on the crew, plus the graveyard of the fallen."""
import math
from collections import Counter

import pygame

from ..config import BAD, GOLD, GOOD, H, MUTED, PANEL, PANEL_EDGE, SCALE, TEXT, W
from ..icons import draw_icon
from ..miners import MAX_LEVEL, level_mult, xp_to_next
from ..sprites import HI_VIS, draw_portrait
from ..ui import Button, draw_gold, draw_text
from ..upgrades import BRANCHES
from ..util import fmt, shade
from .base import Scene

TABS = [("crew", "Active crew"), ("graveyard", "Graveyard")]
ROLE_BADGES = {"foreman": ("FOREMAN", HI_VIS), "driller": ("DRILLER", (235, 160, 70)),
               "guard": ("GUARD", (120, 150, 220)), "demolitionist": ("DEMOLITION", (225, 80, 70)),
               "medic": ("MEDIC", (120, 220, 140)), "hero": ("HERO", (250, 205, 70)),
               "engineer": ("ENGINEER", (240, 140, 70)), "archer": ("ARCHER", (160, 210, 120)),
               "taxman": ("TAX", (110, 210, 120)), "claygolem": ("GOLEM", (200, 140, 240))}
TAB_W, TAB_H, TAB_Y = 230, 46, 84
LIST_TOP, LIST_BOTTOM = 196, H - 72
ROW_H = 62
LEFT, RIGHT = 24, W - 24
CREW_COLOR = BRANCHES["crew"]["color"]
GRAVE_COLOR = (150, 150, 165)

# (sort key, header for the crew tab, header for the graveyard tab, x centre at 1280 wide)
COLUMNS = [(key, a, b, round(x * SCALE)) for key, a, b, x in [
    ("blocks", "Blocks mined", "Blocks mined", 600),
    ("gold", "Gold earned", "Gold earned", 735),
    ("monsters", "Monsters", "Monsters", 860),
    ("saved", "Times saved", "Times saved", 975),
    ("time", "On the job", "Lasted", 1085),
    ("depth", "Joined at", "Died at", 1190),
]]


def fmt_time(secs):
    secs = int(max(0, secs))
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60:02d}s"
    return f"{secs // 3600}h {secs % 3600 // 60:02d}m"


class CrewScene(Scene):
    simulate = False   # like the upgrades, browsing the crew pauses the game

    def __init__(self, game):
        super().__init__(game)
        self.return_to = "play"
        self.tab = "crew"
        self.scroll = {tab: 0 for tab, _ in TABS}
        self.sort = {"crew": (None, True), "graveyard": (None, True)}   # (column, descending)
        self.tab_rects = {tab: pygame.Rect(LEFT + i * (TAB_W + 8), TAB_Y, TAB_W, TAB_H)
                          for i, (tab, _) in enumerate(TABS)}
        self.back_button = Button((LEFT, H - 54, 130, 40), "< Back", self.close, size=26, color=(70, 64, 90))

    # ----- data -----------------------------------------------------------
    def rows(self):
        w = self.world
        if self.tab == "crew":
            rows = [dict(look={**m.look(), "role": m.role}, name=m.name, stats=m.stats, miner=m, order=i,
                         role=m.role, level=m.level, xp=m.xp,
                         time=w.clock - m.stats["hired_clock"], depth=m.stats["hired_depth"])
                    for i, m in enumerate(w.miners)]
        else:
            rows = [dict(look=g, name=g["name"], stats=g["stats"], killer=g["killer"], order=i,
                         role=g.get("role", "miner"), level=g.get("level", 1), xp=g.get("xp", 0.0),
                         time=g["died_clock"] - g["stats"]["hired_clock"], depth=g["died_depth"])
                    for i, g in enumerate(w.graveyard)]
            rows.reverse()   # most recent first by default
        col, desc = self.sort[self.tab]
        if col:
            rows.sort(key=lambda r: self.value(r, col), reverse=desc)
        if self.tab == "crew":   # the foreman heads the list, then the specialists, then the miners
            order = {"hero": 0, "engineer": 0, "archer": 0, "taxman": 0, "claygolem": 0,   # (camp people first)
                     "foreman": 1, "medic": 2, "guard": 3, "demolitionist": 4, "driller": 5}
            rows.sort(key=lambda r: order.get(r["role"], 6))
        return rows

    @staticmethod
    def value(row, col):
        if col in ("time", "depth"):
            return row[col]
        return row["stats"][col]

    def list_height(self):
        return len(self.rows()) * ROW_H

    def max_scroll(self):
        return max(0, self.list_height() - (LIST_BOTTOM - LIST_TOP))

    # ----- actions --------------------------------------------------------
    def close(self):
        self.game.switch(self.return_to)

    def handle(self, event):
        if self.back_button.handle(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab, rect in self.tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.tab = tab
                    return
            if LIST_TOP - 30 <= event.pos[1] < LIST_TOP:   # click a column header to sort by it
                for key, _, _, x in COLUMNS:
                    if abs(event.pos[0] - x) < 60:
                        col, desc = self.sort[self.tab]
                        self.sort[self.tab] = (key, not desc if col == key else True)
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll[self.tab] = max(0, min(self.max_scroll(), self.scroll[self.tab] - event.y * 40))
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_c):
                self.close()
            elif event.key == pygame.K_TAB:
                self.tab = "graveyard" if self.tab == "crew" else "crew"

    # ----- drawing --------------------------------------------------------
    def draw(self, s):
        f = self.fonts
        mouse = pygame.mouse.get_pos()
        title = draw_text(s, f, "CREW", 50, TEXT, (LEFT, 22))
        badge = pygame.Rect(title.right + 18, 26, 112, 30)
        pygame.draw.rect(s, (60, 52, 30), badge, border_radius=8)
        pygame.draw.rect(s, GOLD, badge, 2, border_radius=8)
        for dx in (-41, -35):
            pygame.draw.rect(s, GOLD, (badge.centerx + dx, badge.centery - 7, 4, 14))
        draw_text(s, f, "PAUSED", 24, GOLD, (badge.centerx + 10, badge.centery), "center")
        self.scroll[self.tab] = min(self.scroll[self.tab], self.max_scroll())

        self.draw_tabs(s, mouse)
        self.draw_summary(s)
        rows = self.rows()
        if rows:
            self.draw_header(s)
            self.draw_rows(s, rows, mouse)
        else:
            draw_text(s, f, "No miners have died yet. Keep it that way!", 30, MUTED,
                      (W // 2, (LIST_TOP + LIST_BOTTOM) // 2), "center")
        self.back_button.draw(s, f, mouse)
        draw_text(s, f, "Click a column to sort   Mouse wheel: scroll   Tab: switch   C / Esc: back", 20, MUTED,
                  (RIGHT, H - 34), "midright")

    def draw_tabs(self, s, mouse):
        pygame.draw.line(s, (70, 60, 92), (LEFT, TAB_Y + TAB_H), (RIGHT, TAB_Y + TAB_H), 2)
        counts = {"crew": len(self.world.miners), "graveyard": len(self.world.graveyard)}
        for tab, label in TABS:
            rect = self.tab_rects[tab]
            color = CREW_COLOR if tab == "crew" else GRAVE_COLOR
            active = tab == self.tab
            body = shade(color, 0.45) if active else ((48, 42, 62) if rect.collidepoint(mouse) else (34, 30, 46))
            pygame.draw.rect(s, body, rect.inflate(0, 6 if active else 0).move(0, -3 if active else 0),
                             border_top_left_radius=10, border_top_right_radius=10)
            pygame.draw.rect(s, color, (rect.x + 8, rect.y + (-3 if active else 0), rect.w - 16, 4), border_radius=2)
            draw_text(s, self.fonts, f"{label} ({counts[tab]})", 28, TEXT if active else shade(color, 0.95),
                      rect.center, "center")

    def draw_summary(self, s):
        f = self.fonts
        y = LIST_TOP - 52
        if self.tab == "crew":
            miners = self.world.miners
            stats = [m.stats for m in miners]
            text = (f"{len(miners)} miners   {fmt(sum(st['blocks'] for st in stats))} blocks mined   "
                    f"{sum(st['monsters'] for st in stats)} monsters fought off   earned")
            r = draw_text(s, f, text, 24, MUTED, (LEFT + 4, y), "midleft")
            draw_gold(s, f, fmt(sum(st["gold"] for st in stats)), 24, GOLD, (r.right + 8, y), "midleft")
        else:
            graves = self.world.graveyard
            if not graves:
                return
            killers = Counter(g["killer"] for g in graves).most_common(1)[0]
            text = (f"{len(graves)} fallen   deadliest foe: {killers[0]} ({killers[1]})   "
                    f"the departed earned")
            r = draw_text(s, f, text, 24, MUTED, (LEFT + 4, y), "midleft")
            draw_gold(s, f, fmt(sum(g["stats"]["gold"] for g in graves)), 24, GOLD, (r.right + 8, y), "midleft")

    def draw_header(self, s):
        f = self.fonts
        y = LIST_TOP - 16
        col, desc = self.sort[self.tab]
        draw_text(s, f, "Miner", 22, MUTED, (100, y), "midleft")
        draw_text(s, f, "Status" if self.tab == "crew" else "Fate", 22, MUTED, (300, y), "midleft")
        for key, crew_label, grave_label, x in COLUMNS:
            label = crew_label if self.tab == "crew" else grave_label
            active = key == col
            r = draw_text(s, f, label, 22, TEXT if active else MUTED, (x, y), "center")
            if active:   # little sort arrow
                ax, ay = r.right + 8, y
                pts = [(ax - 4, ay - 2), (ax + 4, ay - 2), (ax, ay + 3)] if desc else \
                      [(ax - 4, ay + 2), (ax + 4, ay + 2), (ax, ay - 3)]
                pygame.draw.polygon(s, TEXT, pts)
        pygame.draw.line(s, (70, 60, 92), (LEFT, LIST_TOP - 3), (RIGHT, LIST_TOP - 3), 1)

    def draw_rows(self, s, rows, mouse):
        f = self.fonts
        dead = self.tab == "graveyard"
        best_gold = max(r["stats"]["gold"] for r in rows)
        area = pygame.Rect(LEFT, LIST_TOP, RIGHT - LEFT, LIST_BOTTOM - LIST_TOP)
        old_clip = s.get_clip()
        s.set_clip(area)
        y0 = LIST_TOP - self.scroll[self.tab]
        for i, row in enumerate(rows):
            rect = pygame.Rect(LEFT, y0 + i * ROW_H, RIGHT - LEFT - 14, ROW_H - 4)
            if rect.bottom < LIST_TOP or rect.top > LIST_BOTTOM:
                continue
            hover = rect.collidepoint(mouse) and area.collidepoint(mouse)
            pygame.draw.rect(s, (46, 40, 62) if hover else PANEL, rect, border_radius=8)
            pygame.draw.rect(s, PANEL_EDGE, rect, 1, border_radius=8)
            fallen = dead or row.get("miner") is not None and row["miner"].state == "down"
            draw_portrait(s, f, row["look"], (rect.x + 38, rect.centery - 2), dead=fallen,
                          pick_level=self.world.lv("diamond"))
            name = draw_text(s, f, row["name"], 28, MUTED if dead else TEXT, (100, rect.centery - 10), "midleft")
            self.draw_level(s, row, rect, dead)
            tag_right = name.right
            if row["role"] in ROLE_BADGES:   # role badge after the name
                text, color = ROLE_BADGES[row["role"]]
                label = f[16].render(text, True, (30, 20, 10))
                pill = pygame.Rect(name.right + 8, name.centery - 8, label.get_width() + 14, 16)
                pygame.draw.rect(s, shade(color, 0.6) if dead else color, pill, border_radius=8)
                s.blit(label, label.get_rect(center=pill.center))
                tag_right = pill.right
            if row["stats"]["gold"] == best_gold and best_gold > 0 and len(rows) > 1:   # top earner
                draw_icon(s, "crown", (tag_right + 16, name.centery - 1), 9, GOLD)
            self.draw_status(s, row, rect)
            st = row["stats"]
            # the foreman doesn't dig: show the orders they've barked in the blocks column instead
            if row["role"] == "foreman":
                work = f"{st.get('orders', 0)} orders"
            elif row["role"] in ("guard", "medic"):
                work = "-"
            else:
                work = fmt(st["blocks"])
            cells = [work, None, str(st["monsters"]), str(st["saved"]), fmt_time(row["time"]), f"{row['depth']}m"]
            for (key, _, _, x), text in zip(COLUMNS, cells):
                if key == "gold":
                    draw_gold(s, f, fmt(st["gold"]), 26, GOLD if not dead else shade(GOLD, 0.7),
                              (x, rect.centery), "center")
                else:
                    draw_text(s, f, text, 26, MUTED if dead else TEXT, (x, rect.centery), "center")
        s.set_clip(old_clip)
        if self.max_scroll():   # scrollbar
            track = pygame.Rect(RIGHT - 8, LIST_TOP, 6, area.h)
            pygame.draw.rect(s, (40, 34, 54), track, border_radius=3)
            frac = area.h / self.list_height()
            thumb = pygame.Rect(track.x, track.y + (track.h - track.h * frac) * self.scroll[self.tab] / self.max_scroll(),
                                6, max(24, track.h * frac))
            pygame.draw.rect(s, (120, 108, 150), thumb, border_radius=3)

    def draw_level(self, s, row, rect, dead):
        """Under the name: experience level, and (for the living) a bar of xp towards the next one."""
        f = self.fonts
        level = row["level"]
        y = rect.centery + 15
        maxed = level >= MAX_LEVEL
        color = shade(GOLD, 0.7) if dead else GOLD
        label = draw_text(s, f, "MASTER" if maxed else f"Lv {level}", 20, color, (100, y), "midleft")
        if dead or maxed:
            tip = f"x{level_mult(level):.2f} at their job" if not dead else ("reached master" if maxed else "")
            draw_text(s, f, tip, 18, MUTED, (label.right + 8, y), "midleft")
            return
        bar = pygame.Rect(label.right + 8, y - 3, 70, 6)
        pygame.draw.rect(s, (20, 16, 24), bar.inflate(2, 2), border_radius=3)
        frac = min(1.0, row["xp"] / xp_to_next(level))
        pygame.draw.rect(s, GOLD, (bar.x, bar.y, int(bar.w * frac), bar.h), border_radius=3)
        draw_text(s, f, f"x{level_mult(level):.2f}", 18, MUTED, (bar.right + 6, y), "midleft")

    def draw_status(self, s, row, rect):
        f = self.fonts
        x, y = 300, rect.centery
        if self.tab == "graveyard":
            draw_text(s, f, f"Killed by a {row['killer']}", 24, shade(BAD, 0.9), (x, y - 9), "midleft")
            draw_text(s, f, f"joined at {row['stats']['hired_depth']}m", 20, MUTED, (x, y + 11), "midleft")
            return
        m = row["miner"]
        if m.state == "down":
            text = (f"Knocked out - back up in {math.ceil(m.respawn)}s" if getattr(m, "ko", False)
                    else f"Dead - replacement in {math.ceil(m.respawn)}s")
            draw_text(s, f, text, 24, MUTED, (x, y - 9), "midleft")
            return
        if m.state == "grabbed":
            label, color = f"Under attack by a {m.attacker.spec['name']}!" if m.attacker else "Under attack!", BAD
        elif m.is_foreman:
            label = f"Supervising {m.inspecting.name}" if m.inspecting else "Barking orders"
            color = HI_VIS
        elif m.role == "guard":
            fighting = m.task == "fighting" and m.goal in self.world.enemies
            label = f"Fighting a {m.goal.spec['name']}" if fighting else "On patrol"
            color = ROLE_BADGES["guard"][1]
        elif m.role == "demolitionist":
            label = {"walking": "Heading to a tough block", "planting": "Planting a charge!",
                     "taking cover": "Taking cover"}.get(m.task, "Waiting for the next job")
            color = ROLE_BADGES["demolitionist"][1]
        elif m.role == "driller":
            label, color = "Drilling", ROLE_BADGES["driller"][1]
        elif m.role in ("hero", "engineer", "archer", "taxman", "claygolem"):
            busy = {"hero": {"rescuing": "To the rescue!"}, "engineer": {"forging": "Rigging a pick",
                                                                          "heading": "Off to rig a pick"},
                    "archer": {"shooting": "Shooting"}, "taxman": {"visiting": f"Off to collect from {m.goal.name}" if m.task == "visiting" and m.goal else "Doing the rounds",
                               "collecting": "Collecting taxes", "waiting": "Waiting for someone to tax",
                               "auditing": "Taxing a monster"},
                    "claygolem": {"leaping": "Leaping in to slam!"}}[m.role]
            idle = {"hero": "Digging", "engineer": "Looking for a pick to rig", "archer": "Keeping watch",
                    "taxman": "Doing the rounds", "claygolem": "Waiting on your clicks"}[m.role]
            label, color = busy.get(m.task, idle), ROLE_BADGES[m.role][1]
        elif m.role == "medic":
            patient = m.goal if m.task == "healing" and m.goal in self.world.miners else None
            label = f"Patching up {patient.name}" if patient else "On call"
            color = ROLE_BADGES["medic"][1]
        else:
            label, color = "Working", GOOD
        draw_text(s, f, label, 24, color, (x, y - 9), "midleft")
        bar = pygame.Rect(x, y + 8, 150, 8)
        frac = max(0.0, m.hp / m.max_hp)
        pygame.draw.rect(s, (20, 16, 24), bar.inflate(2, 2), border_radius=3)
        pygame.draw.rect(s, GOOD, (bar.x, bar.y, int(bar.w * frac), bar.h), border_radius=3)   # crew: always green
        draw_text(s, f, f"{m.hp:.0f}/{m.max_hp:.0f} hp", 20, MUTED, (bar.right + 10, bar.centery), "midleft")
