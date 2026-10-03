"""Test games for developers: a world at any depth, set up about how a player would have it by then.

Used by `uv run main.py --depth N` / `--boss NAME` (see main.py). Nothing here touches the real save.
"""
import random

from .artifacts import COMMON, TROPHY_OF
from .blocks import generate_layer, layer_value
from .enemies import BOSS_EVERY, BOSSES, ENEMY_TYPES, boss_for
from .miners import MAX_LEVEL, xp_to_next
from .upgrades import UPGRADES, ore_mult, ore_richness, value_mult
from .world import World

# Upgrades a player leans on, as (level at the depth it unlocks, levels gained per metre after that).
# Everything else that's unlocked gets 1 level, plus 1 every 6 metres.
CORE = {
    "miners": (2, 0.25), "power": (2, 0.55), "speed": (1, 0.4), "boots": (1, 0.2), "click": (1, 0.45),
    "value": (1, 0.3), "slayer": (2, 0.45), "executioner": (1, 0.3), "defense": (1, 0.2), "hardhats": (1, 0.15),
    "firstaid": (1, 0.12), "smite": (1, 0.15),
}
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


def test_levels(depth):
    """Upgrade levels for a player who has reached `depth` (only upgrades they could have bought)."""
    levels = {}
    for up in UPGRADES:
        if depth < up["depth"]:
            continue
        since = depth - up["depth"]
        base, rate = CORE.get(up["key"], (1, 1 / 6))
        lv = int(base + rate * since)
        levels[up["key"]] = min(lv, up["max"]) if up["max"] else lv
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
    player there would have them, and some gold to spend. A boss guarding this depth rises straight away."""
    rng = random.Random(depth if seed is None else seed)
    w = World()
    w.levels.update(test_levels(depth))
    w.depth = depth
    prospector = w.lv("prospector")
    w.current = generate_layer(depth, ore_mult(prospector), rng=rng, richness=ore_richness(prospector))
    w.next = generate_layer(depth + 1, ore_mult(prospector), rng=rng, richness=ore_richness(prospector))
    w.layer_value = layer_value(w.current)
    beaten = [b for b in BOSSES[:max(0, depth - 1) // BOSS_EVERY]]   # bosses already behind them
    w.artifacts = [TROPHY_OF[b] for b in beaten] + rng.sample(COMMON, min(len(COMMON), depth // 6))
    w.refresh_artifacts()
    w.boss_done = depth - 1
    w.sync_miners()
    for m in w.miners:   # a crew that's been around a while
        m.level = min(MAX_LEVEL, 1 + depth // 10 + rng.randint(0, 2))
        m.xp = rng.uniform(0, xp_to_next(m.level)) if m.level < MAX_LEVEL else 0.0
    w.gold = layer_value(w.current) * value_mult(w.lv("value")) * 3 if gold is None else gold
    w.enemy_timer = w.wave_interval()
    if boss_for(depth):
        w.spawn_boss()
    return w
