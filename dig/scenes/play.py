"""The dig site: isometric board plus HUD."""
import math
import time

import pygame

from ..config import BAD, GOLD, GRID, H, MUTED, TEXT, W
from ..enemies import ENEMY_START_DEPTH, max_enemies
from ..render import draw_board, pick_block
from ..sprites import pick_enemy
from ..ui import Button, draw_panel, draw_text
from ..upgrades import UPGRADES
from ..util import fmt
from .base import Scene


class PlayScene(Scene):
    combat = True

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
            enemy = pick_enemy(self.world, event.pos, time.time())
            if enemy:   # enemies take priority over blocks
                self.world.hit_enemy(enemy, self.world.click_hit_damage())
                return
            hit = pick_block(self.world, event.pos)
            if hit:
                self.world.player_hit(hit[0])

    def draw(self, surf):
        mouse = pygame.mouse.get_pos()
        enemy = pick_enemy(self.world, mouse, time.time())
        block = None if enemy else pick_block(self.world, mouse)
        draw_board(surf, self.world, self.fonts, hover=block, hover_enemy=enemy)
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

        down = sum(1 for m in w.miners if m.state == "down")
        stats = [(f"Miners: {len(w.miners) - down}/{len(w.miners)}" + (f"  ({down} down)" if down else ""),
                  BAD if down else TEXT),
                 (f"Pick dmg: {fmt(w.miner_hit_damage())}", TEXT),
                 (f"Click dmg: {fmt(w.click_hit_damage())}", TEXT),
                 (f"Blocks mined: {fmt(w.total_blocks)}", TEXT)]
        draw_panel(surf, pygame.Rect(16, H - 140, 300, 124))
        for i, (s, color) in enumerate(stats):
            draw_text(surf, f, s, 24, color, (32, H - 128 + i * 27))

        if w.depth >= ENEMY_START_DEPTH:
            secs = math.ceil(w.enemy_timer)
            incoming = max_enemies(w.depth) - len(w.enemies)
            wave = f"next wave in {secs}s" + (f" (+{incoming})" if incoming > 0 else " (at max)")
            if w.enemies:
                grabbed = sum(1 for m in w.miners if m.state == "grabbed")
                if grabbed:
                    title = f"{grabbed} MINER{'S' if grabbed > 1 else ''} UNDER ATTACK!"
                elif w.announcement:
                    title = w.announcement[0]
                else:
                    title = "ENEMIES IN THE MINE!"
                pulse = 0.75 + 0.25 * math.sin(time.time() * 8)
                draw_text(surf, f, title, 36, tuple(int(c * pulse) for c in BAD), (W // 2 + 30, 36), "center")
                draw_text(surf, f, f"Click them to save your crew  -  {wave}", 22, MUTED, (W // 2 + 30, 64), "center")
            else:
                color = BAD if secs <= 5 else MUTED
                draw_text(surf, f, wave[0].upper() + wave[1:], 28, color, (W // 2 + 30, 40), "center")
        draw_text(surf, f, "Click blocks (top or sides) to mine them yourself!", 24, MUTED,
                  (W - 20, H - 20), "bottomright")
