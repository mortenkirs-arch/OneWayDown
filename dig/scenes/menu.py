"""Main menu."""
import math
import sys
import time

import pygame

from ..blocks import BLOCKS
from ..config import GOLD, H, TEXT, W
from ..iso import draw_cube, origin_at
from ..ui import Button, draw_gold, draw_text
from ..util import fmt, shade
from ..title import Title
from .base import Scene


MENU_DY = (H - 720) // 2   # keep the menu vertically centred on taller windows


class MenuScene(Scene):
    simulate = False

    def __init__(self, game):
        super().__init__(game)
        self.title = None   # the stone "DOWN" title (see dig/title.py)
        self.has_saves = game.latest_slot() is not None   # (refreshed on every visit)
        cx, dy = W // 2 - 160, MENU_DY
        self.buttons = {
            "continue": Button((cx, 330 + dy, 320, 60), "Continue", game.continue_game),
            "new": Button((cx, 405 + dy, 320, 60), "New Game", self.new_game),
            "load": Button((cx, 480 + dy, 320, 60), "Load Game", lambda: game.open_slots("load")),
            "settings": Button((cx, 555 + dy, 320, 60), "Settings", lambda: game.open_settings("menu"),
                               color=(64, 84, 110)),
            "quit": Button((cx, 630 + dy, 320, 60), "Quit", game.quit, color=(120, 60, 70)),
        }
        if sys.platform == "emscripten":   # (in a browser there's nothing to quit to: you just close the tab)
            del self.buttons["quit"]

    def enter(self):
        self.has_saves = self.game.latest_slot() is not None

    def new_game(self):
        """With no saves yet, straight to picking the mode; otherwise pick the slot for it first."""
        if self.has_saves:
            self.game.open_slots("new")
        else:
            self.game.choose_mode(self.game.slots[0])

    def handle(self, event):
        for b in self.buttons.values():
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and self.has_saves:
            self.game.continue_game()

    def draw(self, surf):
        mouse = pygame.mouse.get_pos()
        bob = math.sin(time.time() * 2) * 0.12
        # decorative isometric stacks
        with origin_at((W // 2 + 360, 330 + MENU_DY)):
            for i, k in enumerate(["diamond", "gold", "stone", "dirt"]):
                draw_cube(surf, i % 2, i // 2, 1, BLOCKS[k]["color"], BLOCKS[k].get("fleck"), seed=i)
            draw_cube(surf, 0, 0, 2.3 + bob, BLOCKS["gold"]["color"], BLOCKS["gold"]["fleck"], seed=9)
        with origin_at((W // 2 - 420, 360 + MENU_DY)):
            for i, k in enumerate(["coal", "copper", "stone", "dirt"]):
                draw_cube(surf, i % 2, i // 2, 1, BLOCKS[k]["color"], BLOCKS[k].get("fleck"), seed=i + 20)
            draw_cube(surf, 1, 1, 2.3 - bob, BLOCKS["diamond"]["color"], BLOCKS["diamond"]["fleck"], seed=3)

        if self.title is None:   # (built on first use: it needs the display up)
            self.title = Title(W)
        self.title.draw(surf, W // 2, 34 + MENU_DY, time.time())
        if self.world:
            draw_gold(surf, self.fonts, f"{fmt(self.world.gold)} gold  -  depth {self.world.display_depth}m",
                      26, TEXT, (W // 2, 280 + MENU_DY), "center")
        b = self.buttons
        b["continue"].enabled = b["load"].enabled = self.has_saves
        for btn in b.values():
            btn.draw(surf, self.fonts, mouse)
