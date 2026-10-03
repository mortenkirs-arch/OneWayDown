"""Game simulation: the dig site, miners, mining rules and save data."""
import math
import random
import time

from .blocks import BLOCKS, Block, generate_layer
from .config import BAD, GOLD, GOOD, GRID, TEXT, W
from .effects import Floater, Particle
from .enemies import FIRST_SPAWN_DELAY, Enemy, choose_kind, edge_cell, max_enemies, spawn_delay
from .iso import iso
from .miners import MINER_REGEN, MINER_RESPAWN_SECS, Miner
from .upgrades import (BRANCHES, UPGRADES, click_damage, dynamite_interval, is_maxed, is_unlocked,
                       miner_count, miner_damage, ore_mult, swing_time, upgrade_cost, value_mult,
                       walk_speed)
from .util import fmt

NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class World:
    def __init__(self):
        self.gold = 0.0
        self.depth = 0                     # depth index of the current (top) layer
        self.levels = {u["key"]: 0 for u in UPGRADES}
        self.total_blocks = 0
        self.current = generate_layer(0)
        self.next = generate_layer(1)
        self.miners = []
        self.sync_miners()
        self.rise = 0.0                    # layer-shift animation offset (in blocks)
        self.particles = []
        self.floaters = []
        self.rings = []                    # expanding circle effects [x, y, age, max_r, color]
        self.earn_log = []                 # (time, amount) for $/s estimate
        self.gps_cached = 0.0
        self.tap_timer = 0.0
        self.dynamite_timer = 0.0
        self.enemies = []
        self.enemy_timer = FIRST_SPAWN_DELAY

    # ----- stats ----------------------------------------------------------
    def lv(self, key): return self.levels[key]

    def miner_hit_damage(self):
        team = 1 + 0.03 * self.lv("teamwork") * len(self.miners)
        return miner_damage(self.lv("power")) * team

    def miner_swing_time(self):
        return max(0.1, swing_time(self.lv("speed")) * 0.9 ** self.lv("foreman"))

    def click_hit_damage(self):
        return click_damage(self.lv("click"))

    def gold_per_sec(self):
        now = time.time()
        self.earn_log = [(t, a) for t, a in self.earn_log if now - t < 15]
        if self.earn_log:
            span = max(5.0, now - self.earn_log[0][0])
            self.gps_cached = sum(a for _, a in self.earn_log) / span
        return self.gps_cached

    def sync_miners(self, announce=False):
        while len(self.miners) < miner_count(self.lv("miners")):
            miner = Miner(taken_names={m.name for m in self.miners})
            self.miners.append(miner)
            if announce:
                px, py = self.entity_screen(miner, 60)
                self.floaters.append(Floater(f"{miner.name} joins the crew!", px, py, GOOD, life=2.0, size=24))

    def column_height(self, cx, cy):
        return 2 if (cx, cy) in self.current else 1

    @staticmethod
    def cell_of(x, y):
        return int(min(GRID - 1, max(0, x))), int(min(GRID - 1, max(0, y)))

    def cell_screen(self, cell):
        return iso(cell[0] + 0.5, cell[1] + 0.5, 2 + self.rise)

    def entity_screen(self, e, lift=0):
        """Screen position of a miner/enemy, `lift` pixels above its feet."""
        x, y = iso(e.x, e.y, e.draw_z + self.rise)
        return x, y - lift

    # ----- combat ---------------------------------------------------------
    def nearest_free_miner(self, x, y):
        free = [m for m in self.miners if m.state == "working"]
        return min(free, key=lambda m: (m.x - x) ** 2 + (m.y - y) ** 2, default=None)

    def spawn_enemy(self):
        kind = choose_kind(self.depth)
        if not kind:
            return
        cell = edge_cell()
        enemy = Enemy(kind, self.depth, cell, self.column_height(*cell))
        self.enemies.append(enemy)
        px, py = self.entity_screen(enemy)
        for _ in range(16):
            self.particles.append(Particle(px, py - 30, (110, 84, 60), big=True))
        self.floaters.append(Floater(f"A {enemy.spec['name'].lower()} crawls out!", px, py - 60, BAD,
                                     life=1.8, size=26))

    def grab(self, enemy, miner):
        if enemy.kind == "spider":
            enemy.grab_offset = (0.0, 0.0)          # rides on the miner's head
        else:
            # stand beside the miner on screen (screen-x follows x - y) so the choke is visible
            side = 1 if (enemy.x - miner.x) - (enemy.y - miner.y) >= 0 else -1
            reach = enemy.spec["reach"] * 1.15
            enemy.grab_offset = (side * reach, -side * reach)
            enemy.facing = -side
        enemy.victim = miner
        enemy.state = "attacking"
        miner.state = "grabbed"
        miner.attacker = enemy
        px, py = self.entity_screen(miner, 60)
        self.floaters.append(Floater(f"{miner.name}: HELP!", px, py, BAD, life=1.2, size=26))

    def miner_down(self, miner):
        miner.state = "down"
        miner.respawn = MINER_RESPAWN_SECS
        miner.attacker = None
        miner.target = None
        px, py = self.entity_screen(miner, 30)
        self.floaters.append(Floater(f"{miner.name} is down!", px, py - 20, BAD, life=1.6, size=26))
        for _ in range(12):
            self.particles.append(Particle(px, py, miner.shirt, big=True))

    def respawn_miner(self, miner):
        miner.place_randomly()
        miner.draw_z = self.column_height(*self.cell_of(miner.x, miner.y))
        miner.hp = miner.max_hp
        miner.state = "working"
        px, py = self.entity_screen(miner, 50)
        self.floaters.append(Floater(f"{miner.name} is back to work!", px, py, GOOD, life=1.4, size=22))

    def hit_enemy(self, enemy, dmg):
        if enemy not in self.enemies:
            return
        enemy.hp -= dmg
        enemy.flash = 0.12
        px, py = self.entity_screen(enemy, 22)
        self.rings.append([px, py + 18, 0.0, 30, BAD])
        for _ in range(6):
            self.particles.append(Particle(px, py, (120, 190, 80) if enemy.kind == "zombie" else (90, 60, 120)))
        if enemy.hp <= 0:
            self.kill_enemy(enemy)

    def kill_enemy(self, enemy):
        self.enemies.remove(enemy)
        bounty = enemy.bounty_base * value_mult(self.lv("value"))
        self.gold += bounty
        self.earn_log.append((time.time(), bounty))
        px, py = self.entity_screen(enemy, 22)
        self.floaters.append(Floater(f"+${fmt(bounty)}", px, py - 20, GOLD, size=28))
        self.rings.append([px, py + 18, 0.0, 60, GOOD])
        for _ in range(26):
            self.particles.append(Particle(px, py, random.choice([(120, 190, 80), (70, 110, 50), (200, 60, 60)]),
                                           big=True))
        victim = enemy.victim
        if victim and victim.attacker is enemy:
            victim.state = "working"
            victim.attacker = None
            vx, vy = self.entity_screen(victim, 60)
            self.floaters.append(Floater("Saved!", vx, vy, GOOD, life=1.3, size=28))

    # ----- upgrades -------------------------------------------------------
    def can_buy(self, up):
        return (is_unlocked(up, self.levels) and not is_maxed(up, self.levels)
                and self.gold >= upgrade_cost(up, self.levels[up["key"]]))

    def buy(self, up):
        if not self.can_buy(up):
            return False
        self.gold -= upgrade_cost(up, self.levels[up["key"]])
        self.levels[up["key"]] += 1
        self.sync_miners(announce=True)
        return True

    # ----- mining ---------------------------------------------------------
    def damage(self, cell, dmg, sparks=3):
        """Apply damage to one block. Returns False if the layer changed (stop chaining)."""
        block = self.current.get(cell)
        if not block:
            return True
        block.hp -= dmg
        px, py = self.cell_screen(cell)
        spec = BLOCKS[block.kind]
        for _ in range(sparks):
            self.particles.append(Particle(px, py, spec.get("fleck") or spec["color"]))
        if block.hp <= 0:
            depth = self.depth
            self.break_block(cell, block)
            return depth == self.depth
        return True

    def splash(self, cell, dmg, color):
        targets = [(cell[0] + dx, cell[1] + dy) for dx, dy in NEIGHBOURS]
        depth = self.depth
        for t in targets:
            if self.depth != depth:
                return
            if t in self.current:
                self.damage(t, dmg, sparks=2)
        px, py = self.cell_screen(cell)
        self.rings.append([px, py, 0.0, 70, color])

    def miner_hit(self, cell):
        dmg = self.miner_hit_damage()
        crit = random.random() < 0.05 * self.lv("crit")
        if crit:
            dmg *= 3
            px, py = self.cell_screen(cell)
            self.floaters.append(Floater("CRIT!", px, py - 30, (255, 150, 90), life=0.7, size=22))
        if self.damage(cell, dmg) and crit and self.lv("quake"):
            self.splash(cell, dmg * 0.25 * self.lv("quake"), BRANCHES["tools"]["color"])

    def player_hit(self, cell, sparks=6, ring_color=(255, 255, 255)):
        dmg = self.click_hit_damage()
        px, py = self.cell_screen(cell)
        self.rings.append([px, py, 0.0, 26, ring_color])
        if self.damage(cell, dmg, sparks) and self.lv("shockwave"):
            self.splash(cell, dmg * 0.2 * self.lv("shockwave"), BRANCHES["hands"]["color"])

    def blast(self):
        if not self.current:
            return
        cx, cy = random.choice(list(self.current))
        dmg = self.click_hit_damage() * 10
        px, py = self.cell_screen((cx, cy))
        self.floaters.append(Floater("BOOM!", px, py - 30, (255, 120, 60), life=1.2, size=40))
        self.rings.append([px, py, 0.0, 140, (255, 150, 60)])
        for _ in range(30):
            self.particles.append(Particle(px, py, random.choice([(255, 200, 80), (255, 110, 40), (90, 80, 80)]),
                                           big=True))
        for e in list(self.enemies):   # dynamite hurts enemies caught in the blast too
            if max(abs(e.x - (cx + 0.5)), abs(e.y - (cy + 0.5))) <= 1.6:
                self.hit_enemy(e, dmg)
        depth = self.depth
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if self.depth != depth:
                    return
                self.damage((cx + dx, cy + dy), dmg, sparks=2)

    def break_block(self, cell, block):
        del self.current[cell]
        earned = block.value * value_mult(self.lv("value"))
        px, py = self.cell_screen(cell)
        if random.random() < 0.04 * self.lv("double"):
            earned *= 2
            self.floaters.append(Floater("x2!", px + 26, py - 34, GOOD, size=22))
        if random.random() < 0.02 * self.lv("goldrush"):
            nugget = block.value * value_mult(self.lv("value")) * 25
            earned += nugget
            self.floaters.append(Floater(f"NUGGET! +${fmt(nugget)}", px, py - 50, GOLD, life=1.8, size=30))
            self.rings.append([px, py, 0.0, 90, GOLD])
        self.gold += earned
        self.total_blocks += 1
        self.earn_log.append((time.time(), earned))
        spec = BLOCKS[block.kind]
        for _ in range(14):
            self.particles.append(Particle(px, py, spec["color"], big=True))
            if spec.get("fleck"):
                self.particles.append(Particle(px, py, spec["fleck"], big=True))
        self.floaters.append(Floater(f"+${fmt(earned)}", px, py - 10, GOLD))
        for m in self.miners:
            if m.target == cell:
                m.target = None
        if not self.current:
            self.descend()

    def descend(self):
        self.depth += 1
        self.current = self.next
        self.next = generate_layer(self.depth + 1, ore_mult(self.lv("prospector")))
        self.rise = -1.0
        for m in self.miners:
            m.draw_z += 1
            m.target = None
        for e in self.enemies:
            e.draw_z += 1
        self.floaters.append(Floater(f"Depth {self.depth}m", W / 2, 120, TEXT, life=2.0, size=40))

    def pick_target(self, miner):
        if not self.current:
            return None
        claimed = {m.target for m in self.miners if m is not miner and m.target}
        best, best_d = None, 1e9
        for cell in self.current:
            d = (cell[0] + 0.5 - miner.x) ** 2 + (cell[1] + 0.5 - miner.y) ** 2
            if cell in claimed:
                d += 6
            d += random.random() * 0.3
            if d < best_d:
                best, best_d = cell, d
        return best

    # ----- update ---------------------------------------------------------
    def update(self, dt, combat=True):
        """Advance the simulation. With combat=False enemies freeze and none spawn."""
        self.sync_miners()
        if self.rise < 0:
            self.rise = min(0.0, self.rise + dt * 2.5)
        speed = walk_speed(self.lv("boots"))
        swing = self.miner_swing_time()
        for m in self.miners:
            if m.state == "down":
                m.respawn -= dt
                if m.respawn <= 0:
                    self.respawn_miner(m)
                continue
            if m.state == "grabbed":
                if random.random() < dt * 5:   # panicked sweat
                    px, py = self.entity_screen(m, 36)
                    self.particles.append(Particle(px, py, (150, 200, 255)))
                continue
            m.hp = min(m.max_hp, m.hp + MINER_REGEN * dt)
            if m.target is None or m.target not in self.current:
                m.target = self.pick_target(m)
            m.anim = max(0.0, m.anim - dt * 4)
            if m.target:
                tx, ty = m.target[0] + 0.5, m.target[1] + 0.5
                dx, dy = tx - m.x, ty - m.y
                dist = math.hypot(dx, dy)
                if dist > 0.05:
                    step = min(dist, speed * dt)
                    m.x += dx / dist * step
                    m.y += dy / dist * step
                    m.facing = 1 if (dx - dy) >= 0 else -1
                else:
                    m.swing -= dt
                    if m.swing <= 0:
                        m.swing += swing
                        m.anim = 1.0
                        self.miner_hit(m.target)
            target_z = self.column_height(*self.cell_of(m.x, m.y))
            m.draw_z += (target_z - m.draw_z) * min(1.0, dt * 10)

        if combat:
            for e in list(self.enemies):
                e.update(self, dt)
            if self.depth >= 1 and len(self.enemies) < max_enemies(self.depth):
                self.enemy_timer -= dt
                if self.enemy_timer <= 0:
                    self.enemy_timer = spawn_delay(self.depth)
                    self.spawn_enemy()

        if self.lv("autotap"):
            self.tap_timer += dt * self.lv("autotap")
            while self.tap_timer >= 1 and self.current:
                self.tap_timer -= 1
                self.player_hit(random.choice(list(self.current)), sparks=3,
                                ring_color=BRANCHES["hands"]["color"])
        if self.lv("dynamite"):
            self.dynamite_timer += dt
            if self.dynamite_timer >= dynamite_interval(self.lv("dynamite")):
                self.dynamite_timer = 0.0
                self.blast()

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for f in self.floaters:
            f.update(dt)
        self.floaters = [f for f in self.floaters if f.life > 0]
        for r in self.rings:
            r[2] += dt
        self.rings = [r for r in self.rings if r[2] < 0.4]

    # ----- persistence ----------------------------------------------------
    def to_dict(self):
        pack = lambda layer: [[x, y, b.kind, b.hp] for (x, y), b in layer.items()]
        return dict(gold=self.gold, depth=self.depth, levels=self.levels,
                    total_blocks=self.total_blocks, current=pack(self.current),
                    next=pack(self.next), saved_at=time.time(), gps=self.gold_per_sec(),
                    crew=[m.look() for m in self.miners])

    @classmethod
    def from_dict(cls, d):
        w = cls()
        w.gold = d["gold"]
        w.depth = d["depth"]
        w.levels.update({k: v for k, v in d["levels"].items() if k in w.levels})
        w.total_blocks = d.get("total_blocks", 0)
        w.current = {(x, y): Block(k, w.depth, hp) for x, y, k, hp in d["current"]}
        w.next = {(x, y): Block(k, w.depth + 1, hp) for x, y, k, hp in d["next"]}
        if not w.current:
            w.descend()
        w.miners = []
        w.sync_miners()
        for miner, look in zip(w.miners, d.get("crew", [])):   # older saves have no crew: keep random looks
            miner.apply_look(look)
        w.gps_cached = d.get("gps", 0.0)
        return w
