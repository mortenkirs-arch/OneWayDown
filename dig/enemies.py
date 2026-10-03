"""Enemies that crawl out of the dig site and attack miners.

Enemies only act while the player is on the dig site (see Scene.combat), so nothing
can kill the crew while you are browsing menus.
"""
import math
import random

from .config import GRID

# hp/bounty scale with depth; dps is against miners (MINER_MAX_HP = 10)
ENEMY_TYPES = {
    "zombie": dict(name="Zombie", hp=14, speed=0.55, dps=1.3, bounty=12, min_depth=1, weight=3,
                   reach=0.3, skin=(118, 168, 92), shirt=(70, 88, 130)),
    "spider": dict(name="Cave Spider", hp=7, speed=1.5, dps=2.4, bounty=8, min_depth=6, weight=2,
                   reach=0.25, skin=(58, 48, 70), shirt=None),
}
FIRST_SPAWN_DELAY = 35.0


def spawn_delay(depth):
    return random.uniform(25, 50) * max(0.5, 1 - depth * 0.01)


def max_enemies(depth):
    return min(4, 1 + depth // 8)


def choose_kind(depth):
    options = [(k, s["weight"]) for k, s in ENEMY_TYPES.items() if depth >= s["min_depth"]]
    if not options:
        return None
    return random.choices([k for k, _ in options], weights=[w for _, w in options])[0]


def edge_cell():
    i = random.randrange(GRID)
    return random.choice([(i, 0), (i, GRID - 1), (0, i), (GRID - 1, i)])


class Enemy:
    EMERGE_SECS = 1.0

    def __init__(self, kind, depth, cell, ground_z):
        spec = ENEMY_TYPES[kind]
        self.kind = kind
        self.max_hp = spec["hp"] * 1.12 ** depth
        self.hp = self.max_hp
        self.bounty_base = spec["bounty"] * 2 * 1.1 ** depth
        self.x, self.y = cell[0] + 0.5, cell[1] + 0.5
        self.draw_z = ground_z - 0.9
        self.state = "emerging"       # emerging | hunting | attacking
        self.timer = 0.0
        self.victim = None
        self.grab_offset = (0.0, 0.0)
        self.facing = 1
        self.flash = 0.0              # white hit-flash timer
        self.anim_t = random.uniform(0, 10)

    @property
    def spec(self):
        return ENEMY_TYPES[self.kind]

    def release(self):
        self.victim = None
        self.state = "hunting"

    def update(self, world, dt):
        self.anim_t += dt
        self.flash = max(0.0, self.flash - dt)
        ground = world.column_height(*world.cell_of(self.x, self.y))

        if self.state == "emerging":   # climbing up out of the rock
            self.timer += dt
            self.draw_z = ground - 0.9 * max(0.0, 1 - self.timer / self.EMERGE_SECS)
            if self.timer >= self.EMERGE_SECS:
                self.state = "hunting"
            return

        if self.state == "attacking":
            v = self.victim
            if v is None or v.state != "grabbed" or v.attacker is not self:
                self.release()
            else:
                self.x, self.y = v.x + self.grab_offset[0], v.y + self.grab_offset[1]
                v.hp -= self.spec["dps"] * dt
                if v.hp <= 0:
                    world.miner_down(v)
                    self.release()
        else:
            target = world.nearest_free_miner(self.x, self.y)
            if target:
                dx, dy = target.x - self.x, target.y - self.y
                dist = math.hypot(dx, dy)
                self.facing = 1 if (dx - dy) >= 0 else -1
                if dist <= self.spec["reach"]:
                    world.grab(self, target)
                else:
                    step = min(dist, self.spec["speed"] * dt)
                    self.x += dx / dist * step
                    self.y += dy / dist * step
        self.draw_z += (ground - self.draw_z) * min(1.0, dt * 10)
