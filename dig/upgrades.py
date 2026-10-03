"""Upgrade tree: stat formulas, branches and node definitions."""
import math

from .util import fmt


def miner_count(lv): return 1 + lv
def miner_damage(lv): return (1 + lv) * 1.08 ** lv
def swing_time(lv): return max(0.15, 0.9 * 0.92 ** lv)
def walk_speed(lv): return 1.6 * (1 + 0.15 * lv)
def click_damage(lv): return (2 + 2 * lv) * 1.1 ** lv
def value_mult(lv): return 1.2 ** lv
def ore_mult(lv): return 1 + 0.25 * lv
def dynamite_interval(lv): return max(4, 16 - 2 * lv)


BRANCHES = {
    "core":    dict(name="Core",    color=(240, 196, 80)),
    "crew":    dict(name="Crew",    color=(90, 170, 240)),
    "tools":   dict(name="Tools",   color=(240, 120, 80)),
    "hands":   dict(name="Hands",   color=(190, 110, 235)),
    "fortune": dict(name="Fortune", color=(100, 210, 120)),
    "mastery": dict(name="Mastery", color=(255, 90, 125)),
}


def _up(key, name, branch, icon, pos, requires, base, growth, max_lv, desc, effect):
    return dict(key=key, name=name, branch=branch, icon=icon, pos=pos, requires=requires,
                base=base, growth=growth, max=max_lv, desc=desc, effect=effect)


# pos = (column, tier); columns may be fractional so merge nodes sit between branches
UPGRADES = [
    _up("power", "Sharper Pickaxe", "core", "pick", (1.5, 0), [], 15, 1.55, None,
        "Miners hit harder. Every path starts here.", lambda l: f"{fmt(miner_damage(l))} dmg / hit"),
    # Crew
    _up("miners", "Hire Miner", "crew", "miner", (0, 1), [("power", 1)], 30, 2.1, 15,
        "Another miner joins the dig.", lambda l: f"{miner_count(l)} miners"),
    _up("boots", "Mining Boots", "crew", "boot", (0, 2), [("miners", 1)], 25, 1.6, 15,
        "Miners walk between blocks faster.", lambda l: f"{walk_speed(l):.1f} tiles / s"),
    _up("teamwork", "Teamwork", "crew", "team", (0, 3), [("boots", 2)], 400, 2.0, 10,
        "Every miner on the crew boosts everyone's damage.", lambda l: f"+{3 * l}% dmg per miner"),
    # Tools
    _up("speed", "Swing Speed", "tools", "clock", (1, 1), [("power", 1)], 40, 1.7, 25,
        "Miners swing faster.", lambda l: f"{swing_time(l):.2f}s / swing"),
    _up("crit", "Lucky Strikes", "tools", "star", (1, 2), [("speed", 2)], 150, 1.9, 10,
        "Miner hits can crit for triple damage.", lambda l: f"{5 * l}% crit chance"),
    _up("quake", "Seismic Strikes", "tools", "bolt", (1, 3), [("crit", 2)], 900, 2.1, 5,
        "Crits shake the four neighbouring blocks.", lambda l: f"crits splash {25 * l}%"),
    # Hands
    _up("click", "Power Gloves", "hands", "hand", (2, 1), [("power", 1)], 10, 1.45, None,
        "Your own clicks hit harder.", lambda l: f"{fmt(click_damage(l))} dmg / click"),
    _up("shockwave", "Shockwave", "hands", "wave", (2, 2), [("click", 3)], 120, 1.9, 5,
        "Your clicks splash onto neighbouring blocks.", lambda l: f"clicks splash {20 * l}%"),
    _up("autotap", "Auto-Tapper", "hands", "cursor", (2, 3), [("shockwave", 1)], 600, 2.0, 10,
        "A ghostly hand clicks random blocks for you.", lambda l: f"{l} taps / s"),
    # Fortune
    _up("value", "Ore Appraiser", "fortune", "coin", (3, 1), [("power", 1)], 75, 1.75, None,
        "Everything you dig sells for more.", lambda l: f"x{value_mult(l):.2f} value"),
    _up("prospector", "Prospector", "fortune", "gem", (3, 2), [("value", 2)], 250, 1.9, 10,
        "Ore veins show up more often in new layers.", lambda l: f"x{ore_mult(l):.2f} ore chance"),
    _up("double", "Double Haul", "fortune", "coins", (3, 3), [("prospector", 1)], 800, 2.0, 10,
        "Broken blocks sometimes pay out twice.", lambda l: f"{4 * l}% double pay"),
    # Mastery: merge points where two branches meet
    _up("foreman", "Foreman", "mastery", "crown", (0.5, 4), [("teamwork", 1), ("quake", 1)],
        5000, 2.5, 5, "Barks orders: the whole crew swings faster.",
        lambda l: f"-{round(100 * (1 - 0.9 ** l))}% swing time"),
    _up("dynamite", "Dynamite", "mastery", "bomb", (1.5, 4), [("quake", 1), ("autotap", 1)],
        8000, 2.5, 6, "Blasts a 3x3 area for 10x click damage now and then.",
        lambda l: "no dynamite" if l == 0 else f"boom every {dynamite_interval(l)}s"),
    _up("goldrush", "Gold Rush", "mastery", "nugget", (2.5, 4), [("autotap", 1), ("double", 1)],
        12000, 2.5, 5, "Broken blocks may drop a nugget worth 25x.",
        lambda l: f"{2 * l}% nugget chance"),
]
UPGRADE_BY_KEY = {u["key"]: u for u in UPGRADES}


def upgrade_cost(up, level):
    return math.ceil(up["base"] * up["growth"] ** level)


def is_unlocked(up, levels):
    return all(levels[k] >= n for k, n in up["requires"])


def is_maxed(up, levels):
    return up["max"] is not None and levels[up["key"]] >= up["max"]
