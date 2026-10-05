"""Miners: the player's crew. They dig, can be grabbed by enemies, go down and respawn.

Each miner gets a random look (skin, hair, style, facial hair, shirt, height) and a name.
The look is saved with the game so the crew stays recognisable between sessions.
"""
import random

from .config import GRID

# Crew roles. Diggers mine blocks; the rest are specialist hires from the Crew menu.
ROLES = {
    "miner":         dict(hp=1.0, speed=1.0, height=0),
    "driller":       dict(hp=2.0, speed=0.65, height=2),   # stocky, slow, hits blocks rapidly
    "guard":         dict(hp=1.6, speed=1.1, height=3),    # patrols and fights monsters
    "demolitionist": dict(hp=1.0, speed=1.0, height=0),    # plants charges on tough blocks
    "foreman":       dict(hp=1.0, speed=0.8, height=4),    # walks the site barking orders
}
DIGGERS = ("miner", "driller")
CRIT_ANIM_SECS = 0.6          # a critical strike's slam-and-recoil animation
MINER_MAX_HP = 10.0           # before Hard Hats (see upgrades.miner_max_hp)

# Experience: the crew get better at their jobs the longer they survive (a new recruit starts over).
MAX_LEVEL = 10
XP_FIRST = 10.0               # xp from level 1 to 2 (a digger earns about 1 xp per block broken)...
XP_GROWTH = 1.6               # ...and each level after needs this much more than the last


def xp_to_next(level):
    return XP_FIRST * XP_GROWTH ** (level - 1)


def level_mult(level):
    """How good a crew member is at their job: 1x at level 1, 2x at MAX_LEVEL."""
    return 1 + (level - 1) / (MAX_LEVEL - 1)

SKIN_TONES = [(255, 224, 196), (241, 194, 155), (224, 172, 125), (198, 134, 90),
              (161, 102, 64), (120, 74, 46), (88, 54, 36)]
NATURAL_HAIR = [(30, 24, 20), (78, 52, 32), (150, 100, 50), (226, 194, 110),
                (184, 72, 30), (205, 205, 210)]
DYED_HAIR = [(90, 160, 235), (235, 90, 170), (120, 210, 110), (170, 110, 235)]
HAIR_STYLES = {"short": 4, "long": 3, "ponytail": 2, "mohawk": 1, "bald": 1}
FACIAL_HAIR = {None: 6, "beard": 2, "mustache": 2}
SHIRTS = [(80, 160, 230), (230, 120, 80), (120, 200, 110), (210, 110, 200), (240, 200, 70),
          (90, 200, 200), (200, 70, 70), (150, 150, 165), (250, 150, 180), (110, 110, 220)]
NAMES = ["Gus", "Dot", "Rocco", "Mabel", "Bjorn", "Pip", "Rusty", "Ada", "Clem", "Nell",
         "Otto", "Fern", "Boris", "Tilly", "Hank", "Ivy", "Moe", "Greta", "Duke", "Opal",
         "Ziggy", "Bea", "Knut", "Lola", "Stan", "Wren", "Igor", "Peg", "Chip", "Rita",
         "Dusty", "Olga", "Flint", "Juno", "Barry", "Sven", "Ruby", "Clyde", "Agnes", "Rex"]

LOOK_FIELDS = ("name", "skin", "hair", "style", "facial", "shirt", "height")
ROMAN = ["", "", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X"]


def new_stats(depth=0, clock=0.0):
    """Lifetime record for one miner (shown on the Crew page, kept in the graveyard)."""
    return dict(blocks=0, gold=0.0, monsters=0, saved=0, orders=0, hired_depth=depth, hired_clock=clock)


def base_name(name):
    """'Gus III' -> 'Gus'."""
    return name.split(" ")[0]


def numbered_name(name, previous):
    """Name for the `previous + 1`-th miner called `name`: Gus, Gus II, Gus III, ..."""
    n = previous + 1
    return name + (ROMAN[n] if n < len(ROMAN) else f" #{n}")


def _weighted(options):
    return random.choices(list(options), weights=list(options.values()))[0]


def random_look(taken_names=()):
    free = [n for n in NAMES if n not in taken_names] or NAMES
    style = _weighted(HAIR_STYLES)
    dyed = random.random() < (0.6 if style == "mohawk" else 0.12)   # mohawks love a dye job
    return dict(
        name=random.choice(free),
        skin=random.choice(SKIN_TONES),
        hair=random.choice(DYED_HAIR if dyed else NATURAL_HAIR),
        style=style,
        facial=_weighted(FACIAL_HAIR),
        shirt=random.choice(SHIRTS),
        height=random.choice((-2, 0, 0, 2, 3)),   # px taller/shorter than average
    )


class Miner:
    """A crew member. role "miner" digs; role "foreman" walks the site barking orders (see World)."""

    def __init__(self, taken_names=(), role="miner"):
        self.role = role
        self.place_randomly()
        self.draw_z = 2.0
        self.target = None
        self.swing = random.uniform(0, 0.5)
        self.anim = 0.0          # pickaxe animation 0..1
        self.crit = 0.0          # seconds left of the critical-strike slam animation
        self.facing = 1
        self.max_hp = MINER_MAX_HP
        self.hp = self.max_hp
        self.state = "working"   # working | grabbed | down
        self.attacker = None     # enemy currently grabbing this miner
        self.respawn = 0.0       # seconds until a replacement recruit arrives (when dead)
        self.apply_look(random_look(taken_names))
        self.stats = new_stats()
        self.inspecting = None   # foreman: the miner currently being supervised
        self.walk_timer = 0.0    # foreman: seconds until moving on to someone else
        self.bark_timer = 2.0    # foreman: seconds until the next shouted order
        self.task = "idle"       # guard / demolitionist: what they're up to (see World)
        self.task_timer = random.uniform(4.0, 8.0)
        self.goal = None         # guard / demolitionist: (x, y) they're heading for, or a target
        self.charge_cell = None  # demolitionist: the block they're about to blow
        self.streak_cell = None  # Hot Streak: the block being hit in a row...
        self.streak = 0.0        # ...and how many hits in a row so far
        self.sharp = 0.0         # Whetstone: seconds of freshly sharpened pick left
        self.curse = 0.0         # Lich: seconds until the curse on them bursts (0 = not cursed)
        self.stun = 0.0          # Great Bat: seconds left reeling from its screech
        self.last_hurt = -1e9    # game clock when last hit (they only heal once they've had a breather)
        self.level = 1           # experience level (see level_mult)...
        self.xp = 0.0            # ...and xp towards the next one
        if ROLES[role]["height"]:
            self.height = ROLES[role]["height"]
        if role == "foreman" and self.facial is None:   # foremen always have a mustache
            self.facial = "mustache"

    @property
    def is_foreman(self):
        return self.role == "foreman"

    @property
    def digs(self):
        return self.role in DIGGERS

    def to_dict(self):
        return {**self.look(), "role": self.role, "stats": dict(self.stats), "level": self.level, "xp": self.xp}

    def apply_saved(self, data):
        self.apply_look(data)
        self.stats.update(data.get("stats", {}))   # older saves have no stats: keep the zeros
        self.level = data.get("level", 1)          # ...nor levels
        self.xp = data.get("xp", 0.0)

    def apply_look(self, look):
        for field in LOOK_FIELDS:
            value = look[field]
            setattr(self, field, tuple(value) if isinstance(value, list) else value)

    def look(self):
        return {field: getattr(self, field) for field in LOOK_FIELDS}

    def place_randomly(self):
        self.x = random.uniform(1, GRID - 1)
        self.y = random.uniform(1, GRID - 1)
