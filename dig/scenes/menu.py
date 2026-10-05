"""Main menu."""
import math
import time

import pygame

from ..blocks import BLOCKS
from ..config import GOLD, H, TEXT, W
from ..iso import draw_cube, origin_at
from ..ui import Button, draw_gold, draw_text
from ..util import fmt, shade
from .base import Scene


MENU_DY = (H - 720) // 2   # keep the menu vertically centred on taller windows


class MenuScene(Scene):
    simulate = False

    def __init__(self, game):
        super().__init__(game)
        self.confirm_new = False
        cx, dy = W // 2 - 160, MENU_DY
        self.buttons = {
            "continue": Button((cx, 330 + dy, 320, 60), "Continue", lambda: game.switch("play")),
            "new": Button((cx, 405 + dy, 320, 60), "New Game", self.new_game),
            "upgrades": Button((cx, 480 + dy, 320, 60), "Upgrades", lambda: game.open_upgrades("menu")),
            "settings": Button((cx, 555 + dy, 320, 60), "Settings", lambda: game.open_settings("menu"),
                               color=(64, 84, 110)),
            "quit": Button((cx, 630 + dy, 320, 60), "Quit", game.quit, color=(120, 60, 70)),
        }

    def enter(self):
        self.confirm_new = False

    def new_game(self):
        if self.world and not self.confirm_new:
            self.confirm_new = True
            return
        self.game.new_game()

    def handle(self, event):
        for key, b in self.buttons.items():
            if b.handle(event):
                if key != "new":
                    self.confirm_new = False
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and self.world:
            self.game.switch("play")

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

        title = "THE ONLY WAY IS DOWN"
        draw_text(surf, self.fonts, title, 84, shade(GOLD, 0.45), (W // 2 + 4, 164 + MENU_DY), "center")
        draw_text(surf, self.fonts, title, 84, GOLD, (W // 2, 160 + MENU_DY), "center")
        if self.world:
            draw_gold(surf, self.fonts, f"{fmt(self.world.gold)} gold  -  depth {self.world.depth}m",
                      26, TEXT, (W // 2, 280 + MENU_DY), "center")
        b = self.buttons
        b["continue"].enabled = self.world is not None
        b["new"].text = "Click again to confirm" if self.confirm_new else "New Game"
        b["new"].size = 26 if self.confirm_new else 30
        b["new"].color = (150, 70, 70) if self.confirm_new else (86, 70, 130)
        for btn in b.values():
            btn.draw(surf, self.fonts, mouse)
