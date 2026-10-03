"""The dig site: isometric board plus HUD."""
import pygame

from ..config import BAD, GOLD, GRID, H, MUTED, TEXT, W
from ..render import draw_board, pick_block
from ..ui import Button, draw_panel, draw_text
from ..upgrades import UPGRADES
from ..util import fmt
from .base import Scene


class PlayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.buttons = [
            Button((W - 360, 16, 170, 46), "Upgrades (U)", lambda: game.open_upgrades("play"), size=26),
            Button((W - 178, 16, 160, 46), "Menu (Esc)", game.to_menu, size=26, color=(70, 64, 90)),
        ]

    def handle(self, event):
        for b in self.buttons:
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.to_menu()
            elif event.key == pygame.K_u:
                self.game.open_upgrades("play")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = pick_block(self.world, event.pos)
            if hit:
                self.world.player_hit(hit[0])

    def draw(self, surf):
        mouse = pygame.mouse.get_pos()
        draw_board(surf, self.world, self.fonts, hover=pick_block(self.world, mouse))
        self.draw_hud(surf, mouse)

    def draw_hud(self, surf, mouse):
        w = self.world
        f = self.fonts
        draw_panel(surf, pygame.Rect(16, 16, 420, 96))
        draw_text(surf, f, f"$ {fmt(w.gold)}", 48, GOLD, (34, 26))
        draw_text(surf, f, f"{fmt(w.gold_per_sec())} / sec", 24, MUTED, (36, 72))
        draw_text(surf, f, f"Depth  {w.depth}m", 34, TEXT, (420, 30), "topright")
        draw_text(surf, f, f"{len(w.current)}/{GRID * GRID} left", 24, MUTED, (420, 72), "topright")
        for b in self.buttons:
            b.draw(surf, f, mouse)
        affordable = sum(1 for u in UPGRADES if w.can_buy(u))
        if affordable:
            badge = (self.buttons[0].rect.right - 4, self.buttons[0].rect.top + 2)
            pygame.draw.circle(surf, BAD, badge, 12)
            draw_text(surf, f, str(affordable), 22, TEXT, badge, "center")
        stats = [f"Miners: {len(w.miners)}",
                 f"Pick dmg: {fmt(w.miner_hit_damage())}",
                 f"Click dmg: {fmt(w.click_hit_damage())}",
                 f"Blocks mined: {fmt(w.total_blocks)}"]
        draw_panel(surf, pygame.Rect(16, H - 140, 260, 124))
        for i, s in enumerate(stats):
            draw_text(surf, f, s, 24, TEXT, (32, H - 128 + i * 27))
        draw_text(surf, f, "Click blocks (top or sides) to mine them yourself!", 24, MUTED,
                  (W - 20, H - 20), "bottomright")
