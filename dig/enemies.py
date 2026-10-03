"""Enemies that invade the dig site and attack miners.

Enemies only act while the player is on the dig site (see Scene.combat), so nothing
can kill the crew while you are browsing menus.

Each enemy type is data in ENEMY_TYPES:
  hp, bounty    base values, scaled by depth when the enemy appears
  speed, dps    tiles/s, and damage per second to a grabbed miner (MINER_MAX_HP = 10)
  min_depth     shallowest depth it can spawn at; weight = relative spawn chance (0 = never spawns directly)
  reach         how close it must get to grab a miner
  entrance      spawn animation: "dig" (claws out of the ground), "drop" (silk thread), "swoop" (flies in),
                "fade" (materialises out of cold mist)
  grab          "side" (stands beside the miner), "head" (rides the head), "neck" (latches onto the neck),
                "orbit" (circles the miner's head), "engulf" (wraps around the whole miner)
  arrival       wording for the wave banner
  altitude      blocks above the ground it floats at (0 / missing = walks)
  wobble        dict(amount, freq): zig-zag while flying towards a target
  phase         dict(every, duration): turns intangible (unclickable) for `duration` of every `every`
                seconds while hunting
  lifesteal     fraction of its own max hp healed by draining a whole miner
  transform     dict(into, min_depth, after): turns into another enemy after flying `after` seconds
  tint          colour a grabbed miner's face fades towards
  gore          colour of the particles when it is hit
"""
import math
import random

from .config import GRID

ENEMY_TYPES = {
    "zombie": dict(name="Zombie", hp=14, speed=0.55, dps=1.3, bounty=12, min_depth=1, weight=3,
                   reach=0.3, entrance="dig", grab="side", arrival="crawls out",
                   tint=(150, 130, 210), gore=(120, 190, 80)),
    "spider": dict(name="Cave Spider", hp=7, speed=1.5, dps=2.4, bounty=8, min_depth=6, weight=2,
                   reach=0.25, entrance="drop", grab="head", arrival="drops in",
                   tint=(150, 200, 120), gore=(90, 60, 120)),
    "bat": dict(name="Bat", hp=5, speed=1.9, dps=1.5, bounty=6, min_depth=3, weight=2,
                reach=0.3, entrance="swoop", grab="neck", arrival="swoops in",
                altitude=1.1, wobble=dict(amount=0.9, freq=6),
                transform=dict(into="vampire", min_depth=12, after=3.0),
                tint=(228, 228, 238), gore=(70, 50, 80)),
    "vampire": dict(name="Vampire", hp=24, speed=0.9, dps=2.0, bounty=24, min_depth=12, weight=0,
                    reach=0.3, entrance="dig", grab="side", arrival="rises", lifesteal=0.5,
                    tint=(228, 228, 238), gore=(160, 30, 45)),
    "wisp": dict(name="Wisp", hp=4, speed=2.6, dps=1.0, bounty=7, min_depth=9, weight=2,
                 reach=0.3, entrance="fade", grab="orbit", arrival="flickers in",
                 altitude=0.8, wobble=dict(amount=1.3, freq=9),
                 tint=(170, 210, 255), gore=(150, 215, 255)),
    "ghost": dict(name="Ghost", hp=20, speed=0.45, dps=1.6, bounty=18, min_depth=15, weight=2,
                  reach=0.3, entrance="fade", grab="engulf", arrival="materialises",
                  altitude=0.35, wobble=dict(amount=0.35, freq=1.5), phase=dict(every=4.0, duration=1.2),
                  tint=(160, 190, 230), gore=(220, 230, 255)),
}
FLY_ALTITUDE = ENEMY_TYPES["bat"]["altitude"]   # bat swoop-in / transformation height

# Waves: every spawn_interval(depth) seconds the board is topped up to max_enemies(depth).
ENEMY_START_DEPTH = 1          # no enemies on the surface layer
WAVE_INTERVAL_START = 35.0     # seconds between waves at ENEMY_START_DEPTH...
WAVE_INTERVAL_MIN = 20.0       # ...shrinking linearly to this by WAVE_FASTEST_DEPTH, then staying there
WAVE_FASTEST_DEPTH = 10
MAX_ENEMIES_CAP = 8


def spawn_interval(depth):
    t = (depth - ENEMY_START_DEPTH) / (WAVE_FASTEST_DEPTH - ENEMY_START_DEPTH)
    t = min(1.0, max(0.0, t))
    return WAVE_INTERVAL_START + (WAVE_INTERVAL_MIN - WAVE_INTERVAL_START) * t


def max_enemies(depth):
    """Enemies alive after each wave: 1 at depth 1, +1 every 3 levels, up to MAX_ENEMIES_CAP."""
    return min(MAX_ENEMIES_CAP, 1 + depth // 3)


def choose_kind(depth):
    options = [(k, s["weight"]) for k, s in ENEMY_TYPES.items() if s["weight"] > 0 and depth >= s["min_depth"]]
    if not options:
        return None
    return random.choices([k for k, _ in options], weights=[w for _, w in options])[0]


EDGE_CELLS = sorted({c for i in range(GRID) for c in ((i, 0), (i, GRID - 1), (0, i), (GRID - 1, i))})


def edge_cells(count):
    """`count` distinct random cells on the board's outer ring."""
    return random.sample(EDGE_CELLS, min(count, len(EDGE_CELLS)))


TELEGRAPH_SECS = 0.7   # warning before the enemy appears (cracks / silk strand / eyes in the dark)
ENTRANCE_SECS = 1.0    # the entrance animation itself
TRANSFORM_SECS = 0.8   # bat -> vampire smoke transformation


class Enemy:
    def __init__(self, kind, depth, cell, ground_z, delay=0.0):
        self.depth = depth
        self.become(kind)
        self.x, self.y = cell[0] + 0.5, cell[1] + 0.5
        self.draw_z = ground_z
        self.state = "emerging"       # emerging | hunting | attacking | transforming
        self.timer = -delay           # state clock; negative = not started yet (staggered waves)
        self.victim = None
        self.grab_offset = (0.0, 0.0)
        self.facing = 1
        self.flash = 0.0              # white hit-flash timer
        self.anim_t = random.uniform(0, 10)
        self.flight_time = 0.0        # seconds spent flying free (drives bat -> vampire)
        self.hunt_time = 0.0          # seconds spent hunting (drives ghost phasing)
        self.heading = (1.0, 0.0)     # last movement direction in grid space (wisp trails)

    def become(self, kind):
        """Set the enemy type, with full health for that type at this depth."""
        spec = ENEMY_TYPES[kind]
        self.kind = kind
        self.max_hp = spec["hp"] * 1.12 ** self.depth
        self.hp = self.max_hp
        self.bounty_base = spec["bounty"] * 2 * 1.1 ** self.depth

    @property
    def spec(self):
        return ENEMY_TYPES[self.kind]

    @property
    def altitude(self):
        return self.spec.get("altitude", 0.0)

    @property
    def flying(self):
        return self.altitude > 0

    @property
    def phased(self):
        """Intangible right now (ghosts fade out for part of every cycle while hunting)."""
        phase = self.spec.get("phase")
        if not phase or self.state != "hunting":
            return False
        return self.hunt_time % phase["every"] >= phase["every"] - phase["duration"]

    def entrance_progress(self):
        """<0 while waiting/telegraphing, 0..1 during the entrance animation, >=1 once done."""
        return (self.timer - TELEGRAPH_SECS) / ENTRANCE_SECS

    @property
    def targetable(self):
        return self.state not in ("emerging", "transforming") and not self.phased

    def release(self):
        self.victim = None
        self.state = "hunting"

    def update(self, world, dt):
        self.anim_t += dt
        self.flash = max(0.0, self.flash - dt)
        ground = world.column_height(*world.cell_of(self.x, self.y))
        self.draw_z += (ground - self.draw_z) * min(1.0, dt * 10)

        if self.state == "emerging":   # spawn animation; the sprite code reads entrance_progress()
            before = self.timer
            self.timer += dt
            if before < TELEGRAPH_SECS <= self.timer:
                if self.spec["entrance"] == "dig":
                    world.enemy_burst(self)        # ground bursts open
                elif self.spec["entrance"] == "fade":
                    world.enemy_materialise(self)  # puff of cold mist
            if self.timer >= TELEGRAPH_SECS + ENTRANCE_SECS:
                self.state = "hunting"
                if self.spec["entrance"] == "drop":
                    world.enemy_landed(self)   # thud on landing
            return

        if self.state == "transforming":
            self.timer += dt
            if self.timer >= TRANSFORM_SECS:
                self.state = "hunting"
            return

        if self.state == "attacking":
            v = self.victim
            if v is None or v.state != "grabbed" or v.attacker is not self:
                self.release()
                return
            self.x, self.y = v.x + self.grab_offset[0], v.y + self.grab_offset[1]
            drained = min(v.hp, self.spec["dps"] * dt)
            v.hp -= drained
            if self.spec.get("lifesteal"):
                self.hp = min(self.max_hp, self.hp + drained / v.max_hp * self.max_hp * self.spec["lifesteal"])
                world.blood_drip(v, self)
            if v.hp <= 0:
                world.miner_down(v)
                self.release()
            return

        # hunting
        self.hunt_time += dt
        transform = self.spec.get("transform")
        if transform and self.depth >= transform["min_depth"]:
            self.flight_time += dt
            if self.flight_time >= transform["after"]:
                world.transform_enemy(self, transform["into"])
                return
        target = world.nearest_free_miner(self.x, self.y)
        if not target:
            return
        dx, dy = target.x - self.x, target.y - self.y
        dist = math.hypot(dx, dy)
        self.facing = 1 if (dx - dy) >= 0 else -1
        if dist <= self.spec["reach"]:
            world.grab(self, target)
            return
        ux, uy = dx / dist, dy / dist
        wob = self.spec.get("wobble")
        if wob and dist > 0.8:   # zig-zag flight
            wobble = math.sin(self.anim_t * wob["freq"]) * wob["amount"]
            ux, uy = ux - uy * wobble, uy + ux * wobble
            norm = math.hypot(ux, uy)
            ux, uy = ux / norm, uy / norm
        self.heading = (ux, uy)
        step = min(dist, self.spec["speed"] * dt)
        self.x = min(GRID - 0.05, max(0.05, self.x + ux * step))
        self.y = min(GRID - 0.05, max(0.05, self.y + uy * step))
