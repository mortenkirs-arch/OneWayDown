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
from ..achievements import ACHIEVEMENTS, TIERS, tier
from ..artifacts import ARTIFACTS, REVEAL_POP_SECS
from ..camp import COLLAPSE_FADE, COLLAPSE_SECS
from ..enemies import ENEMY_START_DEPTH, max_enemies
from ..effects import Floater
from ..icons import draw_icon, draw_padlock
from ..iso import origin_at
from ..biomes import biome_at
from ..render import draw_ambient, draw_board, draw_flying_coins, pick_block, pick_boiler
from ..sprites import pick_enemy
from ..ui import Button, draw_callout, draw_coin, draw_glow, draw_panel, draw_pointer, draw_text, wrap_text
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
            Button((W - 360, 122, 170, 38), "Base Camp (B)", game.open_camp, size=24, color=(120, 86, 50)),
            Button((W - 178, 122, 160, 38), "Achievements (H)", game.open_achievements, size=24,
                   color=(150, 110, 40)),
        ]
        self.banner = None   # [achievement, real time it went up]: the one being announced

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
            elif event.key == pygame.K_b:
                self.game.open_camp()
            elif event.key == pygame.K_h:
                self.game.open_achievements()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.world.reveals and self.reveal_rect().collidepoint(event.pos):
                if self.reveal_close_rect().collidepoint(event.pos):   # only the X closes the found card...
                    self.world.reveals.pop(0)
                return   # ...other clicks on it do nothing, so spam-clicking can't dismiss it unread
            if any(r.collidepoint(event.pos) for r in HUD_PANELS):   # clicks on the HUD aren't play
                return
            if self.world.collapse is not None:   # the shaft's coming down: nothing left to dig or fight
                return
            self.world.combo_click()   # every click counts towards the combo, whatever it lands on
            if "claygolem" in self.world.camp:   # ...and towards Mitts' next leap
                self.world.mitts_click(self.mitts_target(event.pos))
            self.world.combo_held = True   # ...and holding the button keeps it from running down
            if self.world.lv("slam"):   # Charged Slam: holding the button anywhere on the play area charges
                self.charge = time.time()
            if pick_boiler(self.world, event.pos):   # Steam Boiler: vent it once it's full
                if not self.world.vent_boiler():
                    self.world.floaters.append(Floater(f"Pressure {round(100 * self.world.boiler)}%",
                                                       event.pos[0], event.pos[1] - 30, MUTED, life=1.0, size=22))
                return
            cursed = self.world.pick_cursed(event.pos)
            if cursed:   # lifting an Archlich's curse (or freeing someone caged or entranced) comes first
                if cursed.curse > 0:
                    self.world.lift_curse(cursed)
                else:
                    self.world.free_held(cursed)
                return
            enemy = pick_enemy(self.world, event.pos, time.time())
            if enemy:   # enemies take priority over blocks
                self.world.player_hit_enemy(enemy, event.pos)
                self.game.audio.play("hit")   # (blocks: "click")
                return
            pool = self.world.pick_void_pool(event.pos)
            if pool:   # The Void Maw's pools of darkness: a click drives one back
                self.world.dispel_void_pool(pool)
                return
            hit = pick_block(self.world, event.pos)
            if hit:
                self.world.player_hit(hit[0], manual=True)
                self.game.audio.play("click")
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
                            target=pick_enemy(self.world, pos, time.time()), held=held)

    def mitts_target(self, pos):
        """Where Mitts should come down for a click at `pos`: the monster under it, or else the block."""
        enemy = pick_enemy(self.world, pos, time.time())
        if enemy:
            return self.world.cell_of(enemy.x, enemy.y)
        return self.slam_target(pos)

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
        self.draw_achievement_banner(surf, w)
        if w.collapse is not None and w.collapse > COLLAPSE_SECS - COLLAPSE_FADE:   # the dust settles... to black
            fade = pygame.Surface(surf.get_size())
            fade.fill((0, 0, 0))
            fade.set_alpha(int(255 * min(1.0, (w.collapse - (COLLAPSE_SECS - COLLAPSE_FADE)) / COLLAPSE_FADE)))
            surf.blit(fade, (0, 0))

    BANNER_SECS = 4.0   # an achievement's banner stays up this long (less while others are waiting behind it)

    def draw_achievement_banner(self, surf, w):
        """ACHIEVEMENT UNLOCKED: a banner sliding up at the bottom of the screen, one achievement at a time."""
        now = time.time()
        if self.banner:
            key, since = self.banner
            secs = self.BANNER_SECS if not w.achievement_queue else 2.0
            if now - since > secs:
                self.banner = None
        if self.banner is None:
            if not w.achievement_queue:
                return
            self.banner = [w.achievement_queue.pop(0), now]
        key, since = self.banner
        a = ACHIEVEMENTS[key]
        color = TIERS[tier(key)]["color"]
        age = now - since
        secs = self.BANNER_SECS if not w.achievement_queue else 2.0
        slide = min(1.0, age / 0.25, max(0.0, (secs - age) / 0.25))   # in and out
        box = pygame.Rect(0, 0, 460, 70)
        box.midbottom = (W // 2 - 10, H - 18 + int((1 - slide) * 100))   # (clear of the HUD and the hints)
        draw_panel(surf, box)
        pygame.draw.rect(surf, color, box, 2, border_radius=10)
        ic = (box.x + 38, box.centery)
        pygame.draw.circle(surf, tuple(c // 3 for c in color), ic, 24)
        draw_icon(surf, a["icon"], ic, 17, color)
        heading = TIERS[tier(key)]["banner"]
        draw_text(surf, self.fonts, heading, 18, color, (box.x + 74, box.y + 18), "midleft")
        draw_text(surf, self.fonts, a["name"], 28, TEXT, (box.x + 74, box.y + 44), "midleft")

    REVEAL_W = 250   # the found-artifact notification: a slim card down the left side, beside the board

    def reveal_lines(self, art):
        """The notification's text, wrapped to its width: (text, size, colour) per line."""
        f = self.fonts
        inner = self.REVEAL_W - 28
        lines = [(t, 24, art["color"]) for t in wrap_text(f[24], art["name"], inner - 56)]
        lines += [(t, 20, TEXT) for t in wrap_text(f[20], art["bonus"], inner)]
        lines += [(t, 18, MUTED) for t in wrap_text(f[18], art["lore"], inner)]
        return lines

    def reveal_rect(self):
        key = self.world.reveals[0][0]
        lines = self.reveal_lines(ARTIFACTS[key])
        height = 102 + sum(size + 2 for _, size, _ in lines if size != 24) + 40
        return pygame.Rect(16, TOP_PANEL.bottom + 14, self.REVEAL_W, max(150, height))

    def reveal_close_rect(self):
        box = self.reveal_rect()
        return pygame.Rect(box.right - 36, box.top + 8, 28, 28)

    def draw_reveal(self, surf, w, mouse):
        """A found artifact: a notification down the left side - clear of the fight - with its icon, name, what
        it does and a line of lore. It slides in, and stays until its X is clicked."""
        key, shown = w.reveals[0]
        art = ARTIFACTS[key]
        f = self.fonts
        box = self.reveal_rect()
        slide = min(1.0, shown / REVEAL_POP_SECS)
        slide = 1 - (1 - slide) ** 3                              # eases in from off the left edge
        layer = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*PANEL, 245), layer.get_rect(), border_radius=12)
        pygame.draw.rect(layer, art["color"], layer.get_rect(), 3, border_radius=12)
        draw_text(layer, f, "BOSS TROPHY!" if "boss" in art else "ARTIFACT FOUND!", 22, GOLD, (14, 22), "midleft")
        lines = self.reveal_lines(art)
        ic = (36, 66)   # the icon, glowing, beside the name
        glow = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*art["color"], int(60 + 30 * math.sin(time.time() * 4))), (35, 35), 30)
        layer.blit(glow, (ic[0] - 35, ic[1] - 35))
        draw_icon(layer, art["icon"], ic, 18, art["color"])
        y = 44
        for text, size, color in lines:
            x = 70 if size == 24 else 14   # (the name sits beside the icon; the rest uses the full width)
            if size != 24 and y < 102:   # (below the icon)
                y = 102
            draw_text(layer, f, text, size, color, (x, y))
            y += size + 2
        more = len(w.reveals) - 1
        footer = (f"{more} more to see  -  " if more else "") + "see all with A"
        draw_text(layer, f, footer, 18, GOLD if more else MUTED, (box.w - 12, box.h - 12), "bottomright")
        close = self.reveal_close_rect().move(-box.x, -box.y)   # the X, top right
        hot = slide >= 1 and self.reveal_close_rect().collidepoint(mouse)
        pygame.draw.rect(layer, (90, 50, 60) if hot else (56, 46, 72), close, border_radius=7)
        pygame.draw.rect(layer, (255, 150, 150) if hot else PANEL_EDGE, close, 2, border_radius=7)
        cx, cy, d = close.centerx, close.centery, 6
        for a, b in (((cx - d, cy - d), (cx + d, cy + d)), ((cx - d, cy + d), (cx + d, cy - d))):
            pygame.draw.line(layer, (255, 255, 255) if hot else TEXT, a, b, 3)
        surf.blit(layer, (box.x - (1 - slide) * (box.right + 10), box.y))

    def draw_milestone(self, surf, w):
        """Bottom of the top panel: the next depth that unlocks upgrades, and progress towards it."""
        f = self.fonts
        nxt = next_milestone(w.depth)
        if not nxt:
            draw_text(surf, f, "Every upgrade unlocked!", 22, GOLD, (34, 142), "midleft")
            return
        depth, ups = nxt
        names = ", ".join(u["name"] for u in ups[:2]) + (f" +{len(ups) - 2} more" if len(ups) > 2 else "")
        draw_text(surf, f, f"Next unlock at {w.shown(depth)}m: {names}", 22, MUTED, (34, 138), "midleft")
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
        tip = w.combat_tip()
        if not tip:
            return
        clicks, affordable = tip
        t = time.time()
        btn = self.buttons[0]
        draw_glow(surf, btn.rect, t)
        crew_bottom = self.buttons[2].rect.bottom   # (below the right-hand buttons, clear of the boss bar)
        names = ", ".join(u["name"] for u in affordable[:2]) + (f" +{len(affordable) - 2} more" if len(affordable) > 2 else "")
        draw_callout(surf, self.fonts, [("The Zombie King is tough!", BAD),
                                        (f"At this rate it takes ~{clicks} clicks to bring down.", TEXT),
                                        ("Combat upgrades you can afford now:", TEXT),
                                        (f"Upgrades (U)  >  Combat:  {names}", GOLD),
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
        left = max(0, math.ceil(self.world.boss_time_limit() - boss.fight_time))
        hint = "It's coming..." if boss.state == "emerging" else self.boss_tip(boss)
        room = 2 * (cx - TOP_PANEL.right) - 24   # (between the top-left panel and the buttons)
        size = next((n for n in (20, 18, 16) if f[n].size(hint)[0] <= room), 16)
        draw_text(surf, f, hint, size, MUTED, (cx, 84), "center")
        if boss.state != "emerging":
            draw_text(surf, f, f"retreats in {left}s", 18, BAD if left <= 15 else MUTED, (cx, 104), "center")

    def boss_tip(self, boss):
        """What to do about this boss right now."""
        w = self.world
        held = {m.held["kind"] for m in w.miners if getattr(m, "held", None)}
        if "cage" in held:
            return "Click the caged crew member - three blows break the ribs!"
        if "trance" in held:
            return "Click the entranced crew member to snap them out of it!"
        if getattr(boss, "gaze", None):
            return f"Its eye has fixed on {boss.gaze[0].name} - strike the eye to break its gaze!"
        if any(getattr(m, "pulled", None) for m in w.miners):
            return "Silk lash - she's reeling someone in to her slam!"
        if boss.kind == "slimeking" and boss.slam_at and boss.windup > 0:
            return "He's bouncing over to belly-flop on your crew!"
        if boss.kind == "zombieking":
            if boss.enraged:
                return "ENRAGED - he charges at the crew and slams much faster!"
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
            return "Click him!"
        if boss.kind == "lich":
            if any(m.curse > 0 for m in w.miners):
                return "Click the cursed crew member to lift the curse!"
            shield = round(100 * (1 - boss.dmg_taken))
            if shield:
                return f"His wisps shield him ({shield}% less damage) - kill them!"
            return "Click him!  He raises the dead to fight for him"
        if boss.kind == "greatbat":
            if boss.slam_at:
                return "It's diving at your crew!"
            return "It dives on whoever it marks; its screech stuns and its wings blow the crew back"
        if boss.kind == "bonetyrant":
            if boss.mode == "pile":
                return "Smash the bones before they pull themselves together!"
            if boss.mode in ("stride", "volley"):
                return "It's hurling bones at your crew - chase it down and hit it!"
            return "After each slam it backs off to throw bones - and it won't stay down the first time"
        if boss.kind == "slimeking":
            if boss.mode == "split":
                left = sum(1 for c in boss.chunks if c in w.enemies)
                return f"{left} chunk{'s' if left != 1 else ''} left - every one of them slams!"
            return "At half health he bursts into 8 chunks - and every one of them slams"
        if boss.kind == "voidmaw":
            if boss.inhale is not None:
                return "It's inhaling - strike its open eye to choke it!"
            if w.void_pools:
                return "Its pools eat at your crew - click them away!"
            return "Only its open eye feels a blow - and when it inhales, strike the eye"
        return "Click it!"

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
        draw_text(surf, f, f"Depth  {w.display_depth}m", 34, TEXT, (420, 30), "topright")
        draw_text(surf, f, f"{len(w.current)}/{GRID * GRID} left", 24, MUTED, (420, 72), "topright")
        camp = self.buttons[4]
        locked = not w.expedition and not w.camp_ready   # (no camp until The Void Maw has fallen once)
        camp.text = "Camp - 100m" if locked else "Base Camp (B)"
        camp.color = (64, 60, 72) if locked else (120, 86, 50)
        for b in self.buttons:
            b.draw(surf, f, mouse)
        if locked:   # a padlock on it: there's something down there to unlock
            draw_padlock(surf, (camp.rect.x + 22, camp.rect.centery), 9, (200, 190, 150))
        affordable = sum(1 for u in UPGRADES if w.can_buy(u))
        if affordable:   # (upgrades you can afford get a count; new artifacts don't - you closed their card)
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

        boss = w.boss()
        if boss:
            self.draw_boss_bar(surf, boss)
        elif w.depth >= ENEMY_START_DEPTH and w.collapse is None and w.lv("miners"):
            # (no waves once the shaft's coming down - nor before you've hired a miner for them to bother)
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
