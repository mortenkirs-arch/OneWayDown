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

Bosses (boss=True) never grab: they stalk the crew, wind up and slam the ground around them, and
call in minions. Extra keys:
  look, scale   which enemy sprite to draw, and how much bigger
  slam          damage to every crew member in reach when the slam lands (MINER_MAX_HP = 10)
  minion        dict(kind, count, every): summoned around the boss every `every` seconds
  dive          (flying bosses) instead of walking up and slamming, it marks a crew member's spot and
                swoops onto it when the wind-up ends
Each boss also has a trick of its own, run by World.boss_special (see the BOSS TRICKS constants below):
  Zombie King   rallies nearby zombies (faster, tougher) and goes into a rage below half health
  Broodmother   her slams leave webs that slow the crew; she lays egg sacs that hatch into spiders
  Vampire Lord  turns into a swarm of bats, flies to a crew member and bites them to heal
  Great Bat     dive-bombs a crew member from the air instead of slamming, and screeches to stun the crew
  Bone Tyrant   throws bones at distant crew; its first "death" leaves a bone pile you must smash quickly
  Lich          curses a crew member (click them to lift it before it explodes); his wisps shield him

Egg sacs (hatch=...) don't move: they hatch into `count` of `kind` after `after` seconds unless broken.
entrance="none" means the enemy is simply there, with no spawn-in animation.
"""
import math
import random

from .blocks import hp_scale, value_scale
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
                transform=dict(into="vampire", min_depth=16, after=3.0),
                tint=(228, 228, 238), gore=(70, 50, 80)),
    "vampire": dict(name="Vampire", hp=28, speed=0.9, dps=2.0, bounty=26, min_depth=16, weight=0,
                    reach=0.3, entrance="dig", grab="side", arrival="rises", lifesteal=0.5,
                    tint=(228, 228, 238), gore=(160, 30, 45)),
    "skeleton": dict(name="Skeleton", hp=12, speed=0.75, dps=1.5, bounty=11, min_depth=9, weight=3,
                     reach=0.3, entrance="dig", grab="side", arrival="rattles out",
                     tint=(200, 200, 220), gore=(232, 226, 205)),
    "wisp": dict(name="Wisp", hp=5, speed=2.6, dps=1.0, bounty=8, min_depth=13, weight=2,
                 reach=0.3, entrance="fade", grab="orbit", arrival="flickers in",
                 altitude=0.8, wobble=dict(amount=1.3, freq=9),
                 tint=(170, 210, 255), gore=(150, 215, 255)),
    "ghost": dict(name="Ghost", hp=24, speed=0.45, dps=1.6, bounty=20, min_depth=19, weight=2,
                  reach=0.3, entrance="fade", grab="engulf", arrival="materialises",
                  altitude=0.35, wobble=dict(amount=0.35, freq=1.5), phase=dict(every=4.0, duration=1.2),
                  tint=(160, 190, 230), gore=(220, 230, 255)),

    # ----- bosses: one every BOSS_EVERY metres, in this order, then round again ----------------
    "zombieking": dict(name="Zombie King", hp=2200, speed=0.45, dps=0, bounty=360, min_depth=0, weight=0,
                       reach=0.9, entrance="dig", grab="side", arrival="rises", boss=True,
                       look="zombie", scale=2.2, slam=4.0, minion=dict(kind="zombie", count=2, every=14.0),
                       tint=(150, 130, 210), gore=(120, 190, 80)),
    "broodmother": dict(name="Broodmother", hp=2000, speed=0.8, dps=0, bounty=360, min_depth=0, weight=0,
                        reach=0.9, entrance="drop", grab="head", arrival="descends", boss=True,
                        look="spider", scale=2.4, crown_lift=14, slam=3.0,
                        minion=dict(kind="eggsac", count=2, every=9.0),
                        tint=(150, 200, 120), gore=(90, 60, 120)),
    "greatbat": dict(name="Great Bat", hp=2400, speed=1.0, dps=0, bounty=380, min_depth=0, weight=0,
                     reach=0.9, entrance="swoop", grab="neck", arrival="swoops in", boss=True, dive=True,
                     altitude=1.1, look="bat", scale=2.4, crown_lift=16, slam=4.0,
                     minion=dict(kind="bat", count=3, every=11.0),
                     tint=(228, 228, 238), gore=(70, 50, 80)),
    "bonetyrant": dict(name="Bone Tyrant", hp=2400, speed=0.5, dps=0, bounty=400, min_depth=0, weight=0,
                       reach=0.9, entrance="dig", grab="side", arrival="rises", boss=True,
                       look="skeleton", scale=2.3, slam=5.0, minion=dict(kind="skeleton", count=2, every=12.0),
                       tint=(200, 200, 220), gore=(232, 226, 205)),
    "vampirelord": dict(name="Vampire Lord", hp=2800, speed=0.6, dps=0, bounty=400, min_depth=0, weight=0,
                        reach=0.9, entrance="dig", grab="side", arrival="awakens", boss=True, lifesteal=0.03,
                        look="vampire", scale=2.0, slam=4.0, minion=dict(kind="bat", count=2, every=12.0),
                        tint=(228, 228, 238), gore=(160, 30, 45)),
    "lich": dict(name="Lich", hp=2600, speed=0.4, dps=0, bounty=420, min_depth=0, weight=0,
                 reach=0.9, entrance="fade", grab="engulf", arrival="materialises", boss=True,
                 altitude=0.35, wobble=dict(amount=0.2, freq=1.0),
                 look="ghost", scale=2.2, slam=5.0, minion=dict(kind="wisp", count=3, every=10.0),
                 boss_tint=(205, 160, 255),
                 tint=(160, 190, 230), gore=(200, 170, 255)),
    "eggsac": dict(name="Egg Sac", hp=10, speed=0, dps=0, bounty=4, min_depth=0, weight=0,
                   reach=0, entrance="none", grab="head", arrival="", hatch=dict(kind="spider", count=2, after=6.0),
                   tint=(230, 230, 210), gore=(225, 225, 200)),
}
FLY_ALTITUDE = ENEMY_TYPES["bat"]["altitude"]   # bat swoop-in / transformation height

BOSSES = ["zombieking", "broodmother", "greatbat", "bonetyrant", "vampirelord", "lich"]
BOSS_EVERY = 10              # a boss guards every 10th metre
BOSS_TIME_LIMIT = 150.0      # seconds before an unbeaten boss retreats (no reward, but the dig goes on)
BOSS_PCT_SCALE = 0.04        # bosses shrug off "share of max health" damage (Executioner, guards, ballista...)
BOSS_WINDUP = 1.3            # seconds of warning before a slam lands
BOSS_SLAM_RADIUS = 1.4       # tiles: crew this close to the boss when it slams get hit
BOSS_SLAM_COOLDOWN = 3.5     # seconds after a slam before it can wind up again
BOSS_MAX_MINIONS = 4         # it stops calling for help with this many minions alive
DIVE_SECS = 0.35             # a diving boss swoops onto its marked spot over the last moments of the wind-up

# ----- BOSS TRICKS ------------------------------------------------------------------------------
RALLY_RADIUS = 2.5           # Zombie King: zombies this close to him are rallied...
RALLY_SPEED = 1.6            # ...moving this much faster...
RALLY_TOUGH = 0.5            # ...and taking only this share of damage
ENRAGE_AT = 0.5              # below this share of his health he rages:
ENRAGE_PACE = 0.55           # wind-ups and cool-downs shrink to this share
WEB_SECS = 9.0               # Broodmother: webs left by her slam last this long...
WEB_SLOW = 0.35              # ...and crew crossing them move at this share of their speed
BAT_FORM_EVERY = 14.0        # Vampire Lord: seconds between turning into a swarm of bats
BAT_FORM_SPEED = 3.2         # tiles/s the swarm flies (nothing can hit it)
BITE_SECS = 3.5              # how long he feeds on the crew member he lands on...
BITE_DPS = 2.2               # ...draining this much health a second...
BITE_HEAL = 0.012            # ...and healing this share of his max health a second
BITE_BREAK = 0.04            # taking this share of his max health while biting makes him let go
CURSE_EVERY = 9.0            # Lich: seconds between curses
CURSE_SECS = 4.5             # a curse bursts this long after it lands, unless you click the crew member
CURSE_DMG = 6.0              # damage to every crew member within CURSE_RADIUS when it bursts
CURSE_RADIUS = 1.5
CURSE_WARD = 0.3             # Spirit Lantern weakens the burst by this share per level
SHIELD_PER_WISP = 0.25       # each wisp alive takes this share off the damage the Lich takes...
SHIELD_MAX = 0.75            # ...up to this much
SCREECH_EVERY = 13.0         # Great Bat: seconds between screeches...
SCREECH_RADIUS = 3.5         # ...stunning the crew within this many tiles...
SCREECH_STUN = 2.2           # ...for this long
BONE_THROW_EVERY = 5.0       # Bone Tyrant: seconds between bones thrown at whoever is furthest away...
BONE_THROW_DMG = 3.0         # ...hitting for this much
BONE_THROW_SECS = 0.7        # (flight time)
PILE_SECS = 5.0              # its first "death" leaves a bone pile: smash it within this long...
PILE_HP = 0.2                # ...(the pile has this share of its max health)...
REFORM_HP = 0.5              # ...or it pulls itself together with this share


def boss_for(depth):
    """The boss guarding this depth, or None if it isn't a boss depth."""
    if depth < BOSS_EVERY or depth % BOSS_EVERY:
        return None
    return BOSSES[(depth // BOSS_EVERY - 1) % len(BOSSES)]

# Waves: every spawn_interval(depth) seconds the board is topped up to max_enemies(depth).
ENEMY_START_DEPTH = 1          # monsters arrive the moment you reach this depth (none above it)
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
    def __init__(self, kind, depth, cell, ground_z, delay=0.0, hp_mult=1.0):
        self.depth = depth
        self.hp_mult = hp_mult        # (Zombie King's Crown)
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
        self.windup = 0.0             # boss: seconds until the slam lands (0 = not winding up)
        self.windup_total = BOSS_WINDUP   # boss: how long this wind-up lasts in all (shorter when enraged)
        self.cooldown = BOSS_SLAM_COOLDOWN   # boss: seconds before it can wind up again
        self.summon_timer = 4.0       # boss: seconds until it calls in minions
        self.fight_time = 0.0         # boss: seconds since it arrived (it retreats at BOSS_TIME_LIMIT)
        self.dmg_taken = 1.0          # share of incoming damage that lands (rallied zombies, shielded Lich)
        self.enraged = False          # Zombie King: below ENRAGE_AT health
        self.mode = "stalk"           # Vampire Lord: stalk | bats (flying, untouchable) | bite
        self.trick_timer = 6.0        # seconds until the boss's own trick (bat form, curse)
        self.goal = None              # Vampire Lord: the crew member the swarm is flying at
        self.bite_hp = 0.0            # his health when the bite began (to tell when he's been hit enough)
        self.slam_at = None           # Great Bat: the spot it will dive onto when the wind-up ends
        self.reformed = False         # Bone Tyrant: already pulled itself back together once
        self.pile_timer = 0.0         # ...seconds left to smash its bone pile
        if ENEMY_TYPES[kind]["entrance"] == "none":
            self.state = "hunting"

    def become(self, kind):
        """Set the enemy type, with full health for that type at this depth."""
        spec = ENEMY_TYPES[kind]
        self.kind = kind
        self.max_hp = spec["hp"] * hp_scale(self.depth) * self.hp_mult
        self.hp = self.max_hp
        self.bounty_base = spec["bounty"] * 2 * value_scale(self.depth)

    @property
    def boss(self):
        return self.spec.get("boss", False)

    @property
    def pct_scale(self):
        """How much of any "share of max health" damage actually lands (bosses resist it)."""
        return BOSS_PCT_SCALE if self.boss else 1.0

    @property
    def look(self):
        """The sprite this enemy is drawn with (bosses borrow a regular monster's, scaled up)."""
        return self.spec.get("look", self.kind)

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
        if not phase or self.state != "hunting" or getattr(self, "warded", False):   # Spirit Lantern
            return False
        return self.hunt_time % phase["every"] >= phase["every"] - phase["duration"]

    def entrance_progress(self):
        """<0 while waiting/telegraphing, 0..1 during the entrance animation, >=1 once done."""
        return (self.timer - TELEGRAPH_SECS) / ENTRANCE_SECS

    @property
    def targetable(self):
        return self.state not in ("emerging", "transforming") and not self.phased and self.mode != "bats"

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

        if self.boss:
            self.update_boss(world, dt)
            return
        hatch = self.spec.get("hatch")
        if hatch:
            self.timer += dt
            if self.timer >= hatch["after"]:
                world.hatch(self)
            return

        if self.state == "attacking":
            v = self.victim
            if v is None or v.state != "grabbed" or v.attacker is not self:
                self.release()
                return
            self.x, self.y = v.x + self.grab_offset[0], v.y + self.grab_offset[1]
            drained = min(v.hp, self.spec["dps"] * dt * world.art_mult("grab_dmg"))   # (Broodmother's Silk)
            v.hp -= drained
            if self.spec.get("lifesteal"):
                self.hp = min(self.max_hp, self.hp + drained / v.max_hp * self.max_hp * self.spec["lifesteal"])
                world.blood_drip(v, self)
            if v.hp <= 0:
                world.miner_down(v, killer=self)
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
        step = min(dist, self.spec["speed"] * getattr(self, "speed_mult", 1.0) * dt)   # (Spirit Lantern)
        self.x = min(GRID - 0.05, max(0.05, self.x + ux * step))
        self.y = min(GRID - 0.05, max(0.05, self.y + uy * step))

    def update_boss(self, world, dt):
        """Stalk the nearest crew member, wind up, slam the ground around itself; call in minions."""
        self.hunt_time += dt
        self.fight_time += dt
        if self.fight_time >= BOSS_TIME_LIMIT:
            world.boss_retreat(self)
            return
        self.summon_timer -= dt
        if self.summon_timer <= 0:
            self.summon_timer = self.spec["minion"]["every"]
            world.boss_summon(self)
        if world.boss_special(self, dt):   # busy with its own trick (flying as bats, feeding)
            return
        pace = ENRAGE_PACE if self.enraged else 1.0
        if self.windup > 0:   # rooted to the spot, about to slam (or, diving, about to swoop)
            if self.slam_at and self.windup <= DIVE_SECS:
                tx, ty = self.slam_at
                share = min(1.0, dt / max(self.windup, dt))
                self.x += (tx - self.x) * share
                self.y += (ty - self.y) * share
            self.windup -= dt
            if self.windup <= 0:
                self.windup = 0.0
                self.cooldown = BOSS_SLAM_COOLDOWN * pace
                world.boss_slam(self)
                self.slam_at = None
            return
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.spec.get("dive"):
            self.hover_and_dive(world, dt, pace)
            return
        target = world.nearest_crew(self.x, self.y)
        if not target:
            return
        dx, dy = target.x - self.x, target.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0.03:
            self.facing = 1 if (dx - dy) >= 0 else -1
        if dist <= self.spec["reach"]:
            if self.cooldown <= 0:
                self.windup = self.windup_total = BOSS_WINDUP * pace
            return
        ux, uy = dx / dist, dy / dist
        self.heading = (ux, uy)
        step = min(dist - self.spec["reach"] * 0.8, self.spec["speed"] * getattr(self, "speed_mult", 1.0) * dt)
        self.x = min(GRID - 0.05, max(0.05, self.x + ux * step))
        self.y = min(GRID - 0.05, max(0.05, self.y + uy * step))

    def hover_and_dive(self, world, dt, pace):
        """A flying boss: drift about over the board, and when ready mark a crew member's spot to dive onto."""
        if self.cooldown <= 0:
            crew = [m for m in world.miners if m.state != "down"]
            if crew:
                target = random.choice(crew)
                self.slam_at = (target.x, target.y)
                self.windup = self.windup_total = BOSS_WINDUP * pace
                return
        if self.goal is None or math.hypot(self.goal[0] - self.x, self.goal[1] - self.y) < 0.2:
            self.goal = (random.uniform(1.5, GRID - 1.5), random.uniform(1.5, GRID - 1.5))
        dx, dy = self.goal[0] - self.x, self.goal[1] - self.y
        dist = math.hypot(dx, dy)
        if dist > 0.03:
            self.facing = 1 if (dx - dy) >= 0 else -1
            step = min(dist, self.spec["speed"] * dt)
            self.x += dx / dist * step
            self.y += dy / dist * step
