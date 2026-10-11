"""Test games for developers: a world at any depth, set up about how a player would have it by then.

Used by `uv run main.py --depth N` / `--boss NAME` (see main.py). Nothing here touches the real save.
"""
import random

from .artifacts import COMMON, TROPHY_OF
from .blocks import generate_layer, layer_value
from .enemies import BOSS_EVERY, BOSSES, ENEMY_TYPES, boss_for
from .miners import MAX_LEVEL, xp_to_next
from .upgrades import UPGRADES, ore_mult, ore_richness, value_mult
from .camp import EXPEDITION_DEPTH, hireable
from .world import World

# A real player's game at 60m, just after beating the Lich (the boss there at the time), which felt about right:
# every other depth is scaled from it. Upgrade levels:
ANCHOR_DEPTH = 60
ANCHOR_LEVELS = {
    "autotap": 5, "ballista": 1, "bigbombs": 2, "boots": 7, "bounty": 7, "chests": 2, "cleave": 5, "click": 12,
    "coffee": 3, "combo": 3, "crit": 2, "deepstrike": 1, "defense": 7, "demolition": 2, "diamond": 3, "double": 2, "driller": 4,
    "dynamite": 2, "executioner": 11, "firstaid": 5, "foreman": 1, "goldblock": 3, "golddust": 5, "golden": 7,
    "goldrush": 1, "guard": 4, "hardhats": 5, "laststand": 2, "masterwork": 1, "midas": 1, "miners": 9,
    "graveyardshift": 2, "medic": 2, "veterans": 1, "power": 7, "prospector": 5, "quake": 1, "secondwind": 3, "shockwave": 5, "slam": 1,
    "slayer": 12, "smite": 7, "speed": 4, "spiritlantern": 1, "steady": 3, "streak": 2, "surveyor": 3,
    "teamwork": 4, "traps": 2, "treasure": 5, "value": 8, "vault": 1, "vein": 1, "whetstone": 1,
}
# ...the common artifacts, in the order they were found...
ANCHOR_COMMONS = ["medal", "gauntlet", "boots", "heart", "amulet", "pickhead", "compass", "claw", "horseshoe"]
# ...and the crew's levels by role.
ANCHOR_CREW = {
    "miner": [5, 5, 4, 4, 3, 2, 2, 2, 2, 1, 1], "driller": [6, 5, 4, 2], "guard": [6, 6, 5, 3],
    "demolitionist": [7], "foreman": [7], "medic": [5],
}
CURVE = 0.75     # progress isn't linear: cheap early levels go fast, so a player is further along than depth/60
BUY_AFTER = 3    # metres after an upgrade unlocks before a player has bought its first level
TEST_SAVE_DIR = "saves"


def boss_aliases():
    """{name a developer might type: boss key}: the key itself, its words, and its words run together."""
    aliases = {}
    for key in BOSSES:
        name = ENEMY_TYPES[key]["name"].lower()
        for alias in (key, name.replace(" ", ""), *name.split()):
            if alias not in ("the", "great", "king", "lord"):
                aliases.setdefault(alias, key)
    return aliases


def boss_depth(key):
    """The first depth this boss guards."""
    return (BOSSES.index(key) + 1) * BOSS_EVERY


def progress(depth, start=0):
    """How far along a player at `depth` is towards the anchor game, for something that began at `start`: 0 there,
    1 at the anchor depth, a little more past it."""
    if depth <= start:
        return 0.0
    return ((depth - start) / max(1, ANCHOR_DEPTH - start)) ** CURVE


def test_levels(depth):
    """Upgrade levels for a player who has reached `depth` (only upgrades they could have bought)."""
    levels = {}
    for up in UPGRADES:
        top = ANCHOR_LEVELS.get(up["key"], 0)
        if depth < up["depth"] or not top:
            continue
        lv = round(top * progress(depth, up["depth"]))
        if depth >= up["depth"] + BUY_AFTER:
            lv = max(1, lv)
        levels[up["key"]] = min(lv, up["tree_max"]) if up["max"] else lv   # (no deep ranks)
    changed = True
    while changed:   # drop anything whose prerequisites ended up missing
        changed = False
        for up in UPGRADES:
            if levels.get(up["key"]) and any(levels.get(k, 0) < n for k, n in up["requires"]):
                levels[up["key"]] = 0
                changed = True
    return levels


def test_world(depth, gold=None, seed=None):
    """A fresh World at `depth`: upgrades, crew experience, earlier bosses' trophies and a few artifacts as a
    player there would have them, and some gold to spend. A boss guarding this depth rises straight away.
    Past EXPEDITION_DEPTH it's a later expedition: the camp has one build per expedition finished."""
    rng = random.Random(depth if seed is None else seed)
    w = World()
    if depth > EXPEDITION_DEPTH:
        w.expedition = (depth - 1) // EXPEDITION_DEPTH
        depth -= EXPEDITION_DEPTH * w.expedition
        for _ in range(w.expedition):   # (the camp's hires, in tent order)
            if hireable(w.camp):
                w.camp.append(hireable(w.camp)[0])
    w.levels.update(test_levels(depth))
    w.depth = depth
    prospector = w.lv("prospector")
    w.current = w.new_layer(depth, ore_mult(prospector), rng=rng, richness=ore_richness(prospector))
    w.next = w.new_layer(depth + 1, ore_mult(prospector), rng=rng, richness=ore_richness(prospector))
    w.layer_value = layer_value(w.current)
    beaten = [b for b in BOSSES[:max(0, depth - 1) // BOSS_EVERY]]   # bosses already behind them
    found = min(len(COMMON), round(len(ANCHOR_COMMONS) * depth / ANCHOR_DEPTH))
    others = [a for a in COMMON if a not in ANCHOR_COMMONS]
    commons = ANCHOR_COMMONS[:found] + rng.sample(others, max(0, found - len(ANCHOR_COMMONS)))
    w.artifacts = [TROPHY_OF[b] for b in beaten] + commons
    w.refresh_artifacts()
    w.boss_done = depth - 1
    w.sync_miners()
    by_role = {}
    for m in w.miners:   # a crew that's been around a while: the anchor crew's levels, scaled to this depth
        spread = ANCHOR_CREW.get(m.role, ANCHOR_CREW["miner"])
        k = by_role[m.role] = by_role.get(m.role, -1) + 1
        m.level = min(MAX_LEVEL, 1 + round((spread[min(k, len(spread) - 1)] - 1) * progress(depth)))
        m.xp = rng.uniform(0, xp_to_next(m.level)) if m.level < MAX_LEVEL else 0.0
    w.gold = layer_value(w.current) * value_mult(w.lv("value")) * 3 if gold is None else gold
    w.enemy_timer = w.wave_interval()
    if boss_for(depth):
        w.spawn_boss()
    return w
