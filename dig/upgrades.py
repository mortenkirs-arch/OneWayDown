"""Upgrades: stat formulas, the five upgrade menus (tabs) and their node definitions.

Each upgrade lives in one tab ("branch") and forms a small branching tree inside it.
`pos` = (column, tier) within that tab's tree; columns may be fractional.
"""
import math

from .util import fmt

# ----- stat formulas -------------------------------------------------------
# Crew
def miner_count(lv): return lv   # you start with no miners: every one is hired
def walk_speed(lv): return 1.6 * (1 + 0.15 * lv)
def second_wind_boost(lv): return 0.2 * lv            # extra swing speed for 8s after clearing a layer
def demo_interval(lv): return max(2.5, 7 - 0.9 * lv)   # seconds between a demolitionist's charges
# Tools
def miner_damage(lv): return (1 + lv) * 1.08 ** lv
def swing_time(lv): return max(0.15, 0.9 * 0.92 ** lv)
def ore_damage_mult(lv): return 1 + 0.25 * lv         # Diamond Tips, vs ore blocks
def masterwork_mult(lv): return 1.5 ** lv
def streak_bonus(lv): return 0.02 * lv                # Hot Streak: extra damage per consecutive hit
def vein_share(lv): return 0.15 * lv                  # Vein Follower: crack connected ore by this share
def whetstone_boost(lv): return 0.2 + 0.1 * lv if lv else 0.0   # Whetstone: sharpened picks hit this much harder
# Hands (your clicks on BLOCKS)
def click_damage(lv): return (2 + 2 * lv) * 1.1 ** lv
def dynamite_interval(lv): return max(4, 16 - 2 * lv)
def combo_step(lv): return 0.005 * lv                 # Combo Clicks: bonus per click in the combo
def golden_interval(lv): return max(15, 60 - 9 * lv)  # Golden Blocks: seconds between golden blocks
def golden_payout(lv): return 20 + 10 * lv            # ...jackpot, in multiples of the block's value
def slam_mult(lv): return 3 + 2 * lv                  # Charged Slam: x click damage at full charge
# Fortune
def value_mult(lv): return 1.2 ** lv
def ore_mult(lv): return 1 + 0.15 * lv                # Prospector: more ore in new layers (capped)...
def ore_richness(lv): return 1 + 0.12 * lv            # ...and rarer kinds of it turning up more often
def bounty_mult(lv): return 1 + 0.5 * lv
def dust_share(lv): return 0.2 * lv                  # Gold Dust: gold per click, as a share of the damage's worth
def midas_mult(lv): return 1 + 0.1 * lv
def clear_share(lv): return 0.25 + 0.05 * lv          # share of a cleared layer paid as a bonus
def milestone_mult(lv): return 2 + 0.2 * lv           # milestone (every 5m) bonus multiplier
def chest_chance(lv): return 0.01 * lv                # Buried Treasure: chance a block hides a chest
def vault_rate(lv): return 0.01 * lv                  # Gold Vault: interest per minute on banked gold
# Combat (your clicks on MONSTERS, and miners fighting back)
def monster_damage(lv): return (4 + 4 * lv) * 1.12 ** lv
def enemy_hit_floor(lv): return min(0.25, 0.08 + 0.01 * lv)   # min share of an enemy's max hp per hit
def miner_strike(lv): return 0.0 if lv == 0 else 0.02 + 0.004 * lv  # share of attacker's max hp per strike
def last_stand_mult(lv): return 1 + 0.5 * lv           # Last Stand: strikes this much harder when desperate
def miner_max_hp(lv): return 10 * (1 + 0.25 * lv)
def respawn_secs(lv): return 15 - 1.5 * lv
def miner_regen(lv): return 0.015 + 0.0075 * lv       # share of max health healed per second
def wisp_slow(lv): return 0.15 * lv                   # Spirit Lantern: wisps near the crew slow down
def trap_share(lv): return 0.05 * lv                  # Booby Traps: share of max hp taken on arrival
def ballista_interval(lv): return max(1.2, 3.2 - 0.4 * lv)
def ballista_share(lv): return 0.06 + 0.015 * lv      # Ballista: share of max hp per bolt


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
    _up("miners", "Hire Miner", "crew", "miner", (1.5, 0), [], 30, 2.1, 16,
        "Another miner joins the dig.",
        lambda l: f"{miner_count(l)} miner{'s' if miner_count(l) != 1 else ''} hired"),
    _up("boots", "Mining Boots", "crew", "boot", (0.5, 1), [("miners", 1)], 25, 1.6, 15,
        "Miners walk between blocks faster.", lambda l: f"{walk_speed(l):.1f} tiles / s"),
    _up("teamwork", "Teamwork", "crew", "team", (0.5, 2), [("boots", 1)], 400, 2.0, 10,
        "Every miner on the crew boosts everyone's damage.", lambda l: f"+{3 * l}% dmg per miner"),
    _up("foreman", "Foreman", "crew", "crown", (0.5, 3), [("teamwork", 1)], 5000, 2.5, 5,
        "Hire a foreman who walks the site barking orders. While they're alive the whole crew swings "
        "faster, and miners they're standing near faster still.",
        lambda l: f"-{round(100 * (1 - 0.9 ** l))}% swing time"),
    _up("treasure", "Treasure Map", "crew", "map", (2.5, 1), [("miners", 1)], 150, 1.9, 5,
        "Miners go for ore first, and ore sells for more.", lambda l: f"+{10 * l}% ore value"),
    _up("secondwind", "Second Wind", "crew", "wind", (2.5, 2), [("treasure", 1)], 500, 2.0, 5,
        "Clearing a layer gives the crew a burst of speed.",
        lambda l: f"+{round(100 * second_wind_boost(l))}% swing speed for 8s"),
    _up("driller", "Hire Driller", "crew", "jackhammer", (1.5, 1), [("miners", 1)], 800, 2.2, 5,
        "A stocky driller with a jackhammer: double health and slow on their feet, but hammers through "
        "blocks almost twice as fast as a miner.", lambda l: f"{l} driller{'s' if l != 1 else ''}"),
    _up("guard", "Hire Guard", "crew", "lantern", (1.5, 2), [("driller", 1)], 3000, 2.4, 4,
        "A burly guard who patrols the dig and fights monsters on their own, rushing to anyone being grabbed.",
        lambda l: f"{l} guard{'s' if l != 1 else ''}"),
    _up("demolition", "Demolitionist", "crew", "tnt", (1.5, 3), [("guard", 1)], 10000, 2.6, 5,
        "Hire a demolitionist who plants charges where the blocks are thickest: each one levels every "
        "block in a 3x3. More levels, more charges.",
        lambda l: "no demolitionist" if l == 0 else f"a 3x3 charge every {demo_interval(l):.1f}s"),
    _up("nightshift", "Night Shift", "crew", "moon", (1.5, 4), [("foreman", 1), ("secondwind", 1)],
        8000, 2.8, 5, "Extra miners on top of the ones you hire.", lambda l: f"+{l} miners"),

    # ----- Tools --------------------------------------------------------------
    _up("power", "Sharper Pickaxe", "tools", "pick", (1.5, 0), [("miners", 1)], 15, 1.55, None,   # (needs a miner)
        "Miners hit harder.", lambda l: f"{fmt(miner_damage(l))} dmg / hit"),
    _up("speed", "Swing Speed", "tools", "clock", (0.5, 1), [("power", 1)], 40, 1.7, 25,
        "Miners swing faster.", lambda l: f"{swing_time(l):.2f}s / swing"),
    _up("crit", "Lucky Strikes", "tools", "star", (0.5, 2), [("speed", 1)], 150, 1.9, 10,
        "Miner hits can crit for triple damage.", lambda l: f"{5 * l}% crit chance"),
    _up("quake", "Seismic Strikes", "tools", "bolt", (0.5, 3), [("crit", 1)], 900, 2.1, 5,
        "Crits shake the four neighbouring blocks.", lambda l: f"crits splash {25 * l}%"),
    _up("diamond", "Diamond Tips", "tools", "tip", (2.5, 1), [("power", 1)], 120, 1.8, 10,
        "Miners hit ore blocks much harder.", lambda l: f"x{ore_damage_mult(l):.2f} dmg vs ore"),
    _up("deepstrike", "Deep Strike", "tools", "drill", (2.5, 2), [("diamond", 1)], 600, 2.0, 5,
        "Miner hits also crack the block underneath.", lambda l: f"{10 * l}% to the layer below"),
    _up("streak", "Hot Streak", "tools", "flame", (1.5, 1), [("power", 1)], 300, 1.9, 10,
        "Every hit on the same block lands harder than the last (up to 10 in a row).",
        lambda l: f"+{round(100 * streak_bonus(l))}% dmg per hit in a row"),
    _up("vein", "Vein Follower", "tools", "vein", (1.5, 2), [("streak", 1)], 1500, 2.1, 5,
        "A miner breaking ore cracks all the same ore connected to it.",
        lambda l: f"{round(100 * vein_share(l))}% to connected ore"),
    _up("whetstone", "Whetstone", "tools", "whetstone", (1.5, 3), [("vein", 1)], 6000, 2.4, 5,
        "A sharpening wheel on site: miners take turns sharpening, and hit harder for 45s after.",
        lambda l: f"+{round(100 * whetstone_boost(l))}% dmg when sharp"),
    _up("masterwork", "Masterwork", "tools", "anvil", (1.5, 4), [("quake", 1), ("deepstrike", 1)],
        6000, 2.6, 5, "Masterfully forged picks for the whole crew.",
        lambda l: f"x{masterwork_mult(l):.2f} miner dmg"),

    # ----- Hands --------------------------------------------------------------
    _up("click", "Power Gloves", "hands", "hand", (1.5, 0), [], 10, 1.45, None,
        "Your clicks hit blocks harder.", lambda l: f"{fmt(click_damage(l))} dmg / click"),
    _up("shockwave", "Shockwave", "hands", "wave", (0.5, 1), [("click", 1)], 120, 1.9, 5,
        "Your clicks splash onto neighbouring blocks.", lambda l: f"clicks splash {20 * l}%"),
    _up("autotap", "Auto-Tapper", "hands", "cursor", (0.5, 2), [("shockwave", 1)], 600, 2.0, 10,
        "A ghostly hand clicks random blocks for you.", lambda l: f"{l} taps / s"),
    _up("dynamite", "Dynamite", "hands", "bomb", (0.5, 3), [("autotap", 1)], 8000, 2.5, 6,
        "Blasts an area for 10x click damage now and then.",
        lambda l: "no dynamite" if l == 0 else f"boom every {dynamite_interval(l)}s"),
    _up("bigbombs", "Bigger Bombs", "hands", "bigbomb", (0.5, 4), [("dynamite", 1)], 15000, 3.0, 2,
        "Dynamite blasts cover a wider area.", lambda l: f"{3 + 2 * l}x{3 + 2 * l} blast"),
    _up("combo", "Combo Clicks", "hands", "combo", (1.5, 1), [("click", 1)], 150, 1.8, 10,
        "Clicking quickly builds a combo that powers up your clicks (up to 20 in a row).",
        lambda l: f"up to x{1 + 20 * combo_step(l):.1f} at a full combo"),
    _up("goldblock", "Golden Blocks", "hands", "goldblock", (1.5, 2), [("combo", 1)], 800, 2.2, 5,
        "Every so often a block turns to gold for a few seconds. Click it for a jackpot!",
        lambda l: "none" if l == 0 else f"every {golden_interval(l)}s, worth {golden_payout(l)}x"),
    _up("slam", "Charged Slam", "hands", "slam", (1.5, 3), [("goldblock", 1)], 4000, 2.4, 5,
        "Hold the mouse anywhere on the dig to charge, release for a huge slam that shakes the blocks "
        "and monsters around.",
        lambda l: f"up to {slam_mult(l)}x click dmg"),
    _up("golden", "Golden Touch", "hands", "touch", (2.5, 0), [], 15, 1.75, 10,   # first Hands buy
        "Your own clicks on blocks earn gold as you dig.", lambda l: f"{5 * l}% of block value / click"),
    _up("steady", "Steady Hands", "hands", "target", (2.5, 1), [("golden", 1)], 300, 1.9, 10,
        "Your clicks on blocks can crit for triple damage.", lambda l: f"{5 * l}% click crit chance"),

    # ----- Fortune ------------------------------------------------------------
    _up("value", "Ore Appraiser", "fortune", "coin", (1.5, 0), [], 75, 1.75, None,
        "Blocks sell for more.", lambda l: f"x{value_mult(l):.2f} block value"),
    _up("prospector", "Prospector", "fortune", "gem", (0.5, 1), [("value", 1)], 250, 1.9, 10,
        "New layers hold more ore, and richer ore: the rarer kinds turn up more often.",
        lambda l: f"x{ore_mult(l):.2f} ore, x{ore_richness(l):.2f} richer"),
    _up("double", "Double Haul", "fortune", "coins", (0.5, 2), [("prospector", 1)], 800, 2.0, 10,
        "Broken blocks sometimes pay out twice.", lambda l: f"{4 * l}% double pay"),
    _up("goldrush", "Gold Rush", "fortune", "nugget", (0.5, 3), [("double", 1)], 12000, 2.5, 5,
        "Broken blocks may drop a nugget worth 25x.", lambda l: f"{2 * l}% nugget chance"),
    _up("bounty", "Bounty Hunter", "fortune", "skull", (2.5, 1), [("value", 1)], 100, 1.7, 10,
        "Monsters pay out bigger bounties.", lambda l: f"x{bounty_mult(l):.1f} bounties"),
    _up("golddust", "Gold Dust", "fortune", "bag", (2.5, 2), [("bounty", 1)], 400, 2.2, 5,
        "Every click shakes loose gold: a share of what the damage it deals is worth, on blocks and monsters.",
        lambda l: f"{round(100 * dust_share(l))}% of damage dealt as gold"),
    _up("surveyor", "Surveyor's Contract", "fortune", "scroll", (1.5, 1), [("value", 1)], 400, 2.0, 5,
        "Bigger bonuses for clearing layers, and for milestones.",
        lambda l: f"{round(100 * clear_share(l))}% clear bonus, x{milestone_mult(l):.1f} milestones"),
    _up("chests", "Buried Treasure", "fortune", "chest", (1.5, 2), [("surveyor", 1)], 2000, 2.2, 5,
        "Some blocks in new layers hide a treasure chest that bursts open when broken.",
        lambda l: f"{l}% of blocks hide a chest"),
    _up("vault", "Gold Vault", "fortune", "vault", (1.5, 3), [("chests", 1)], 9000, 2.5, 5,
        "Earn interest on your banked gold every minute (capped by your income).",
        lambda l: f"{round(100 * vault_rate(l))}% interest / minute"),
    _up("midas", "Midas Touch", "fortune", "sun", (1.5, 4), [("goldrush", 1), ("golddust", 1)],
        15000, 2.6, 5, "Every source of gold pays more.", lambda l: f"x{midas_mult(l):.1f} all gold"),

    # ----- Combat -------------------------------------------------------------
    _up("slayer", "Monster Slayer", "combat", "sword", (1.5, 0), [], 25, 1.5, None,
        "Your clicks hit monsters harder (separate from block damage).",
        lambda l: f"{fmt(monster_damage(l))} dmg / click on monsters"),
    _up("executioner", "Executioner", "combat", "axe", (0.5, 1), [("slayer", 1)], 60, 1.6, 17,
        "Every hit you land takes at least a share of a monster's health.",
        lambda l: f"min {enemy_hit_floor(l):.0%} of max hp / hit"),
    _up("smite", "Critical Smite", "combat", "burst", (0.5, 2), [("executioner", 1)], 250, 1.9, 10,
        "Your hits on monsters can crit for triple damage.", lambda l: f"{5 * l}% smite chance"),
    _up("cleave", "Cleave", "combat", "slash", (0.5, 3), [("smite", 1)], 1200, 2.1, 5,
        "Hitting a monster also hits other monsters close by.", lambda l: f"{20 * l}% to monsters nearby"),
    _up("defense", "Self Defense", "combat", "shield", (2.5, 1), [("slayer", 1)], 80, 1.7, 10,
        "Grabbed miners fight back, striking their attacker once a second: it buys time until help arrives.",
        lambda l: "miners can't fight back" if l == 0 else f"{100 * miner_strike(l):.1f}% of attacker hp / strike"),
    _up("hardhats", "Hard Hats", "combat", "helmet", (2.5, 2), [("defense", 1)], 200, 1.8, 8,
        "Miners survive longer when grabbed.", lambda l: f"{miner_max_hp(l):.1f} miner hp"),
    _up("firstaid", "First Aid", "combat", "cross", (2.5, 3), [("hardhats", 1)], 700, 2.0, 6,
        "Miners heal faster, and replacements for the fallen arrive sooner.",
        lambda l: f"{respawn_secs(l):.1f}s to replace, heal {100 * miner_regen(l):.1f}% of health/s"),
    _up("spiritlantern", "Spirit Lantern", "combat", "spiritlamp", (1.5, 1), [("slayer", 1)], 500, 2.2, 3,
        "Blue spirit-light on every helmet: ghosts can't fade out, and wisps slow down near the crew.",
        lambda l: "no lanterns" if l == 0 else f"ghosts can't phase, wisps -{round(100 * wisp_slow(l))}% speed"),
    _up("traps", "Booby Traps", "combat", "spikes", (1.5, 2), [("spiritlantern", 1)], 2500, 2.2, 5,
        "Spikes punch up into monsters as they climb out of the ground or drop in.",
        lambda l: f"{round(100 * trap_share(l))}% of max hp on arrival"),
    _up("ballista", "Ballista", "combat", "ballista", (1.5, 3), [("traps", 1)], 12000, 2.5, 5,
        "A crossbow turret on the corner of the dig that fires bolts at monsters.",
        lambda l: "no ballista" if l == 0 else
        f"a bolt every {ballista_interval(l):.1f}s, {round(100 * ballista_share(l))}% of max hp"),
    _up("laststand", "Last Stand", "combat", "fist", (1.5, 4), [("cleave", 1), ("firstaid", 1)],
        10000, 2.8, 3, "Miners below 30% health fight back far harder.",
        lambda l: f"x{last_stand_mult(l):.1f} strike when desperate"),
]
# Depth milestones: an upgrade can't be bought until you've dug this deep (as well as owning its
# prerequisites). Gives you something to dig towards - capstones only open up deep down.
UNLOCK_DEPTH = {
    # Crew
    "miners": 0, "boots": 2, "treasure": 4, "teamwork": 8, "secondwind": 10, "foreman": 16, "nightshift": 28,
    "driller": 5, "guard": 11, "demolition": 18,
    "streak": 4, "vein": 9, "whetstone": 16,
    "combo": 4, "goldblock": 7, "slam": 14,
    "surveyor": 3, "chests": 8, "vault": 15,
    "spiritlantern": 9, "traps": 12, "ballista": 20,
    # Tools
    "power": 0, "speed": 1, "diamond": 3, "crit": 6, "deepstrike": 9, "quake": 14, "masterwork": 25,
    # Hands
    "click": 2, "golden": 0, "shockwave": 4, "steady": 7, "autotap": 10, "dynamite": 18, "bigbombs": 30,
    # Fortune
    "value": 0, "bounty": 3, "prospector": 5, "double": 9, "golddust": 12, "goldrush": 20, "midas": 32,
    # Combat (monsters show up from depth 1)
    "slayer": 1, "executioner": 2, "defense": 3, "smite": 6, "hardhats": 6, "firstaid": 10, "cleave": 12,
    "laststand": 24,
}
# A special price for an upgrade's very first level (its normal curve starts after it).
FIRST_LEVEL_PRICE = {"miners": 10}
for _u in UPGRADES:
    _u["depth"] = UNLOCK_DEPTH[_u["key"]]
    if _u["key"] in FIRST_LEVEL_PRICE:
        _u["first"] = FIRST_LEVEL_PRICE[_u["key"]]
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
    if "first" in up:   # e.g. your first miner: a cheap kick-off, then the usual curve from `base`
        if level == 0:
            return up["first"]
        level -= 1
    if level == 0:
        return up["base"]
    ramp = up.get("ramp", COST_RAMP)
    inflation = COST_INFLATION ** sum(levels.values())
    return math.ceil(up["base"] * up["growth"] ** level * ramp ** (level * (level - 1) / 2) * inflation)


def tree_requires(up):
    """Prerequisites within the upgrade's own menu: the paths drawn in its tree. (A requirement from another
    menu, like Sharper Pickaxe needing a miner, still has to be met but has no path to draw.)"""
    return [(k, n) for k, n in up["requires"] if UPGRADE_BY_KEY[k]["branch"] == up["branch"]]


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
