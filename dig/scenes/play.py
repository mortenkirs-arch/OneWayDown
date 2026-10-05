"""The dig site: isometric board plus HUD."""
import math
import random
import time

import pygame

from ..config import BAD, BOARD_ORIGIN, GOLD, GOLD_HUD_COIN, GRID, H, MUTED, PANEL, PANEL_EDGE, TEXT, W
from ..world import COMBO_WINDOW

SLAM_MIN_HOLD = 0.35    # hold at least this long for a slam (a quick click is just a click)
SLAM_FULL_HOLD = 0.9    # ...and this much longer for a full-power slam
TOP_PANEL = pygame.Rect(16, 16, 420, 160)
HUD_PANELS = [TOP_PANEL, pygame.Rect(16, H - 167, 330, 151)]   # top-left and bottom-left
from ..artifacts import ARTIFACTS, REVEAL_POP_SECS
from ..enemies import BOSS_TIME_LIMIT, ENEMY_START_DEPTH, max_enemies
from ..icons import draw_icon
from ..iso import origin_at
from ..biomes import biome_at
from ..render import draw_ambient, draw_board, draw_flying_coins, pick_block
from ..sprites import pick_enemy
from ..ui import Button, draw_callout, draw_coin, draw_glow, draw_panel, draw_pointer, draw_text
from ..upgrades import BRANCHES, UPGRADE_BY_KEY, UPGRADES, enemy_hit_floor, next_milestone
from ..util import fmt
from .base import Scene


class PlayScene(Scene):
    combat = True

    def __init__(self, game):
        super().__init__(game)
        self.charge = None   # time pressed while charging a slam
        self.buttons = [
            Button((W - 360, 16, 170, 46), "Upgrades (U)", lambda: game.open_upgrades("play"), size=26),
            Button((W - 178, 16, 160, 46), "Menu (Esc)", game.to_menu, size=26, color=(70, 64, 90)),
            Button((W - 360, 72, 170, 40), "Crew (C)", game.open_crew, size=24, color=(50, 96, 140)),
            Button((W - 178, 72, 160, 40), "Artifacts (A)", game.open_artifacts, size=24, color=(110, 70, 150)),
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
            elif event.key == pygame.K_a:
                self.game.open_artifacts()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.world.reveals and self.reveal_rect().collidepoint(event.pos):
                if self.reveal_close_rect().collidepoint(event.pos):   # only the X closes the found card...
                    self.world.reveals.pop(0)
                return   # ...other clicks on it do nothing, so spam-clicking can't dismiss it unread
            if any(r.collidepoint(event.pos) for r in HUD_PANELS):   # clicks on the HUD aren't play
                return
            self.world.combo_click()   # every click counts towards the combo, whatever it lands on
            self.world.combo_held = True   # ...and holding the button keeps it from running down
            if self.world.lv("slam"):   # Charged Slam: holding the button anywhere on the play area charges
                self.charge = time.time()
            cursed = self.world.pick_cursed(event.pos)
            if cursed:   # lifting a Lich's curse comes first
                self.world.lift_curse(cursed)
                return
            enemy = pick_enemy(self.world, event.pos, time.time())
            if enemy:   # enemies take priority over blocks
                self.world.player_hit_enemy(enemy)
                return
            hit = pick_block(self.world, event.pos)
            if hit:
                self.world.player_hit(hit[0], manual=True)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.world.combo_held = False
            if self.charge:
                self.release_slam(event.pos)

    def release_slam(self, pos):
        """Charged Slam: letting go after holding long enough slams the block (and monster) under the cursor."""
        held = time.time() - self.charge
        self.charge = None
        if held < SLAM_MIN_HOLD:
            return
        cell = self.slam_target(pos)
        if cell:
            self.world.slam(cell, min(1.0, (held - SLAM_MIN_HOLD) / SLAM_FULL_HOLD),
                            target=pick_enemy(self.world, pos, time.time()))

    def slam_target(self, pos):
        """The block under the cursor, or failing that the block nearest to it on screen."""
        hit = pick_block(self.world, pos)
        if hit:
            return hit[0]
        if not self.world.current:
            return None
        return min(self.world.current, key=lambda c: math.dist(pos, self.world.cell_screen(c)))

    def draw(self, surf):
        mouse = pygame.mouse.get_pos()
        enemy = pick_enemy(self.world, mouse, time.time())
        block = None if enemy else pick_block(self.world, mouse)
        w = self.world
        draw_ambient(surf, w, time.time())   # the biome's drifting embers / sparkles / dust
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
        self.draw_combat_tip(surf, w)
        self.draw_charge_and_combo(surf, w, mouse)
        if w.notice:
            self.draw_notice(surf, w)
        if w.reveals:
            self.draw_reveal(surf, w, mouse)

    @staticmethod
    def reveal_rect():
        return pygame.Rect(0, 0, 560, 170).move(W // 2 - 280, 150)

    def reveal_close_rect(self):
        box = self.reveal_rect()
        return pygame.Rect(box.right - 40, box.top + 8, 32, 32)

    def draw_reveal(self, surf, w, mouse):
        """The card that pops up when an artifact is found: icon, name, what it does, a line of lore."""
        key, shown = w.reveals[0]
        art = ARTIFACTS[key]
        f = self.fonts
        box = self.reveal_rect()
        grow = min(1.0, shown / REVEAL_POP_SECS)              # pops in, then stays until the X is clicked
        layer = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*PANEL, 245), layer.get_rect(), border_radius=14)
        pygame.draw.rect(layer, art["color"], layer.get_rect(), 3, border_radius=14)
        trophy = "boss" in art
        draw_text(layer, f, "BOSS TROPHY!" if trophy else "ARTIFACT FOUND!", 24, GOLD, (box.w // 2, 20), "center")
        t = time.time()
        ic = (70, 96)
        glow = pygame.Surface((110, 110), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*art["color"], int(60 + 30 * math.sin(t * 4))), (55, 55), 50)
        layer.blit(glow, (ic[0] - 55, ic[1] - 55))
        draw_icon(layer, art["icon"], ic, 30, art["color"])
        draw_text(layer, f, art["name"], 32, art["color"], (130, 58), "midleft")
        draw_text(layer, f, art["bonus"], 24, TEXT, (130, 94), "midleft")
        draw_text(layer, f, art["lore"], 20, MUTED, (130, 126), "midleft")
        more = len(w.reveals) - 1
        footer = (f"{more} more to see  -  " if more else "") + "see them all with A"
        draw_text(layer, f, footer, 18, GOLD if more else MUTED, (box.w - 14, box.h - 12), "bottomright")
        close = self.reveal_close_rect().move(-box.x, -box.y)   # the X, top right
        hot = grow >= 1 and self.reveal_close_rect().collidepoint(mouse)
        pygame.draw.rect(layer, (90, 50, 60) if hot else (56, 46, 72), close, border_radius=8)
        pygame.draw.rect(layer, (255, 150, 150) if hot else PANEL_EDGE, close, 2, border_radius=8)
        cx, cy, d = close.centerx, close.centery, 7
        for a, b in (((cx - d, cy - d), (cx + d, cy + d)), ((cx - d, cy + d), (cx + d, cy - d))):
            pygame.draw.line(layer, (255, 255, 255) if hot else TEXT, a, b, 3)
        if grow < 1:
            layer = pygame.transform.smoothscale(layer, (max(1, int(box.w * grow)), max(1, int(box.h * grow))))
        surf.blit(layer, layer.get_rect(center=box.center))

    def draw_milestone(self, surf, w):
        """Bottom of the top panel: the next depth that unlocks upgrades, and progress towards it."""
        f = self.fonts
        nxt = next_milestone(w.depth)
        if not nxt:
            draw_text(surf, f, "Every upgrade unlocked!", 22, GOLD, (34, 142), "midleft")
            return
        depth, ups = nxt
        names = ", ".join(u["name"] for u in ups[:2]) + (f" +{len(ups) - 2} more" if len(ups) > 2 else "")
        draw_text(surf, f, f"Next unlock at {depth}m: {names}", 22, MUTED, (34, 138), "midleft")
        prev = max([u["depth"] for u in UPGRADES if u["depth"] <= w.depth], default=0)
        layer = 1 - len(w.current) / (GRID * GRID)            # progress through the current layer
        frac = min(1.0, (w.depth - prev + layer) / max(1, depth - prev))
        bar = pygame.Rect(34, 152, 384, 8)
        pygame.draw.rect(surf, (20, 16, 28), bar, border_radius=4)
        pygame.draw.rect(surf, (240, 150, 90), (bar.x, bar.y, int(bar.w * frac), bar.h), border_radius=4)

    def enter(self):
        self.charge = None   # time pressed while charging a slam
        if self.world:
            self.world.combo_held = False   # (the button may have been let go elsewhere)

    def draw_charge_and_combo(self, surf, w, mouse):
        """Charged Slam's growing ring at the cursor, and the Combo Clicks counter beside it."""
        t = time.time()
        mx, my = mouse
        if getattr(self, "charge", None):
            held = t - self.charge
            if held > 0.12:
                frac = min(1.0, max(0.0, (held - SLAM_MIN_HOLD) / SLAM_FULL_HOLD))
                full = frac >= 1.0
                rad = 12 + 26 * min(1.0, held / (SLAM_MIN_HOLD + SLAM_FULL_HOLD))
                color = (255, 255, 255) if full and int(t * 12) % 2 else (200, 150, 255)
                pygame.draw.circle(surf, color, (mx, my), int(rad), 3)
                if held >= SLAM_MIN_HOLD:
                    pygame.draw.arc(surf, (255, 230, 255), (mx - rad - 6, my - rad - 6, 2 * rad + 12, 2 * rad + 12),
                                    math.pi / 2, math.pi / 2 + math.tau * frac, 4)
                if full:
                    draw_text(surf, self.fonts, "SLAM!", 26, (240, 210, 255), (mx, my - rad - 16), "center")
        if w.lv("combo") and w.combo >= 3:
            heat = min(1.0, w.combo / 20)
            color = tuple(int(a + (b - a) * heat) for a, b in zip((255, 220, 120), (255, 110, 60)))
            r = draw_text(surf, self.fonts, f"x{w.combo_mult():.2f}", 30 + int(8 * heat), color,
                          (mx + 22, my + 10), "topleft")
            draw_text(surf, self.fonts, f"{w.combo} combo", 18, MUTED, (r.left, r.bottom), "topleft")
            bar = pygame.Rect(r.left, r.bottom + 16, 60, 4)   # time left before the combo drops
            pygame.draw.rect(surf, (20, 16, 28), bar)
            pygame.draw.rect(surf, color, (bar.x, bar.y, int(bar.w * w.combo_timer / COMBO_WINDOW), bar.h))

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

    def draw_combat_tip(self, surf, w):
        """The first boss is a wall without combat upgrades: glow the Upgrades button and say where to look."""
        if not w.combat_tip():
            return
        t = time.time()
        btn = self.buttons[0]
        draw_glow(surf, btn.rect, t)
        crew_bottom = self.buttons[2].rect.bottom   # (below the right-hand buttons, clear of the boss bar)
        draw_callout(surf, self.fonts, [("The Zombie King is tough!", BAD),
                                        ("Combat upgrades bring it down faster:", TEXT),
                                        ("Upgrades (U)  >  Combat:  Monster Slayer, Executioner", GOLD),
                                        ("(the fight waits while you shop)", MUTED)],
                     (W - 16, crew_bottom + 14), "topright", size=22)

    def draw_notice(self, surf, w):
        """Banner at the bottom: new upgrades at a depth milestone, or news of a boss."""
        text, left, *hint = w.notice   # (an optional third item replaces the "Press U" hint)
        img = self.fonts[28].render(text, True, GOLD)
        box = img.get_rect(midbottom=(W // 2, H - 64)).inflate(36, 20)
        alpha = int(255 * min(1.0, left / 0.5))
        layer = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*PANEL, 235), layer.get_rect(), border_radius=10)
        pygame.draw.rect(layer, GOLD, layer.get_rect(), 2, border_radius=10)
        layer.blit(img, img.get_rect(center=(box.w // 2, box.h // 2)))
        layer.set_alpha(alpha)
        surf.blit(layer, box)
        hint = hint[0] if hint else "Press U to see them"
        if hint:
            draw_text(surf, self.fonts, hint, 20, MUTED, (W // 2, box.bottom + 14), "center")

    def draw_boss_bar(self, surf, boss):
        """Top of the screen during a boss fight: its name, a big health bar and the time left."""
        f = self.fonts
        cx = W // 2 + 30
        pulse = 0.8 + 0.2 * math.sin(time.time() * 5)
        draw_text(surf, f, boss.spec["name"].upper(), 34, tuple(int(c * pulse) for c in BAD), (cx, 30), "center")
        bar = pygame.Rect(0, 0, 420, 18)
        bar.center = (cx, 60)
        pygame.draw.rect(surf, (20, 16, 24), bar.inflate(4, 4), border_radius=6)
        frac = max(0.0, boss.hp / boss.max_hp)
        pygame.draw.rect(surf, BAD, (bar.x, bar.y, int(bar.w * frac), bar.h), border_radius=5)
        pygame.draw.rect(surf, (255, 200, 190), bar.inflate(4, 4), 2, border_radius=6)
        left = max(0, math.ceil(BOSS_TIME_LIMIT - boss.fight_time))
        hint = "It's coming..." if boss.state == "emerging" else self.boss_tip(boss)
        room = 2 * (cx - TOP_PANEL.right) - 24   # (between the top-left panel and the buttons)
        size = next((n for n in (20, 18, 16) if f[n].size(hint)[0] <= room), 16)
        draw_text(surf, f, hint, size, MUTED, (cx, 84), "center")
        if boss.state != "emerging":
            draw_text(surf, f, f"retreats in {left}s", 18, BAD if left <= 15 else MUTED, (cx, 104), "center")

    def boss_tip(self, boss):
        """What to do about this boss right now."""
        w = self.world
        if boss.kind == "zombieking":
            if boss.enraged:
                return "ENRAGED - he winds up and slams much faster!"
            return "Rallied zombies are tough - kill them away from him, or lure him off"
        if boss.kind == "broodmother":
            if any(e.kind == "eggsac" for e in w.enemies):
                return "Break the egg sacs before they hatch!"
            return "Her slams leave webs that slow your crew"
        if boss.kind == "vampirelord":
            if boss.mode == "bats":
                return "He's a swarm of bats - get ready for where he lands!"
            if boss.mode == "bite":
                return f"He's feeding on {boss.victim.name} - hit him hard to make him let go!"
            return "Click him!  Stay out of the red when he slams"
        if boss.kind == "lich":
            if any(m.curse > 0 for m in w.miners):
                return "Click the cursed crew member to lift the curse!"
            shield = round(100 * (1 - boss.dmg_taken))
            if shield:
                return f"His wisps shield him ({shield}% less damage) - kill them!"
            return "Click him!  Stay out of the red when he slams"
        if boss.kind == "greatbat":
            if boss.slam_at:
                return "It's diving - get out of the red!"
            return "It dives on whoever it marks, and its screech stuns the crew nearby"
        if boss.kind == "bonetyrant":
            if boss.mode == "pile":
                return "Smash the bones before they pull themselves together!"
            return "It hurls bones at the crew furthest away - and it won't stay down the first time"
        return "Click it!  Stay out of the red when it slams"

    def draw_hud(self, surf, mouse):
        w = self.world
        f = self.fonts
        draw_panel(surf, TOP_PANEL)
        biome = biome_at(w.depth)
        draw_text(surf, f, biome["name"], 22, biome["accent"], (34, 108), "midleft")
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
        for count, button in ((affordable, self.buttons[0]), (len(w.new_artifacts), self.buttons[3])):
            if count:
                badge = (button.rect.right - 4, button.rect.top + 2)
                pygame.draw.circle(surf, BAD, badge, 12)
                draw_text(surf, f, str(count), 22, TEXT, badge, "center")

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

        boss = w.boss()
        if boss:
            self.draw_boss_bar(surf, boss)
        elif w.depth >= ENEMY_START_DEPTH:
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
