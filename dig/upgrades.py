"""Upgrades: stat formulas, the five upgrade menus (tabs) and their node definitions.

Each upgrade lives in one tab ("branch") and forms a small branching tree inside it.
`pos` = (column, tier) within that tab's tree; columns may be fractional.
"""
import math

from .util import fmt

# ----- stat formulas -------------------------------------------------------
# Crew
def miner_count(lv): return 1 + lv
def walk_speed(lv): return 1.6 * (1 + 0.15 * lv)
def second_wind_boost(lv): return 0.2 * lv            # extra swing speed for 8s after clearing a layer
# Tools
def miner_damage(lv): return (1 + lv) * 1.08 ** lv
def swing_time(lv): return max(0.15, 0.9 * 0.92 ** lv)
def ore_damage_mult(lv): return 1 + 0.25 * lv         # Diamond Tips, vs ore blocks
def masterwork_mult(lv): return 1.5 ** lv
# Hands (your clicks on BLOCKS)
def click_damage(lv): return (2 + 2 * lv) * 1.1 ** lv
def dynamite_interval(lv): return max(4, 16 - 2 * lv)
# Fortune
def value_mult(lv): return 1.2 ** lv
def ore_mult(lv): return 1 + 0.25 * lv
def bounty_mult(lv): return 1 + 0.5 * lv
def offline_share(lv): return 0.5 + 0.1 * lv
def midas_mult(lv): return 1 + 0.1 * lv
# Combat (your clicks on MONSTERS, and miners fighting back)
def monster_damage(lv): return (4 + 4 * lv) * 1.12 ** lv
def enemy_hit_floor(lv): return min(0.25, 0.08 + 0.01 * lv)   # min share of an enemy's max hp per hit
def miner_strike(lv): return 0.0 if lv == 0 else 0.01 + 0.01 * lv  # share of attacker's max hp per swing
def miner_max_hp(lv): return 10 * (1 + 0.25 * lv)
def respawn_secs(lv): return 15 - 1.5 * lv
def miner_regen(lv): return 1 + 0.5 * lv


TABS = ["crew", "tools", "hands", "fortune", "combat"]
BRANCHES = {
    "crew":    dict(name="Crew",    color=(90, 170, 240),  blurb="Hire and organise your miners"),
    "tools":   dict(name="Tools",   color=(240, 120, 80),  blurb="Better picks for your miners"),
    "hands":   dict(name="Hands",   color=(190, 110, 235), blurb="Your own clicks on blocks"),
    "fortune": dict(name="Fortune", color=(100, 210, 120), blurb="Squeeze more gold out of everything"),
    "combat":  dict(name="Combat",  color=(235, 85, 85),   blurb="Fight the monsters - you and your crew"),
}


def _up(key, name, branch, icon, pos, requires, base, growth, max_lv, desc, effect):
    return dict(key=key, name=name, branch=branch, icon=icon, pos=pos, requires=requires,
                base=base, growth=growth, max=max_lv, desc=desc, effect=effect)


UPGRADES = [
    # ----- Crew ---------------------------------------------------------------
    _up("miners", "Hire Miner", "crew", "miner", (1.5, 0), [], 30, 2.1, 15,
        "Another miner joins the dig.", lambda l: f"{miner_count(l)} miners hired"),
    _up("boots", "Mining Boots", "crew", "boot", (0.5, 1), [("miners", 1)], 25, 1.6, 15,
        "Miners walk between blocks faster.", lambda l: f"{walk_speed(l):.1f} tiles / s"),
    _up("teamwork", "Teamwork", "crew", "team", (0.5, 2), [("boots", 2)], 400, 2.0, 10,
        "Every miner on the crew boosts everyone's damage.", lambda l: f"+{3 * l}% dmg per miner"),
    _up("foreman", "Foreman", "crew", "crown", (0.5, 3), [("teamwork", 1)], 5000, 2.5, 5,
        "Hire a foreman who walks the site barking orders. While they're alive the whole crew swings "
        "faster, and miners they're standing near faster still.",
        lambda l: f"-{round(100 * (1 - 0.9 ** l))}% swing time"),
    _up("treasure", "Treasure Map", "crew", "map", (2.5, 1), [("miners", 2)], 150, 1.9, 5,
        "Miners go for ore first, and ore sells for more.", lambda l: f"+{10 * l}% ore value"),
    _up("secondwind", "Second Wind", "crew", "wind", (2.5, 2), [("treasure", 1)], 500, 2.0, 5,
        "Clearing a layer gives the crew a burst of speed.",
        lambda l: f"+{round(100 * second_wind_boost(l))}% swing speed for 8s"),
    _up("nightshift", "Night Shift", "crew", "moon", (1.5, 4), [("foreman", 1), ("secondwind", 1)],
        8000, 2.8, 5, "Extra miners on top of the ones you hire.", lambda l: f"+{l} miners"),

    # ----- Tools --------------------------------------------------------------
    _up("power", "Sharper Pickaxe", "tools", "pick", (1.5, 0), [], 15, 1.55, None,
        "Miners hit harder.", lambda l: f"{fmt(miner_damage(l))} dmg / hit"),
    _up("speed", "Swing Speed", "tools", "clock", (0.5, 1), [("power", 1)], 40, 1.7, 25,
        "Miners swing faster.", lambda l: f"{swing_time(l):.2f}s / swing"),
    _up("crit", "Lucky Strikes", "tools", "star", (0.5, 2), [("speed", 2)], 150, 1.9, 10,
        "Miner hits can crit for triple damage.", lambda l: f"{5 * l}% crit chance"),
    _up("quake", "Seismic Strikes", "tools", "bolt", (0.5, 3), [("crit", 2)], 900, 2.1, 5,
        "Crits shake the four neighbouring blocks.", lambda l: f"crits splash {25 * l}%"),
    _up("diamond", "Diamond Tips", "tools", "tip", (2.5, 1), [("power", 2)], 120, 1.8, 10,
        "Miners hit ore blocks much harder.", lambda l: f"x{ore_damage_mult(l):.2f} dmg vs ore"),
    _up("deepstrike", "Deep Strike", "tools", "drill", (2.5, 2), [("diamond", 1)], 600, 2.0, 5,
        "Miner hits also crack the block underneath.", lambda l: f"{10 * l}% to the layer below"),
    _up("masterwork", "Masterwork", "tools", "anvil", (1.5, 4), [("quake", 1), ("deepstrike", 1)],
        6000, 2.6, 5, "Masterfully forged picks for the whole crew.",
        lambda l: f"x{masterwork_mult(l):.2f} miner dmg"),

    # ----- Hands --------------------------------------------------------------
    _up("click", "Power Gloves", "hands", "hand", (1.5, 0), [], 10, 1.45, None,
        "Your clicks hit blocks harder.", lambda l: f"{fmt(click_damage(l))} dmg / click"),
    _up("shockwave", "Shockwave", "hands", "wave", (0.5, 1), [("click", 3)], 120, 1.9, 5,
        "Your clicks splash onto neighbouring blocks.", lambda l: f"clicks splash {20 * l}%"),
    _up("autotap", "Auto-Tapper", "hands", "cursor", (0.5, 2), [("shockwave", 1)], 600, 2.0, 10,
        "A ghostly hand clicks random blocks for you.", lambda l: f"{l} taps / s"),
    _up("dynamite", "Dynamite", "hands", "bomb", (0.5, 3), [("autotap", 1)], 8000, 2.5, 6,
        "Blasts an area for 10x click damage now and then.",
        lambda l: "no dynamite" if l == 0 else f"boom every {dynamite_interval(l)}s"),
    _up("bigbombs", "Bigger Bombs", "hands", "bigbomb", (0.5, 4), [("dynamite", 1)], 15000, 3.0, 2,
        "Dynamite blasts cover a wider area.", lambda l: f"{3 + 2 * l}x{3 + 2 * l} blast"),
    _up("golden", "Golden Touch", "hands", "touch", (2.5, 1), [("click", 2)], 60, 1.7, 10,
        "Your own clicks on blocks earn gold as you dig.", lambda l: f"{5 * l}% of block value / click"),
    _up("steady", "Steady Hands", "hands", "target", (2.5, 2), [("golden", 1)], 300, 1.9, 10,
        "Your clicks on blocks can crit for triple damage.", lambda l: f"{5 * l}% click crit chance"),

    # ----- Fortune ------------------------------------------------------------
    _up("value", "Ore Appraiser", "fortune", "coin", (1.5, 0), [], 75, 1.75, None,
        "Blocks sell for more.", lambda l: f"x{value_mult(l):.2f} block value"),
    _up("prospector", "Prospector", "fortune", "gem", (0.5, 1), [("value", 2)], 250, 1.9, 10,
        "Ore veins show up more often in new layers.", lambda l: f"x{ore_mult(l):.2f} ore chance"),
    _up("double", "Double Haul", "fortune", "coins", (0.5, 2), [("prospector", 1)], 800, 2.0, 10,
        "Broken blocks sometimes pay out twice.", lambda l: f"{4 * l}% double pay"),
    _up("goldrush", "Gold Rush", "fortune", "nugget", (0.5, 3), [("double", 1)], 12000, 2.5, 5,
        "Broken blocks may drop a nugget worth 25x.", lambda l: f"{2 * l}% nugget chance"),
    _up("bounty", "Bounty Hunter", "fortune", "skull", (2.5, 1), [("value", 1)], 100, 1.7, 10,
        "Monsters pay out bigger bounties.", lambda l: f"x{bounty_mult(l):.1f} bounties"),
    _up("pockets", "Deep Pockets", "fortune", "bag", (2.5, 2), [("bounty", 1)], 400, 2.2, 5,
        "Your crew earns more while you're away.", lambda l: f"{round(100 * offline_share(l))}% offline income"),
    _up("midas", "Midas Touch", "fortune", "sun", (1.5, 4), [("goldrush", 1), ("pockets", 1)],
        15000, 2.6, 5, "Every source of gold pays more.", lambda l: f"x{midas_mult(l):.1f} all gold"),

    # ----- Combat -------------------------------------------------------------
    _up("slayer", "Monster Slayer", "combat", "sword", (1.5, 0), [], 25, 1.5, None,
        "Your clicks hit monsters harder (separate from block damage).",
        lambda l: f"{fmt(monster_damage(l))} dmg / click on monsters"),
    _up("executioner", "Executioner", "combat", "axe", (0.5, 1), [("slayer", 1)], 60, 1.6, 17,
        "Every hit you land takes at least a share of a monster's health.",
        lambda l: f"min {enemy_hit_floor(l):.0%} of max hp / hit"),
    _up("smite", "Critical Smite", "combat", "burst", (0.5, 2), [("executioner", 2)], 250, 1.9, 10,
        "Your hits on monsters can crit for triple damage.", lambda l: f"{5 * l}% smite chance"),
    _up("cleave", "Cleave", "combat", "slash", (0.5, 3), [("smite", 1)], 1200, 2.1, 5,
        "Hitting a monster also hits other monsters close by.", lambda l: f"{20 * l}% to monsters nearby"),
    _up("defense", "Self Defense", "combat", "shield", (2.5, 1), [("slayer", 1)], 80, 1.7, 10,
        "Grabbed miners fight back, striking their attacker every swing.",
        lambda l: "miners can't fight back" if l == 0 else f"{miner_strike(l):.0%} of attacker hp / swing"),
    _up("hardhats", "Hard Hats", "combat", "helmet", (2.5, 2), [("defense", 1)], 200, 1.8, 8,
        "Miners survive longer when grabbed.", lambda l: f"{miner_max_hp(l):.1f} miner hp"),
    _up("firstaid", "First Aid", "combat", "cross", (2.5, 3), [("hardhats", 1)], 700, 2.0, 6,
        "Miners heal faster, and replacements for the fallen arrive sooner.",
        lambda l: f"{respawn_secs(l):.1f}s to replace, {miner_regen(l):.1f} hp/s regen"),
    _up("laststand", "Last Stand", "combat", "fist", (1.5, 4), [("cleave", 1), ("firstaid", 1)],
        10000, 2.8, 3, "Miners below 30% health fight back far harder.",
        lambda l: f"x{1 + l} strike when desperate"),
]
# Depth milestones: an upgrade can't be bought until you've dug this deep (as well as owning its
# prerequisites). Gives you something to dig towards - capstones only open up deep down.
UNLOCK_DEPTH = {
    # Crew
    "miners": 0, "boots": 2, "treasure": 4, "teamwork": 8, "secondwind": 10, "foreman": 16, "nightshift": 28,
    # Tools
    "power": 0, "speed": 1, "diamond": 3, "crit": 6, "deepstrike": 9, "quake": 14, "masterwork": 25,
    # Hands
    "click": 0, "golden": 2, "shockwave": 4, "steady": 7, "autotap": 10, "dynamite": 18, "bigbombs": 30,
    # Fortune
    "value": 0, "bounty": 3, "prospector": 5, "double": 9, "pockets": 12, "goldrush": 20, "midas": 32,
    # Combat (monsters show up from depth 1)
    "slayer": 1, "executioner": 2, "defense": 3, "smite": 6, "hardhats": 6, "firstaid": 10, "cleave": 12,
    "laststand": 24,
}
for _u in UPGRADES:
    _u["depth"] = UNLOCK_DEPTH[_u["key"]]
UPGRADE_BY_KEY = {u["key"]: u for u in UPGRADES}
UPGRADES_BY_TAB = {tab: [u for u in UPGRADES if u["branch"] == tab] for tab in TABS}

# Pricing (tuned with an auto-player sim so capped upgrades take hours to max, not ~13 minutes):
#  - the first level of every upgrade always costs exactly `base`, so the opening stays snappy
#  - each later level costs `growth` times the previous, and that multiplier climbs by COST_RAMP
#    per level, so an upgrade's own late levels get steep
#  - every level owned across all menus makes further levels COST_INFLATION pricier,
#    so you can't max everything at once and have to choose what to push
COST_RAMP = 1.06
COST_INFLATION = 1.04


def upgrade_cost(up, levels):
    """Price of the next level of `up`, given the current levels of every upgrade."""
    level = levels[up["key"]]
    if level == 0:
        return up["base"]
    ramp = up.get("ramp", COST_RAMP)
    inflation = COST_INFLATION ** sum(levels.values())
    return math.ceil(up["base"] * up["growth"] ** level * ramp ** (level * (level - 1) / 2) * inflation)


def is_unlocked(up, levels):
    """Prerequisite upgrades owned (the depth milestone is checked separately: depth_reached)."""
    return all(levels[k] >= n for k, n in up["requires"])


def depth_reached(up, depth):
    return depth >= up["depth"]


def next_milestone(depth):
    """(depth, [upgrades]) for the next depth that unlocks something, or None once everything is open."""
    ahead = sorted({u["depth"] for u in UPGRADES if u["depth"] > depth})
    if not ahead:
        return None
    return ahead[0], [u for u in UPGRADES if u["depth"] == ahead[0]]


def is_maxed(up, levels):
    return up["max"] is not None and levels[up["key"]] >= up["max"]
