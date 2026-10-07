"""Upgrades: stat formulas, the five branches of the upgrade star map and their node definitions.

The map is a ring of five sectors around a core, one per branch, in TABS order clockwise from the top (each
next to the branches it shares most with). `pos` = (degrees, ring): where the upgrade's star sits, as an angle
from the middle of its branch's sector (clockwise) and a ring counted out from the core (may be fractional).
An upgrade can require upgrades from a neighbouring branch: those paths cross between the sectors.
"""
import math

from .util import fmt

# ----- stat formulas -------------------------------------------------------
# Crew
def miner_count(lv): return lv   # you start with no miners: every one is hired
def walk_speed(lv): return 1.6 * (1 + 0.15 * lv)
def second_wind_boost(lv): return 0.2 * lv            # extra swing speed for 8s after clearing a layer
def coffee_interval(lv): return 45 - 5 * lv           # Coffee Break: seconds between rounds of coffee...
def coffee_cups(lv): return 1 + (lv - 1) // 2         # ...how many diggers get a cup each round...
COFFEE_BOOST, COFFEE_SECS = 0.75, 8.0                 # ...each worth this much extra swing speed, for this long
def demo_interval(lv): return max(2.5, 7 - 0.9 * lv)   # seconds between a demolitionist's charges
def medic_heal(lv): return 0.04 + 0.02 * lv           # Medic: share of a patient's max health healed per second
def veteran_level(lv): return 1 + lv                  # Veterans: the level new crew start at
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
def phantom_interval(lv): return 24 - 3.2 * lv        # Phantom Slam: seconds between the ghostly hand's slams...
PHANTOM_CHARGE = 0.6                                  # ...each charged this far (a full slam you charge beats it),
PHANTOM_WINDUP = 1.2                                  # ...after hanging over its block this long, charging up
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
def miner_regen(lv): return 0.015 + 0.0075 * lv       # share of max health healed per second
def wisp_slow(lv): return 0.15 * lv                   # Spirit Lantern: wisps near the crew slow down
def trap_share(lv): return 0.05 * lv                  # Booby Traps: share of max hp taken on arrival
def ballista_interval(lv): return max(1.2, 3.2 - 0.4 * lv)
def ballista_share(lv): return 0.06 + 0.015 * lv      # Ballista: share of max hp per bolt
# Specialist counters (never bosses):
def holy_bonus(lv): return 0.25 * lv                  # Holy Water: extra damage zombies and skeletons take
def boiler_charge(lv): return 180 - 30 * lv           # Steam Boiler: seconds to build up a full head of steam
def torch_singe(lv): return 0.15 * lv                 # Torches: share of a spider's max hp burnt off as it lands...
def torch_grip(lv): return 1 - 0.15 * lv              # ...and how hard spiders still drain the grabbed
def garlic_ward(lv): return 0.25 * lv                 # Garlic: vampires drain and heal this much less...
def garlic_delay(lv): return 1 + 0.5 * lv             # ...and bats take this many times longer to turn
def salt_single(lv): return 0.3 * lv                  # Rock Salt: chance a slime bursts into one slimeling, not two...
def salt_shrivel(lv): return 0.04 * lv                # ...and share of max hp a slimeling shrivels away per second
# Combat meets Fortune:
def trophy_mult(lv): return 1 + 0.5 * lv              # Trophy Hunter: elite bounties are worth this many times more
def spree_step(lv): return 0.05 * lv                  # Killing Spree: extra bounty per kill already in the spree
SPREE_WINDOW, SPREE_CAP = 3.0, 8                      # ...kills this close together count, up to this many


TABS = ["crew", "tools", "hands", "fortune", "combat"]   # (also the star map's sectors, clockwise from the top)
BRANCHES = {
    "crew":    dict(name="Crew",    color=(90, 170, 240),  blurb="Hire specialists and keep the crew on the move"),
    "tools":   dict(name="Tools",   color=(240, 120, 80),  blurb="How hard, fast and far your crew strikes"),
    "hands":   dict(name="Hands",   color=(190, 110, 235), blurb="Your own clicks, blasts and slams"),
    "fortune": dict(name="Fortune", color=(100, 210, 120), blurb="Squeeze more gold out of every block and beast"),
    "combat":  dict(name="Combat",  color=(235, 85, 85),   blurb="Fight back, and keep the crew alive"),
}


def _up(key, name, branch, icon, pos, requires, base, growth, max_lv, desc, effect):
    return dict(key=key, name=name, branch=branch, icon=icon, pos=pos, requires=requires,
                base=base, growth=growth, max=max_lv, desc=desc, effect=effect)


UPGRADES = [
    # ----- Crew ---------------------------------------------------------------
    _up("miners", "Hire Miner", "crew", "miner", (0, 0), [], 30, 2.1, 16,
        "Another miner joins the dig.",
        lambda l: f"{miner_count(l)} miner{'s' if miner_count(l) != 1 else ''} hired"),
    _up("boots", "Mining Boots", "tools", "boot", (-35, 0.5), [("power", 1)], 25, 1.6, 15,
        "Miners walk between blocks faster.", lambda l: f"{walk_speed(l):.1f} tiles / s"),
    _up("teamwork", "Teamwork", "crew", "team", (22, 1.6), [("miners", 1)], 1100, 2.0, 10,
        "Every miner on the crew boosts everyone's damage.", lambda l: f"+{3 * l}% dmg per miner"),
    _up("foreman", "Foreman", "crew", "crown", (24, 3), [("teamwork", 1)], 95000, 2.5, 5,
        "Hire a foreman who walks the site barking orders. While they're alive the whole crew swings "
        "faster, and miners they're standing near faster still.",
        lambda l: f"+{round(100 * (1 / 0.9 ** l - 1))}% swing speed"),
    _up("coffee", "Coffee Break", "crew", "mug", (0, 1), [("miners", 1)], 150, 1.9, 5,
        f"Every so often the crew take a coffee break: a digger downs a mug and swings {round(100 * COFFEE_BOOST)}% "
        f"faster for {COFFEE_SECS:.0f} seconds. More levels, more rounds - and more cups in each.",
        lambda l: "no coffee" if l == 0 else
        f"{coffee_cups(l)} cup{'s' if coffee_cups(l) != 1 else ''} every {coffee_interval(l)}s"),
    _up("secondwind", "Second Wind", "crew", "wind", (2, 2.4), [("coffee", 1)], 5400, 2.0, 5,
        "Clearing a layer gives the crew a burst of speed.",
        lambda l: f"+{round(100 * second_wind_boost(l))}% swing speed for 8s"),
    _up("driller", "Hire Driller", "crew", "jackhammer", (-22, 1), [("miners", 1)], 800, 2.2, 5,
        "A stocky driller with a jackhammer: double health and slow on their feet, but hammers through "
        "blocks almost twice as fast as a miner.", lambda l: f"{l} driller{'s' if l != 1 else ''}"),
    _up("guard", "Hire Guard", "crew", "lantern", (-27, 2), [("driller", 1), ("defense", 1)], 12000, 2.4, 4,
        "A burly guard who patrols the dig and fights monsters on their own, rushing to anyone being grabbed.",
        lambda l: f"{l} guard{'s' if l != 1 else ''}"),
    _up("demolition", "Demolitionist", "crew", "tnt", (-19, 3), [("guard", 1)], 250000, 2.6, 5,
        "Hire a demolitionist who plants charges where the blocks are thickest: each one levels every "
        "block in a 3x3. More levels, more charges.",
        lambda l: "no demolitionist" if l == 0 else f"a 3x3 charge every {demo_interval(l):.1f}s"),
    _up("medic", "Hire Medic", "crew", "medkit", (-33, 3), [("guard", 1), ("firstaid", 1)], 77000, 2.4, 5,
        "A medic who rushes to whoever is hurt - anyone being grabbed first - and patches them up. Only one ever "
        "signs on: more levels, better medicine.",
        lambda l: "no medic" if l == 0 else f"heals {round(100 * medic_heal(l))}% of health / s"),
    _up("veterans", "Veterans", "crew", "chevrons", (16, 3.75), [("foreman", 1)], 170000, 2.5, 4,
        "Hire experienced hands: new crew, and the replacements for the fallen, arrive already trained.",
        lambda l: f"new crew start at level {veteran_level(l)}"),
    _up("graveyardshift", "Graveyard Shift", "crew", "grave", (6, 4.3), [("veterans", 1), ("secondwind", 1)],
        120000, 2.8, 5, "The dead clock back in: fallen crew rise from the graveyard as ghosts and dig on at the "
        "level they died at. Monsters can't touch them.",
        lambda l: f"up to {l} ghost{'s' if l != 1 else ''} from the graveyard"),

    # ----- Tools --------------------------------------------------------------
    _up("power", "Sharper Pickaxe", "tools", "pick", (0, 0), [("miners", 1)], 15, 1.55, None,   # (needs a miner)
        "Miners hit harder.", lambda l: f"{fmt(miner_damage(l))} dmg / hit"),
    _up("speed", "Swing Speed", "tools", "clock", (22, 1), [("power", 1)], 40, 1.7, 25,
        "Miners swing faster.", lambda l: f"{swing_time(l):.2f}s / swing"),
    _up("crit", "Lucky Strikes", "tools", "star", (24, 2), [("speed", 1)], 220, 1.9, 10,
        "Miner hits can crit for triple damage.", lambda l: f"{5 * l}% crit chance"),
    _up("quake", "Seismic Strikes", "tools", "bolt", (27, 3), [("crit", 1), ("shockwave", 1)], 10000, 2.1, 5,
        "Crits shake the four neighbouring blocks.", lambda l: f"crits splash {25 * l}%"),
    _up("diamond", "Diamond Tips", "tools", "tip", (0, 1), [("power", 1)], 120, 1.8, 10,
        "Miners hit ore blocks much harder.", lambda l: f"x{ore_damage_mult(l):.2f} dmg vs ore"),
    _up("deepstrike", "Deep Strike", "tools", "drill", (0, 2), [("diamond", 1)], 2600, 2.0, 5,
        "Miner hits also crack the block underneath.", lambda l: f"{10 * l}% to the layer below"),
    _up("streak", "Hot Streak", "tools", "flame", (-22, 1), [("power", 1)], 300, 1.9, 10,
        "Every hit on the same block lands harder than the last (up to 10 in a row).",
        lambda l: f"+{round(100 * streak_bonus(l))}% dmg per hit in a row"),
    _up("vein", "Vein Follower", "tools", "vein", (-24, 2), [("streak", 1)], 11000, 2.1, 5,
        "A miner breaking ore cracks all the same ore connected to it.",
        lambda l: f"{round(100 * vein_share(l))}% to connected ore"),
    _up("whetstone", "Whetstone", "tools", "whetstone", (-27, 3), [("vein", 1), ("teamwork", 1)], 130000, 2.4, 5,
        "A sharpening wheel on site: miners take turns sharpening, and hit harder for 45s after.",
        lambda l: f"+{round(100 * whetstone_boost(l))}% dmg when sharp"),
    _up("masterwork", "Earthshaker", "tools", "boulder", (10, 4), [("quake", 1), ("deepstrike", 1)],
        100000, 2.6, 5, "Every blow the crew lands rings through the rock: all their digging hits harder.",
        lambda l: f"x{masterwork_mult(l):.2f} miner dmg"),

    # ----- Hands --------------------------------------------------------------
    _up("click", "Power Gloves", "hands", "hand", (-8, 0), [], 10, 1.45, None,
        "Your clicks hit blocks harder.", lambda l: f"{fmt(click_damage(l))} dmg / click"),
    _up("shockwave", "Shockwave", "hands", "wave", (-22, 1), [("click", 1)], 120, 1.9, 5,
        "Your clicks splash onto neighbouring blocks.", lambda l: f"clicks splash {20 * l}%"),
    _up("autotap", "Auto-Tapper", "hands", "cursor", (-24, 2), [("shockwave", 1)], 9200, 2.0, 10,
        "A ghostly hand clicks random blocks for you.", lambda l: f"{l} taps / s"),
    _up("dynamite", "Dynamite", "hands", "bomb", (-24, 3), [("autotap", 1)], 280000, 2.5, 6,
        "Blasts an area for 10x click damage now and then.",
        lambda l: "no dynamite" if l == 0 else f"boom every {dynamite_interval(l)}s"),
    _up("phantom", "Phantom Slam", "hands", "phantom", (-6, 4.3), [("autotap", 1), ("slam", 1)], 270000, 2.8, 5,
        "The Auto-Tapper's ghostly hand learns to slam: every so often it charges up over the blocks and "
        "brings down a Charged Slam of its own, wherever it will hit the most.",
        lambda l: "no phantom slams" if l == 0 else f"a slam every {phantom_interval(l):.0f}s"),
    _up("bigbombs", "Bigger Bombs", "hands", "bigbomb", (-20, 4), [("dynamite", 1)], 240000, 3.0, 2,
        "Dynamite blasts cover a wider area.", lambda l: f"{3 + 2 * l}x{3 + 2 * l} blast"),
    _up("combo", "Combo Clicks", "hands", "combo", (0, 1), [("click", 1)], 150, 1.8, 10,
        "Clicking quickly builds a combo that powers up your clicks (up to 20 in a row).",
        lambda l: f"up to x{1 + 20 * combo_step(l):.1f} at a full combo"),
    _up("goldblock", "Golden Blocks", "hands", "goldblock", (26, 1), [("golden", 1)], 1400, 2.2, 5,
        "Every so often a block turns to gold for a few seconds. Click it for a jackpot!",
        lambda l: "none" if l == 0 else f"every {golden_interval(l)}s, worth {golden_payout(l)}x"),
    _up("slam", "Charged Slam", "hands", "slam", (4, 3), [("steady", 1)], 76000, 2.4, 5,
        "Hold the mouse anywhere on the dig to charge, release for a huge slam that shakes the blocks "
        "and monsters around.",
        lambda l: f"up to {slam_mult(l)}x click dmg"),
    _up("golden", "Golden Touch", "hands", "touch", (22, 0), [], 15, 1.75, 10,   # first Hands buy
        "Your own clicks on blocks earn gold as you dig.", lambda l: f"{5 * l}% of block value / click"),
    _up("steady", "Steady Hands", "hands", "target", (2, 2), [("combo", 1)], 800, 1.9, 10,
        "Your clicks on blocks can crit for triple damage.", lambda l: f"{5 * l}% click crit chance"),

    # ----- Fortune ------------------------------------------------------------
    _up("value", "Hard Bargain", "fortune", "coin", (0, 0), [], 75, 1.75, None,
        "You drive a hard bargain: everything you dig up sells for more.",
        lambda l: f"x{value_mult(l):.2f} sale value"),
    _up("prospector", "Prospector", "fortune", "gem", (-22, 1), [("value", 1)], 320, 1.9, 10,
        "New layers hold more ore, and richer ore: the rarer kinds turn up more often.",
        lambda l: f"x{ore_mult(l):.2f} ore, x{ore_richness(l):.2f} richer"),
    _up("double", "Double Haul", "fortune", "coins", (-26, 2), [("prospector", 1), ("golden", 1)], 4100, 2.0, 10,
        "Broken blocks sometimes pay out twice.", lambda l: f"{4 * l}% double pay"),
    _up("goldrush", "Gold Rush", "fortune", "nugget", (-24, 3), [("double", 1)], 380000, 2.5, 5,
        "Broken blocks may drop a nugget worth 25x.", lambda l: f"{2 * l}% nugget chance"),
    _up("bounty", "Bounty Hunter", "fortune", "skull", (22, 1), [("value", 1), ("slayer", 1)], 100, 1.7, 10,
        "Monsters pay out bigger bounties.", lambda l: f"x{bounty_mult(l):.1f} bounties"),
    _up("golddust", "Gold Dust", "fortune", "bag", (-33, 3.6), [("goldblock", 1)], 4800, 2.2, 5,
        "Every click shakes loose gold: a share of what the damage it deals is worth, on blocks and monsters.",
        lambda l: f"{round(100 * dust_share(l))}% of damage dealt as gold"),
    _up("surveyor", "Surveyor's Contract", "fortune", "scroll", (0, 1), [("value", 1)], 400, 2.0, 5,
        "Bigger bonuses for clearing layers, and for milestones.",
        lambda l: f"{round(100 * clear_share(l))}% clear bonus, x{milestone_mult(l):.1f} milestones"),
    _up("treasure", "Treasure Map", "fortune", "map", (-4, 1.9), [("surveyor", 1)], 150, 1.9, 5,
        "Miners go for ore first, and ore sells for more.", lambda l: f"+{10 * l}% ore value"),
    _up("chests", "Buried Treasure", "fortune", "chest", (-12, 2.7), [("treasure", 1), ("prospector", 1)], 8900, 2.2,
        5,
        "Some blocks in new layers hide a treasure chest that bursts open when broken.",
        lambda l: f"{l}% of blocks hide a chest"),
    _up("vault", "Gold Vault", "fortune", "vault", (8, 3.2), [("chests", 1)], 160000, 2.5, 5,
        "Earn interest on your banked gold every minute (capped by your income).",
        lambda l: f"{round(100 * vault_rate(l))}% interest / minute"),
    _up("trophy", "Trophy Hunter", "fortune", "trophy", (31, 2.7), [("bounty", 1), ("smite", 1)], 59000, 2.5, 5,
        "Elite monsters are worth hunting: their bounties pay far more, and each one goes up in a burst of gold.",
        lambda l: f"elite bounties x{trophy_mult(l):.1f}"),
    _up("spree", "Killing Spree", "fortune", "spree", (29, 3.8), [("trophy", 1), ("cleave", 1)], 150000, 2.6, 5,
        f"Kills in quick succession (within {SPREE_WINDOW:.0f}s of each other) build a spree: every kill in it pays "
        f"a bigger bounty than the last, up to {SPREE_CAP} in a row.",
        lambda l: f"+{round(100 * spree_step(l))}% bounty per kill in a row"),
    _up("midas", "Midas Touch", "fortune", "sun", (0, 4.2), [("goldrush", 1), ("golddust", 1)],
        220000, 2.6, 5, "Every source of gold pays more.", lambda l: f"x{midas_mult(l):.1f} all gold"),

    # ----- Combat -------------------------------------------------------------
    _up("slayer", "Monster Slayer", "combat", "sword", (0, 0), [], 25, 1.5, None,
        "Your clicks hit monsters harder (separate from block damage).",
        lambda l: f"{fmt(monster_damage(l))} dmg / click on monsters"),
    _up("executioner", "Executioner", "combat", "axe", (-27, 1), [("slayer", 1)], 60, 1.6, 17,
        "Every hit you land takes at least a share of a monster's health.",
        lambda l: f"min {enemy_hit_floor(l):.0%} of max hp / hit"),
    _up("smite", "Critical Smite", "combat", "burst", (-28, 2), [("executioner", 1)], 450, 1.9, 10,
        "Your hits on monsters can crit for triple damage.", lambda l: f"{5 * l}% smite chance"),
    _up("cleave", "Cleave", "combat", "slash", (-28, 3), [("smite", 1)], 7200, 2.1, 5,
        "Hitting a monster also hits other monsters close by.", lambda l: f"{20 * l}% to monsters nearby"),
    _up("defense", "Self Defense", "combat", "shield", (27, 1), [("slayer", 1)], 80, 1.7, 10,
        "Grabbed miners fight back, striking their attacker once a second: it buys time until help arrives.",
        lambda l: "miners can't fight back" if l == 0 else f"{100 * miner_strike(l):.1f}% of attacker hp / strike"),
    _up("hardhats", "Hard Hats", "combat", "helmet", (28, 2), [("defense", 1)], 240, 1.8, 8,
        "Miners survive longer when grabbed.", lambda l: f"{miner_max_hp(l):.1f} miner hp"),
    _up("firstaid", "First Aid", "combat", "cross", (28, 3), [("hardhats", 1)], 1900, 2.0, 6,
        "Miners heal faster once they've had a breather.",
        lambda l: f"heal {100 * miner_regen(l):.1f}% of health/s"),
    _up("spiritlantern", "Spirit Lantern", "combat", "spiritlamp", (3, 3.35), [("holywater", 1)], 17000, 2.5, 3,
        "Blue spirit-light on every helmet: ghosts can't fade out, and wisps slow down near the crew.",
        lambda l: "no lanterns" if l == 0 else f"no fading, wisps -{round(100 * wisp_slow(l))}% speed"),
    _up("traps", "Booby Traps", "combat", "spikes", (-9, 1), [("slayer", 1)], 35000, 2.2, 5,
        "Spikes punch up into monsters as they climb out of the ground or drop in.",
        lambda l: f"{round(100 * trap_share(l))}% of max hp on arrival"),
    _up("ballista", "Ballista", "combat", "ballista", (-10, 2), [("traps", 1)], 180000, 2.5, 5,
        "A crossbow turret on the corner of the dig that fires bolts at monsters.",
        lambda l: "no ballista" if l == 0 else
        f"a bolt every {ballista_interval(l):.1f}s, {round(100 * ballista_share(l))}% of max hp"),
    # specialist counters for the regular monsters (bosses shrug them off), fanning out from the Ballista
    _up("holywater", "Holy Water", "combat", "holywater", (9, 1.3), [("slayer", 1)], 1600, 2.6, 3,
        "Blessed water on every pick and bolt: zombies and skeletons take more damage from everything.",
        lambda l: f"+{round(100 * holy_bonus(l))}% damage to the undead"),
    _up("torches", "Torches", "combat", "torch", (-4, 2.5), [("holywater", 1)], 2900, 2.6, 3,
        "Torches ring the dig: spiders are singed as they drop in, and grip the crew more weakly.",
        lambda l: f"-{round(100 * torch_singe(l))}% hp on landing, -{round(100 * (1 - torch_grip(l)))}% drain"),
    _up("garlic", "Garlic Garlands", "combat", "garlic", (11, 2.75), [("holywater", 1)], 9900, 2.6, 3,
        "Garlic on every helmet: vampires drain and heal less from a bite, and bats take longer to turn into "
        "vampires.",
        lambda l: f"-{round(100 * garlic_ward(l))}% drain, bats turn x{garlic_delay(l):.1f} slower"),
    _up("salt", "Rock Salt", "combat", "salt", (21, 3.4), [("holywater", 1)], 160000, 2.6, 3,
        "Salt scattered on the dig: slimes often burst into just one slimeling, and slimelings shrivel away.",
        lambda l: f"{round(100 * salt_single(l))}% one slimeling, -{round(100 * salt_shrivel(l))}% hp / s"),
    _up("boiler", "Steam Boiler", "combat", "boiler", (-11, 3), [("ballista", 1)], 780000, 2.6, 3,
        "A steam boiler in the corner of the dig slowly builds up pressure. When it's full, click it: scalding "
        "steam rolls across the board and clears it of monsters (bosses stand firm), and the next wave holds back.",
        lambda l: "no boiler" if l == 0 else f"full of steam every {boiler_charge(l) / 60:g} min"),
    _up("laststand", "Last Stand", "combat", "fist", (30, 4), [("firstaid", 1)],
        170000, 2.8, 3, "Miners below 30% health fight back far harder.",
        lambda l: f"x{last_stand_mult(l):.1f} strike when desperate"),
]
# Depth milestones: an upgrade can't be bought until you've dug this deep (as well as owning its
# prerequisites). Gives you something to dig towards - capstones only open up deep down.
UNLOCK_DEPTH = {
    # Crew
    "miners": 0, "coffee": 4, "teamwork": 13, "secondwind": 23, "foreman": 33, "graveyardshift": 45,
    "medic": 29, "veterans": 40,
    "driller": 5, "guard": 19, "demolition": 37,
    "streak": 4, "vein": 20, "whetstone": 34,
    "combo": 4, "goldblock": 10, "slam": 31,
    "surveyor": 3, "chests": 16, "vault": 32,
    "spiritlantern": 24, "traps": 27, "ballista": 36,
    # Tools
    "power": 0, "speed": 1, "boots": 2, "diamond": 3, "crit": 8, "deepstrike": 17, "quake": 28, "masterwork": 43,
    # Hands
    "click": 2, "golden": 0, "shockwave": 3, "steady": 12, "autotap": 25, "dynamite": 39, "bigbombs": 47, "phantom": 46,
    # Fortune
    "value": 0, "bounty": 3, "treasure": 4, "prospector": 6, "double": 18, "golddust": 26, "goldrush": 41, "midas": 48,
    # Combat (monsters show up from depth 1)
    "slayer": 1, "executioner": 2, "defense": 3, "smite": 9, "hardhats": 7, "firstaid": 15, "cleave": 22,
    "laststand": 42,
    "holywater": 11, "torches": 14, "garlic": 21, "salt": 38,   # (specialist counters)
    "trophy": 30, "spree": 35, "boiler": 44,
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
#    so you can't max everything at once and have to choose what to push (3%: the star map has
#    ~60 upgrades now, and a first level of each adds up - at 4% a late game ran to x1400 on everything)
COST_RAMP = 1.06
COST_INFLATION = 1.03


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
    """Prerequisites within the upgrade's own branch (the rest cross over from a neighbouring one)."""
    return [(k, n) for k, n in up["requires"] if UPGRADE_BY_KEY[k]["branch"] == up["branch"]]


SECTOR_DEG = 360 / len(TABS)
RING_IN, RING_STEP = 230, 160   # map units from the core to the first ring, and between rings


def sector_angle(branch):
    """Middle of a branch's sector, in degrees clockwise from straight up."""
    return TABS.index(branch) * SECTOR_DEG


def star_xy(deg, ring):
    """Map position (x right, y down; the core at 0, 0) of a point `deg` clockwise from up, on `ring`."""
    a = math.radians(deg)
    r = RING_IN + ring * RING_STEP
    return r * math.sin(a), -r * math.cos(a)


def star_pos(up):
    """Where an upgrade's star sits on the map."""
    deg, ring = up["pos"]
    return star_xy(sector_angle(up["branch"]) + deg, ring)


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
