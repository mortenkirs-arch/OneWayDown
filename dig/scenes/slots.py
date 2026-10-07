"""The save slots: pick a save to load, or one to start a new game in (replacing what's there, after a second click)."""
import json
import os
import time

import pygame

from ..biomes import biome_at
from ..config import GOLD, H, MUTED, PANEL, PANEL_EDGE, TEXT, W
from ..ui import Button, draw_gold, draw_text
from ..util import fmt, shade
from .base import Scene

SLOT_W, SLOT_H, SLOT_GAP = 640, 104, 18


def slot_summary(path):
    """What's in a save file, for its card: depth, gold, time played and when it was saved. None if it's empty
    (or unreadable)."""
    try:
        with open(path) as f:
            data = json.load(f)
        return dict(depth=data["depth"], gold=data["gold"], clock=data.get("clock", 0.0),
                    saved=os.path.getmtime(path))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def ago(when):
    secs = max(0, time.time() - when)
    for size, unit in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if secs >= size:
            n = int(secs // size)
            return f"{n} {unit}{'s' if n != 1 else ''} ago"
    return "just now"


def played(secs):
    hours, mins = int(secs // 3600), int(secs % 3600 // 60)
    return f"{hours}h {mins:02d}m played" if hours else f"{mins} min played"


class SlotScene(Scene):
    simulate = False   # the game waits while you're here

    def __init__(self, game):
        super().__init__(game)
        self.mode = "load"       # "load" | "new"
        self.return_to = "menu"  # (so the menu music keeps playing)
        self.summaries = []
        self.confirm = None      # the slot a new game would replace, after one click
        self.back_button = Button((W // 2 - 80, 0, 160, 50), "< Back", lambda: game.switch("menu"),
                                  size=28, color=(70, 64, 90))

    def enter(self):
        self.summaries = [slot_summary(p) for p in self.game.slots]   # (read once, not every frame)
        self.confirm = None

    def rects(self):
        top = H // 2 - (len(self.game.slots) * (SLOT_H + SLOT_GAP)) // 2 + 20
        return [pygame.Rect(W // 2 - SLOT_W // 2, top + i * (SLOT_H + SLOT_GAP), SLOT_W, SLOT_H)
                for i in range(len(self.game.slots))]

    def latest(self):
        saved = [(s["saved"], i) for i, s in enumerate(self.summaries) if s]
        return max(saved)[1] if saved else None

    def pick(self, i):
        path = self.game.slots[i]
        if self.mode == "load":
            if self.summaries[i]:
                self.game.play_slot(path)
            return
        if self.summaries[i] and self.confirm != i:   # an existing save: ask before replacing it
            self.confirm = i
            return
        self.game.new_game(path)

    def handle(self, event):
        if self.back_button.handle(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.rects()):
                if rect.collidepoint(event.pos):
                    self.pick(i)
                    return
            self.confirm = None
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.switch("menu")

    def draw(self, s):
        f = self.fonts
        mouse = pygame.mouse.get_pos()
        rects = self.rects()
        title, hint = (("LOAD GAME", "Pick a save to carry on with") if self.mode == "load" else
                       ("NEW GAME", "Pick a save slot for the new game"))
        draw_text(s, f, title, 60, TEXT, (W // 2, rects[0].top - 86), "center")
        draw_text(s, f, hint, 26, MUTED, (W // 2, rects[0].top - 40), "center")
        latest = self.latest()
        for i, (rect, info) in enumerate(zip(rects, self.summaries)):
            usable = info is not None or self.mode == "new"
            hover = usable and rect.collidepoint(mouse)
            replacing = self.confirm == i
            fill = (110, 50, 56) if replacing else shade(PANEL, 1.3 if hover else 1.0)
            pygame.draw.rect(s, fill, rect, border_radius=12)
            pygame.draw.rect(s, GOLD if hover or replacing else PANEL_EDGE, rect, 2, border_radius=12)
            draw_text(s, f, f"Save {i + 1}", 34, TEXT if usable else MUTED, (rect.x + 24, rect.y + 18))
            if i == latest:
                draw_text(s, f, "latest", 22, GOLD, (rect.x + 26, rect.y + 56))
            x = rect.x + 170
            if info is None:
                draw_text(s, f, "Start a new game here" if self.mode == "new" else "Empty", 28,
                          TEXT if self.mode == "new" else MUTED, (x, rect.centery), "midleft")
                continue
            if replacing:
                draw_text(s, f, "Click again to replace this save", 30, TEXT, (x, rect.centery), "midleft")
                continue
            biome = biome_at(info["depth"])
            draw_text(s, f, f"Depth {info['depth']}m", 30, TEXT, (x, rect.y + 18))
            draw_text(s, f, biome["name"], 24, biome["accent"], (x + 170, rect.y + 23))
            draw_gold(s, f, fmt(info["gold"]), 26, GOLD, (x, rect.y + 58))
            draw_text(s, f, f"{played(info['clock'])}  -  saved {ago(info['saved'])}", 22, MUTED,
                      (x + 170, rect.y + 62))
        self.back_button.rect.top = rects[-1].bottom + 36
        self.back_button.draw(s, f, mouse)
