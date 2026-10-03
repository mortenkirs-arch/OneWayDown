"""The dig site: isometric board plus HUD."""
import math
import random
import time

import pygame

from ..config import BAD, BOARD_ORIGIN, GOLD, GOLD_HUD_COIN, GRID, H, MUTED, PANEL, TEXT, W
from ..enemies import ENEMY_START_DEPTH, max_enemies
from ..iso import origin_at
from ..render import draw_board, draw_flying_coins, pick_block
from ..sprites import pick_enemy
from ..ui import Button, draw_callout, draw_coin, draw_glow, draw_panel, draw_pointer, draw_text
from ..upgrades import BRANCHES, UPGRADE_BY_KEY, UPGRADES, enemy_hit_floor, next_milestone
from ..util import fmt
from .base import Scene


class PlayScene(Scene):
    combat = True

    def __init__(self, game):
        super().__init__(game)
        self.buttons = [
            Button((W - 360, 16, 170, 46), "Upgrades (U)", lambda: game.open_upgrades("play"), size=26),
            Button((W - 178, 16, 160, 46), "Menu (Esc)", game.to_menu, size=26, color=(70, 64, 90)),
            Button((W - 360, 72, 170, 40), "Crew (C)", game.open_crew, size=24, color=(50, 96, 140)),
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
            elif event.key == pygame.K_c:
                self.game.open_crew()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            enemy = pick_enemy(self.world, event.pos, time.time())
            if enemy:   # enemies take priority over blocks
                self.world.player_hit_enemy(enemy)
                return
            hit = pick_block(self.world, event.pos)
            if hit:
                self.world.player_hit(hit[0], manual=True)

    def draw(self, surf):
        mouse = pygame.mouse.get_pos()
        enemy = pick_enemy(self.world, mouse, time.time())
        block = None if enemy else pick_block(self.world, mouse)
        w = self.world
        if w.shake > 0:   # dynamite screen shake: jolt the whole board for a moment
            amp = w.shake_power * min(1.0, w.shake / 0.25)
            ox, oy = BOARD_ORIGIN
            with origin_at((ox + random.uniform(-amp, amp), oy + random.uniform(-amp, amp))):
                draw_board(surf, w, self.fonts, hover=block, hover_enemy=enemy)
        else:
            draw_board(surf, w, self.fonts, hover=block, hover_enemy=enemy)
        self.draw_hud(surf, mouse)
        draw_flying_coins(surf, w.coins)   # over the HUD, so they visibly drop into the counter
        self.draw_first_hire_guide(surf, w)
        if w.notice:
            self.draw_notice(surf, w)

    def draw_milestone(self, surf, w):
        """Bottom of the top panel: the next depth that unlocks upgrades, and progress towards it."""
        f = self.fonts
        nxt = next_milestone(w.depth)
        if not nxt:
            draw_text(surf, f, "Every upgrade unlocked!", 22, GOLD, (34, 116), "midleft")
            return
        depth, ups = nxt
        names = ", ".join(u["name"] for u in ups[:2]) + (f" +{len(ups) - 2} more" if len(ups) > 2 else "")
        draw_text(surf, f, f"Next unlock at {depth}m: {names}", 22, MUTED, (34, 112), "midleft")
        prev = max([u["depth"] for u in UPGRADES if u["depth"] <= w.depth], default=0)
        layer = 1 - len(w.current) / (GRID * GRID)            # progress through the current layer
        frac = min(1.0, (w.depth - prev + layer) / max(1, depth - prev))
        bar = pygame.Rect(34, 126, 384, 8)
        pygame.draw.rect(surf, (20, 16, 28), bar, border_radius=4)
        pygame.draw.rect(surf, (240, 150, 90), (bar.x, bar.y, int(bar.w * frac), bar.h), border_radius=4)

    def draw_first_hire_guide(self, surf, w):
        """New game, no miners yet: once the first miner is affordable, point at the Upgrades button."""
        if w.lv("miners") > 0 or w.gold < w.cost(UPGRADE_BY_KEY["miners"]):
            return
        t = time.time()
        btn = self.buttons[0].rect
        draw_glow(surf, btn, t)
        draw_pointer(surf, (btn.left - 10, btn.centery), "right", t)
        draw_callout(surf, self.fonts, [("You can afford your first miner!", GOLD),
                                        ("Open Upgrades (U) to hire them", TEXT)],
                     (btn.left - 60, btn.centery + 6), "midright")

    def draw_notice(self, surf, w):
        """Banner when a depth milestone opens up new upgrades."""
        text, left = w.notice
        img = self.fonts[28].render(text, True, GOLD)
        box = img.get_rect(midbottom=(W // 2, H - 64)).inflate(36, 20)
        alpha = int(255 * min(1.0, left / 0.5))
        layer = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*PANEL, 235), layer.get_rect(), border_radius=10)
        pygame.draw.rect(layer, GOLD, layer.get_rect(), 2, border_radius=10)
        layer.blit(img, img.get_rect(center=(box.w // 2, box.h // 2)))
        layer.set_alpha(alpha)
        surf.blit(layer, box)
        draw_text(surf, self.fonts, "Press U to see them", 20, MUTED, (W // 2, box.bottom + 14), "center")

    def draw_hud(self, surf, mouse):
        w = self.world
        f = self.fonts
        draw_panel(surf, pygame.Rect(16, 16, 420, 134))
        self.draw_milestone(surf, w)
        bump = w.gold_bump / 0.18          # 1 the moment a coin lands, easing back to 0
        cx, cy = GOLD_HUD_COIN
        draw_coin(surf, (cx, cy), 17 + 4 * bump)
        color = tuple(min(255, int(c + (255 - c) * 0.6 * bump)) for c in GOLD)
        draw_text(surf, f, fmt(w.gold), 48, color, (cx + 26, cy + 1), "midleft")
        draw_text(surf, f, f"{fmt(w.gold_per_sec())} gold / sec", 24, MUTED, (36, 72))
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
        specialists = sum(1 for m in w.miners if m.role != "miner")
        crew_text = f"Crew: {len(w.miners) - down}/{len(w.miners)}" + (f"  ({down} dead)" if down else "")
        if specialists:
            crew_text += f"  incl. {specialists} specialist{'s' if specialists != 1 else ''}"
        stats = [(crew_text, BAD if down else TEXT),
                 (f"Pick dmg: {fmt(w.miner_hit_damage())}", TEXT),
                 (f"Click dmg: {fmt(w.click_hit_damage())}  (blocks)", TEXT),
                 (f"Monster dmg: {fmt(w.monster_hit_damage())}  (min {enemy_hit_floor(w.lv('executioner')):.0%})",
                  BRANCHES["combat"]["color"]),
                 (f"Blocks mined: {fmt(w.total_blocks)}", TEXT)]
        draw_panel(surf, pygame.Rect(16, H - 167, 330, 151))
        for i, (s, color) in enumerate(stats):
            draw_text(surf, f, s, 24, color, (32, H - 155 + i * 27))

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
