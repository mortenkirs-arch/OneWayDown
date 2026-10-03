"""Miners: the player's crew. They dig, can be grabbed by enemies, go down and respawn.

Each miner gets a random look (skin, hair, style, facial hair, shirt, height) and a name.
The look is saved with the game so the crew stays recognisable between sessions.
"""
import random

from .config import GRID

MINER_MAX_HP = 10.0
MINER_REGEN = 1.0             # hp per second while working
MINER_RESPAWN_SECS = 15.0

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
    def __init__(self, taken_names=()):
        self.place_randomly()
        self.draw_z = 2.0
        self.target = None
        self.swing = random.uniform(0, 0.5)
        self.anim = 0.0          # pickaxe animation 0..1
        self.facing = 1
        self.max_hp = MINER_MAX_HP
        self.hp = self.max_hp
        self.state = "working"   # working | grabbed | down
        self.attacker = None     # enemy currently grabbing this miner
        self.respawn = 0.0       # seconds until back on their feet (when down)
        self.apply_look(random_look(taken_names))

    def apply_look(self, look):
        for field in LOOK_FIELDS:
            value = look[field]
            setattr(self, field, tuple(value) if isinstance(value, list) else value)

    def look(self):
        return {field: getattr(self, field) for field in LOOK_FIELDS}

    def place_randomly(self):
        self.x = random.uniform(1, GRID - 1)
        self.y = random.uniform(1, GRID - 1)
