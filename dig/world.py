"""Game simulation: the dig site, miners, mining rules and save data."""
import math
import random
import time

from .achievements import (ACHIEVEMENTS, BLINK_SECS, CHECKED, HIRE_UPGRADES, QUICK_KILL_SECS, SPEED_DEMON_SECS, new_feats,
                           new_run)
from .artifacts import (ARTIFACT_CHANCE, ARTIFACT_MIN_DEPTH, ARTIFACTS, COMMON, FIRST_ARTIFACT_BY, STAT_KIND,
                        TROPHY_OF)
from .biomes import biome_at, block_color
from .blocks import BLOCKS, DEEP_ROCK_FROM, HP_GROWTH, Block, crack_share, generate_layer, layer_value
from .camp import (CAMP_ROLES, ITEMS, HIRES, CLIMB_STYLES, COLLAPSE_SECS, CRUMBLE_FROM, CRUMBLE_SPREAD, EXPEDITION_DEPTH,
                   ROLE_CLIMB, ROPE_DROP)
from .config import BAD, GOLD, GOLD_HUD_COIN, GOOD, GRID, MUTED, TEXT, TILE_H, TILE_W, W
from .dynamite import EXPLOSION_SECS, Bomb
from .effects import (CRIT_BURST_SECS, QUAKE_RADIUS, QUAKE_SPEED, CoinFly, Floater, Particle,
                      Smoke)
from .enemies import (ELITE_HP, boss_minion_cap, boss_minion_mult,
                      BAT_FORM_EVERY, BAT_FORM_SPEED, BITE_BREAK, BITE_HEAL, BITE_SECS, BITE_SHARE, SLAM_FEED_MOST,
                      BONE_THROW_SHARE, BONE_THROW_SECS, CHUNK_APART, CHUNK_CROWD, CHUNK_FLING, BONE_VOLLEY, BONE_VOLLEY_HURT, CHUNK_SPLIT_HP,
                      PILE_HP, PILE_SECS, REFORM_HP, SLIME_SPLIT_AT, SLIME_SPLIT_HP, STALK_PATIENCE, STRIDE_RANGE,
                      STRIDE_SPEED, THROW_ANIM_SECS, THROW_RELEASE, VOLLEY_GAP,
                      SCREECH_EVERY, SCREECH_RADIUS, SCREECH_STUN,
                      BOSS_MAX_MINIONS, BOSS_SLAM_RADIUS, BOSS_TIME_LIMIT, CURSE_EVERY, CURSE_RADIUS, CURSE_SHARE,
                      CURSE_SECS, ENEMY_START_DEPTH, ENEMY_TYPES, ENRAGE_AT, RALLY_RADIUS, RALLY_SPEED,
                      RALLY_TOUGH, SHIELD_MAX, SHIELD_PER_WISP, WEB_SECS, WEB_SLOW, Enemy, boss_for, choose_kind,
                      crew_hp_at, elite_chance,
                      edge_cells, max_enemies, spawn_interval,
                      ELITE_GRIP, GOLEM_ARMOUR, GRIP_FROM, SHADE_DPS, SHADE_RADIUS, SHADE_SLOW,
                      BRO_MOUND_SPEED, BRO_NAMES, BRO_SURFACE_RADIUS,
                      BRO_PEEK_CHANCE, BRO_PEEK_SECS, BRO_SWAP, MOUNTAIN_ARMOUR, MOUNTAIN_HEAVE,
                      VOID_EYE, VOID_EYE_OPEN, VOID_EYE_SHUT, VOID_GLANCE, VOID_BITE, VOID_BITE_RADIUS, VOID_INHALE_EVERY, VOID_INHALE_PULL, VOID_INHALE_RADIUS,
                      VOID_INHALE_SECS, VOID_POOL_DRAIN, VOID_POOL_EVERY,
                      VOID_POOL_SECS, VOID_POOLS)
from .iso import iso
from .world_layout import (BALLISTA_POS, BANNER_BOOST, BANNER_RADIUS, BANNER_REPLANT, BOILER_POS, BOLT_SECS, CHEST_FX_SECS,
                           FRINGE_POWER, FRINGE_RADIUS, FRINGE_VALUE, HEIRLOOM_DEEP, HEIRLOOM_EVERY,
                           BLAST_ARROW_BLOCKS, BLAST_ARROW_RADIUS, GLAZE_BONUS, GLAZE_SECS, WHEEL_LIFE, WHEEL_MAX,
                           CHOMP_EVERY, COLLAR_BITE, COLLAR_EVERY, COLLAR_SWALLOW, DIVINING_CHANCE, FEMUR_SECS,
                           MITTS_CLICKS, PUP_EVERY, PUP_PAYOUT, ROCK_SECS, ROUNDING_OFF, TAXES_HURT, TAXES_REACH,
                           TAXES_SHARE,
                           SPIKE_FX_SECS, STEAM_SECS, WHETSTONE_POS)
from .miners import (CAMP_LOOKS, CRIT_ANIM_SECS, MAX_LEVEL, ROLES, Miner, base_name, level_mult, new_stats, numbered_name,
                     xp_to_next)
from .sprites import bomb_fuse_tip, enemy_anchor
from .upgrades import (BRANCHES, UPGRADES, ballista_interval, ballista_share, chest_chance, clear_share,
                       combo_step, dust_share, golden_interval, golden_payout, milestone_mult, slam_mult, streak_bonus,
                       PHANTOM_CHARGE, PHANTOM_WINDUP, phantom_interval,
                       trap_share, vault_rate, vein_share, whetstone_boost,
                       ACID_HITS, BUNKER_BELOW, CUTDOWN_AT, SWITCH_BLOCKS, SWITCH_MONSTERS, SWITCH_RADIUS, VOLATILE_BLAST, flare_burn, flare_ease, pole_share,
                       garlic_delay, garlic_ward, holy_bonus, salt_shrivel, salt_single, torch_grip, torch_singe,
                       SPREE_CAP, SPREE_WINDOW, spree_step, trophy_mult, boiler_charge,
                       bounty_mult, click_damage, depth_reached, dynamite_interval,
                       effect_level, enemy_hit_floor, is_maxed, ko_secs, is_unlocked, masterwork_mult, midas_mult, miner_count, miner_damage,
                       miner_max_hp, last_stand_mult, miner_regen, miner_strike, monster_damage, ore_damage_mult,
                       ore_mult, ore_richness,
                       COFFEE_BOOST, COFFEE_SECS, coffee_cups, coffee_interval, demo_interval, medic_heal, second_wind_boost, swing_time, upgrade_cost, value_mult,
                       veteran_level, walk_speed)
from .util import fmt

NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))
SECOND_WIND_SECS = 8.0
CASUAL_MONSTERS = 0.5    # Casual mode: waves (and boss minions) bring this share of the monsters...
CASUAL_BOSS_HP = 0.5     # ...bosses have this share of their health...
CASUAL_BLOCK_GOLD = 3.0  # ...and broken blocks pay this many times as much, for the bounties you miss out on
LAST_STAND_HP = 0.3     # miners below this share of their health get the Last Stand bonus
PEP_TALK_RADIUS = 2.5    # tiles: miners this close to the foreman get the pep-talk boost
PEP_TALK_BOOST = 1.15    # their swings are this much faster
FOREMAN_STAND_OFF = 0.7  # how close the foreman walks up to the miner they're supervising
FOREMAN_BARKS = ["Faster!", "Put your backs into it!", "That ore won't dig itself!", "Break's over!",
                 "Mind the monsters!", "Deeper!", "Swing, swing, swing!", "Good work, {name}!",
                 "Is that a nap, {name}?", "Gold doesn't wait!"]
DRILL_HITS_PER_SWING = 7.5   # a driller lands this many small hits in the time a miner swings once...
DRILL_SHARE = 0.25           # ...each worth this much of a miner's hit: ~1.9x a miner's digging
HERO_POWER = 4.0             # the Hero Miner digs as hard as this many miners...
HERO_STRIKE = 0.25           # ...and each rescue blow takes this share of a monster's max health (a heavy blow)...
HERO_SWING = 0.6             # ...this often...
HERO_RESCUE_RANGE = 2.5      # ...for anyone grabbed this close (further off, they keep digging)
FORGE_WORK = 1.6             # Goblin Engineer: seconds rigging a pick...
FORGE_SECS = 40.0            # ...which then stays explosive this long: every hit also blasts...
FORGE_BLAST = 0.15           # ...the 8 blocks round it for this share of the hit (times the goblin's level bonus)...
FORGE_BELOW = 0.10           # ...and cracks the 3x3 underneath for this share (never breaking them, like Deep Strike)
FORGE_FX_GAP = 0.35          # (a digger's blasts show at most this often: a late crew swings dozens of times a second)
ARCHER_DRAW = 0.5            # Archer: seconds between arrows, each hitting like one of your clicks on a monster
                             # (Executioner's minimum and all) times the archer's level bonus: up to 2x...
ARCHER_RANGE = 5.0           # ...from up to this far away
ARROW_SECS = 0.3             # (an arrow's flight)
CHOMP_WADDLE = 0.6           # Chompers: how fast it shuffles about between gobbles (tiles a second)
CHOMP_HOP = 0.7              # Chompers (the camp's Friendly Mimic): every CHOMP_EVERY seconds it hops off to gobble
                             # a block, this long in the air getting there...
CHOMP_PAYOUT = 2.0           # ...and coughs up this many times what the block was worth
LEDGER_CHANCE = 1 / 6        # Crooked Ledger: the share of upgrades bought that never make it onto the page (free)
# Every boss's second trick (World.boss_second_trick): how often, and what it does
SECOND_TRICK_FIRST = 6.0     # seconds into a fight before the first one
SECOND_TRICK_EVERY = {"zombieking": 14.0, "broodmother": 13.0, "greatbat": 12.0, "bonetyrant": 16.0,
                      "slimeking": 15.0, "vampirelord": 15.0, "lich": 18.0, "burrowbros": 12.0, "mountain": 11.0,
                      "voidmaw": 16.0}
HAZARD_WARN = 1.5            # a marked spot glows this long before it goes off (Grasping Dead, Sinkholes, Rockslide)
HAZARDS = {   # what each kind does to the crew on its spot: radius (tiles), share of crew health, stun (seconds)
    "grasp": dict(radius=0.75, hurt=0.10, stun=2.5),   # Zombie King: hands burst up and hold them
    "sinkhole": dict(radius=0.8, hurt=0.25, stun=1.5),  # Burrow Brothers: the ground caves in under them
    "rock": dict(radius=0.75, hurt=0.35, stun=0.0),     # The Mountain: a boulder crashes down
}
SILK_SECS = 1.0              # Broodmother's Silk Lash: how long she reels a crew member in for
GUST_RADIUS, GUST_PUSH, GUST_STUN = 3.0, 1.6, 0.6   # Fanged Behemoth's Wing Gust: reach, shove (tiles), daze
CAGE_SECS, CAGE_CLICKS, CAGE_CRUSH = 6.0, 3, 0.4   # Bone Tyrant's Rib Cage: clicks to break it, or it crushes them
TRANCE_SECS = 6.0            # Vampire Lord's Mesmerise: a click snaps them out of it, or it wears off after this long
FLOP_WINDUP = 1.6            # Slime King's Belly Flop: the wind-up before he lands on the marked spot
RAISE_COUNT, RAISE_MAX = 2, 6   # Archlich's Raise the Fallen: skeletons raised at a time, and at most on the board
GAZE_SECS, GAZE_HURT = 2.5, 0.5   # The Void Maw's Gaze: time to strike the eye, and the share of health it sears
ROD_EVERY, ROD_SECS = 25.0, 20.0   # Lightning Rod: Grizzle plants one this often; it crackles away this long...
ROD_ARC, ROD_RANGE = 0.5, 2.2       # ...throwing an arc this often, at a block or monster this close...
ROD_BLOCK, ROD_MONSTER = 0.12, 0.15  # ...cracking off this share of a block, or of a monster's health
ARC_SECS = 0.25                      # (an arc's flicker on screen)
WOUND_UP = 0.4                       # Clockwork Toolkit: rigged picks swing this much faster
WATCH_EVERY, WATCH_STOP = 30.0, 3.0  # Pocket Watch: this often, time stops for the monsters this long
GEARS_TICK = 1.25                    # Clockwork Gears: every timed thing comes round this many times as often
KILN_SHOVE, KILN_RADIUS = 1.2, 2.0   # Kiln: Mitts' landings shove monsters this far, from this close
MUDLING_SECS, MUDLING_MAX = 10.0, 2      # Clay Pit: a mudling digs this long, and at most this many at once...
MUDLING_SWING, MUDLING_POWER = 0.8, 2.0  # ...striking this often, for this many of a crew member's strikes...
MUDLING_SPEED = 1.2                      # ...waddling this fast (tiles a second)
DUMMY_EVERY = 20.0           # Target Dummy (the camp's Combat Tent): Wren plants one this often...
DUMMY_LURE = 3.5             # ...monsters this close go for it instead of the crew...
DUMMY_BLAST, DUMMY_RADIUS = 0.6, 1.6   # ...and when one grabs it, it blows: this share of the monsters' health
                             # round it (times Wren's level bonus), within this far, and half the blocks' beneath
FIRE_EVERY = 4               # Fire Arrows: every this many arrows is a fire arrow...
FIRE_SPLASH, FIRE_RADIUS = 0.5, 1.2   # ...bursting for this share of its hit on the monsters within this of its target
STROLL_EVERY = (3.0, 6.0)    # helpers with nothing to do pick somewhere new to amble to this often (seconds)...
STROLL_PAUSE = 0.3           # ...or, this often, just stand a while...
STROLL_PACE = 0.3            # ...and amble at this share of their usual pace
MITTS_LEAP = 0.45            # Clay Golem: every MITTS_CLICKS of your clicks, Mitts leaps to where you clicked,
                             # this long in the air, fists up, and comes down in a slam...
MITTS_FOLLOW = 0.5           # ...a Charged Slam of yours charged at least this far brings him leaping in after it...
MITTS_IDLE = 10.0            # ...left to himself (no clicks of yours this long), he goes anyway, to the thick of it...
MITTS_CRACK = 0.15           # ...levelling the block under him and taking this share of the 8 round it (times his
                             # level bonus; deep rock only cracks: blocks.crack_share) - or your slam, if that's more
TAX_BLOCKS = 1.0             # Tax Collector: each crew member pays this many average blocks' worth of gold...
TAX_DEEPER = 50              # ...and one more for every this many metres down (a bigger crew, bigger takings),
                             # times his level bonus...
TAX_PAUSE = 1.0              # ...and he stops this long with each to write it in the ledger
GUARD_SWING = 0.7            # seconds between a guard's shovel blows
GUARD_SHARE = 0.08           # each blow takes this share of a monster's max health (~9s to fell one alone)...
GUARD_XP_SHARE = 0.5         # ...and experience counts for half as much as for other crew (x1.5 at most)
GUARD_RUSH = 1.4             # guards break into a run when there's a monster to fight
GUARD_REACH = 0.45           # how close a guard gets before swinging
GUARD_ASSIST_SECS = 3.0      # a guard who hit a monster this recently gets the kill, whoever lands the last blow
XP_PER_BLOCK = 1.0           # xp for breaking a whole block (diggers, and the demolitionist's charges)
XP_PER_MONSTER = 4.0         # xp for blows adding up to a whole monster's health (guards, crew fighting back)
XP_PER_ORDER = 1.5           # xp for each order the foreman barks
XP_PER_HEAL = 3.0            # xp for healing a whole health bar's worth (the medic)
MEDIC_REACH = 0.55           # how close the medic gets to a patient to treat them
MEDIC_RUSH = 1.3             # the medic breaks into a run for a patient being grabbed...
MEDIC_GRABBED = 0.5          # ...but heals someone in a monster's grip at this share of the rate
MEDIC_XP_SHARE = 0.5         # the medic's experience counts for half (x1.5 healing at most)
GHOST_POWER = 0.75           # Graveyard Shift: a ghost digs this hard (x the level they died at)
DEFENSE_STRIKE_SECS = 1.0    # Self Defense: a grabbed miner strikes back this often
CHARGE_BOOM = 0.45           # a demolitionist's charge goes off this much quieter than thrown dynamite
GRAB_SOUND_GAP = 1.0         # the "crew grabbed" alert sounds at most this often (seconds)
RESPAWN_SECS = 15.0          # seconds before a fallen crew member's replacement arrives
REGEN_DELAY = 5.0            # crew only start healing once they've gone this long without being hit
ROCK_SHARE = 0.0015          # layer cleared but the boss still up: each rock a digger throws takes this share
                             # of its max health (x the thrower's level bonus)...
ROCK_EVERY = (2.0, 3.0)      # ...one every this many seconds (random in the range)...
ROCK_RANGE = 6.0             # ...from no further than this (tiles)
XP_PER_ROCK = 0.25
FEMUR_SHARE = 0.35           # Tyrant's Femur: each bone takes this share of the grabbing monster's max health
SKIRMISH_KEEP_AWAY = 2.6     # diggers keep at least this far from the boss (clear of its slam)
MAX_FLYING_COINS = 40
MILESTONE_EVERY = 5          # every 5th metre is a milestone with a bigger clear bonus (see Surveyor's Contract)
STREAK_CAP = 10              # Hot Streak: up to this many hits in a row count
CRIT_QUAKE_REACH = 1.3       # crits: a miner's Seismic Strikes wave only reaches the blocks it shakes (a slam's goes further)...
CRIT_QUAKES_SHOWN = 3        # ...and only this many of those waves show at once
COMBO_WINDOW = 0.9           # Combo Clicks: seconds you can pause between clicks before it drops
COMBO_CAP = 20               # ...and the most clicks that count
GOLDEN_SECS = 6.0            # Golden Blocks: how long a golden block lasts
SLAM_CLICK_RATE = 6.0        # Charged Slam: it pays (Golden Touch) for at least this many clicks a second of holding
SLAM_MONSTER_MULT = 2.0      # Charged Slam: a full slam hits monsters for this many monster clicks
GLOVES_TOUGHEN_FROM = 50     # past this depth your clicks toughen with the rock (the deep rock's extra excepted)
CHEST_PAYOUT = 15            # Buried Treasure: chest worth this many times its block's value
DEEP_GOLD = 1.15             # all gold pays this much more once you're deep, easing in from 0m...
DEEP_GOLD_DEPTH = 17         # ...to the full amount here
BONE_BONUS = 2               # breaking a block with bones in it by your own click: this many times its value
VAULT_PERIOD = 60.0          # Gold Vault: interest is paid this often (seconds)
WHET_SHARPEN_SECS = 1.5      # time spent at the wheel
WHET_SHARP_SECS = 45.0       # how long a sharpened pick stays sharp
WHET_GAP = 3.0               # seconds between sending miners to the wheel
BELL_RANGE = 1.0             # Tremor Bells: a Burrower this close to the crew is heard and flushed out...
BELL_HEARD = 4.0             # ...as is one that's been tunnelling this long anywhere
PIERCE_PAST = 4.0            # Ballista: a bolt flies on this many tiles past its target...
PIERCE_WIDTH = 0.6           # ...skewering every monster within this many tiles of its line
COMBAT_TIP_CLICKS = 100      # the first boss suggests Combat upgrades if your clicks would take more than this
COMBAT_TIP_ORDER = ["slayer", "executioner", "smite", "cleave", "defense", "hardhats"]   # ...these first (vs a boss)
                             # many to bring it down
RENAMED_ROLES = {"blacksmith": "engineer"}   # (the Goblin Blacksmith became the Goblin Engineer)
SAVE_VERSION = 2         # bump when the save format changes meaning (see from_dict migrations)
   # cap on coins in the air at once (late game breaks blocks very fast)


class _Spot:
    """A bare position, for effects at a fixed spot on the board."""

    def __init__(self, x, y, z):
        self.x, self.y, self.draw_z = x, y, z


def the(name, capital=False):
    """'Zombie King' -> 'the Zombie King'; 'The Void Maw' stays as it is."""
    if name.lower().startswith("the "):
        return name if capital else "the" + name[3:]
    return ("The " if capital else "the ") + name


def is_ore(block):
    return BLOCKS[block.kind]["ore"] is not None


class Mudling:
    """A Clay Pit mudling: a knee-high lump of clay Mitts' slam threw up, digging until it crumbles."""

    def __init__(self, x, y, secs=MUDLING_SECS):
        self.x, self.y, self.facing = x, y, 1
        self.left, self.swing, self.anim, self.target = secs, MUDLING_SWING, 0.0, None


class LightningRod:
    """Grizzle's Lightning Rod: a copper spike planted in the rock, arcing at whatever's near it until it burns out."""

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.left, self.arc = ROD_SECS, ROD_ARC


class TargetDummy:
    """Wren's Target Dummy: a straw figure stuffed with blasting powder (all it needs is a spot)."""

    def __init__(self, x, y):
        self.x, self.y = x, y


class World:
    def __init__(self, casual=False):
        self.casual = casual               # Casual mode: fewer monsters, softer bosses, richer blocks
        self.gold = 0.0
        self.depth = 0                     # depth index of the current (top) layer
        self.levels = {u["key"]: 0 for u in UPGRADES}
        self.artifacts = []             # keys of the artifacts found, in order
        self.art_stats = {}             # their combined effects (see refresh_artifacts)
        self.total_blocks = 0
        self.expedition = 0
        self.current = generate_layer(0)
        self.next = generate_layer(1)
        self.layer_value = layer_value(self.current)   # base value of the layer being dug (for its clear bonus)
        self.clock = 0.0                   # game-time seconds; stands still while paused
        self.graveyard = []                # records of every miner who has died (see bury())
        self.miners = []
        self.ghosts = []                   # Graveyard Shift: fallen crew back to dig (never grabbed, never saved)
        self.sync_miners()
        self.rise = 0.0                    # layer-shift animation offset (in blocks)
        self.particles = []
        self.floaters = []
        self.rings = []                    # expanding circle effects [x, y, age, max_r, color]
        self.earn_log = []                 # (clock, amount) for the gold / sec estimate
        self.gps_cached = 0.0
        self.tap_timer = 0.0
        self.dynamite_timer = 0.0
        self.enemies = []
        self.enemy_timer = spawn_interval(ENEMY_START_DEPTH)   # seconds until the next wave
        self.announcement = None                                # [text, seconds left]
        self.second_wind = 0.0                                  # seconds of Second Wind left
        self.coffee_timer = 0.0                                 # Coffee Break: seconds since the last cup
        self.phantom_timer = 0.0                                # Phantom Slam: seconds since the last one...
        self.phantom = None                                     # ...and [cell, seconds charging] once it's chosen
        self.spree, self.spree_at = 0, -1e9                     # Killing Spree: kills in a row, and when the last was
        self.boiler = 0.0                                       # Steam Boiler: pressure, 0..1 (full: ready to vent)
        self.golem_tip = False                                  # told the player how to crack a Rock Golem yet
        self.mountain_tip = False                               # ...and the Mountain's plates
        self.void_tip_at = -99.0                                # ...and when we last pointed at the Void Maw's eye
        self.void_pools = []                                    # The Void Maw's pools of darkness: [x, y, age]
        self.expedition = 0                # expeditions finished (each ends at EXPEDITION_DEPTH: Base Camp)
        self.camp = []                     # who's been hired at Base Camp, in order (they survive every reset)
        self.arrows = []                   # the Archer's arrows in flight: [start (x, y), enemy, age, archer]
        self.collapse = None               # seconds since the shaft started coming down (The Void Maw fell), or None
        self.crumble = {}                  # ...and when each cell of the floor gives way
        self.camp_ready = False            # the shaft has come down: time to build at camp
        self.visit_hire = None             # ...and who's been taken on at camp this visit (one per visit; or an item)
        self.camp_items = []               # the camp's items taken so far (camp.ITEMS: they survive every reset too)
        self.achievements = []             # achievements earned, in order (achievements.py: kept for good)...
        self.achievement_queue = []        # ...those still to be announced on the dig...
        self.feats = new_feats()           # ...counts of the things they need that the lifetime record doesn't keep...
        self.run = new_run(0.0)            # ...and how this expedition is going (for the expedition-long ones)
        self.achieve_timer = 0.0           # (the checks run about once a second)
        self.boss_fight_start = 0.0        # game clock when the boss on the board rose (Untouchable)
        self.chomper = None                # Chompers, the camp's tame Mimic, on the dig: {x, y, timer, hop, chomp_at}
        self.pup = None                    # ...and its Mimic Pup, trotting after it (the same)
        self.ledger_lost = False           # the Crooked Ledger just lost an upgrade's receipt (for the upgrades screen)
        self.boss_return = 0.0             # seconds until The Void Maw rises again, after it retreated
        self.lifetime = dict(blocks=0, gold=0.0, monsters=0, bosses=0, expeditions=0, deepest=0)
        self.steam = None                                       # ...and seconds since it last vented (the steam fx)
        self.in_vein = False                                    # Vein Follower: chain guard
        self.bombs = []                                         # dynamite in flight / on a lit fuse
        self.explosions = []                                    # [x, y, age, size_px] fireballs
        self.smoke = []
        self.shake = 0.0                                        # screen-shake seconds left
        self.shake_power = 0.0                                  # max shake offset in px
        self.flash = 0.0                                        # white flash seconds left
        self.coins = []                                         # earned coins flying to the HUD counter
        self.crit_bursts = []                                   # [x, y, age] critical-strike impact flashes
        self.quakes = []                                        # [x, y, age, cells dusted, reach] Seismic Strike waves
        self.gold_bump = 0.0                                    # HUD counter pulse when coins land
        self.notice = None                                      # [text, seconds left] milestone banner
        self.combo = 0                                          # Combo Clicks: clicks in a row...
        self.combo_timer = 0.0                                  # ...and time left before it drops
        self.combo_held = False                                 # mouse held down (charging a slam): it waits
        self.golden = None                                      # Golden Blocks: [cell, seconds left]
        self.golden_timer = 20.0                                # seconds until the next golden block
        self.vault_timer = 0.0                                  # Gold Vault: seconds towards the next payout
        self.whet_timer = 4.0                                   # Whetstone: seconds until the next miner goes
        self.ballista_timer = 2.0                               # Ballista: seconds until the next bolt
        self.ballista_aim = 0.0                                 # direction the ballista is pointing (radians)
        self.bolts = []                                         # [start (x, y), enemy, age] in flight
        self.rocks = []                                         # [thrower, start (x, y), boss, age] in flight
        self.femur_throws = []                                  # [thrower, start (x, y), monster, age]: Tyrant's Femur
        self.femur_timer = 0.0                                  # seconds until the crew can throw the next bone
        self.bone_throws = []                                   # [start (x, y), target miner, age]: Bone Tyrant
        self.chest_fx = []                                      # [x, y, age] treasure chests bursting open
        self.spike_fx = []                                      # [cell, age] Booby Traps springing
        self.new_unlocks = set()                                # upgrades opened up by depth, not yet looked at
        self.new_artifacts = set()                              # found, not yet looked at on the Artifacts page
        self.reveals = []                                       # [artifact key, seconds shown]: found cards,
                                                                # shown one at a time until closed
        self.boss_done = -1                                     # deepest boss depth already fought (won or fled)
        self.boss_gate_told = False                             # told the player the boss bars the way down
        self.webs = {}                                          # Broodmother: {cell: seconds left} slowing the crew
        self.hazards = []                                       # bosses' marked spots: [x, y, kind, left, boss]
        self.dummies = []                                       # Wren's Target Dummies standing on the board
        self.banner = None                                      # [x, y]: where Rocco's planted the Banner of the Deep
        self.glazed = {}                                        # cell -> (depth, until): blocks Mitts has glazed
        self.dowsed = 0                                         # (the last depth his Divining Rod twitched at)
        self.mudlings = []                                      # Clay Pit mudlings digging away
        self.rods = []                                          # Grizzle's Lightning Rods, crackling away
        self.time_stop = 0.0                                    # Pocket Watch: seconds the monsters stay frozen...
        self.watch_timer = 0.0                                  # ...and since it last went off
        self.arcs = []                                          # [rod, (x, y) struck, age]: arcs on screen
        self.cues = []                                          # sound effects to play this frame (see Game.update)
        self.grab_sound_at = -1e9                               # when the last "crew grabbed" alert sounded

    # ----- stats ----------------------------------------------------------
    def pocket_watch(self, dt):
        """Pocket Watch: every WATCH_EVERY seconds, time stops for the monsters for WATCH_STOP."""
        self.watch_timer += dt
        if self.watch_timer < WATCH_EVERY or not self.enemies:
            return
        self.watch_timer, self.time_stop = 0.0, WATCH_STOP
        self.cues.append(("hit", 0.6))
        self.floaters.append(Floater("TIME STOPS!", W / 2, 220, (200, 220, 255), life=WATCH_STOP, size=40))

    def tick(self):
        """Clockwork Gears: how much sooner every timed thing comes round (1 without them)."""
        return GEARS_TICK if "gears" in self.camp_items else 1.0

    def lv(self, key):
        """An upgrade's level, as its effect works at (its ranks, each worth more on the trees: effect_level)."""
        return effect_level(key, self.levels[key])

    def refresh_artifacts(self):
        """Combine the effects of every artifact found (multiply 'mult' stats, add 'add' stats)."""
        stats = {}
        effects = [ARTIFACTS[k]["effects"] for k in self.artifacts]
        for fx in effects:
            for stat, v in fx.items():
                if STAT_KIND[stat] == "add":
                    stats[stat] = stats.get(stat, 0.0) + v
                else:
                    stats[stat] = stats.get(stat, 1.0) * v
        self.art_stats = stats

    # ----- expeditions ----------------------------------------------------------------------------------------
    @property
    def display_depth(self):
        """The depth the player sees: it keeps counting across expeditions (101m, 102m...)."""
        return self.depth + EXPEDITION_DEPTH * self.expedition

    def shown(self, depth):
        """An expedition depth (an upgrade's unlock, say) as the player sees it."""
        return depth + EXPEDITION_DEPTH * self.expedition

    def new_layer(self, depth, *args, **kw):
        """A fresh layer (every expedition's are just like the first's)."""
        return generate_layer(depth, *args, **kw)

    def boss_time_limit(self):
        return BOSS_TIME_LIMIT + self.art_add("boss_time")

    @classmethod
    def next_expedition(cls, old):
        """The shaft has come down and you've been to Base Camp: a fresh expedition starts beneath it with nothing
        but the camp's people (hired straight into old.camp), the graveyard and the lifetime record."""
        w = cls()
        w.expedition = old.expedition + 1
        w.camp = list(old.camp)
        w.camp_items = list(old.camp_items)
        w.achievements, w.feats = list(old.achievements), old.feats
        w.graveyard = old.graveyard
        w.lifetime = dict(old.lifetime)
        w.lifetime["expeditions"] = w.expedition
        w.clock = old.clock
        w.run = new_run(w.clock)
        w.refresh_artifacts()
        w.depth = 1   # (just below the camp: 101m)
        w.current, w.next = w.new_layer(1), w.new_layer(2)
        w.layer_value = layer_value(w.current)
        w.boss_done = 0
        w.gold = w.art_add("start_gold")
        w.miners = []
        w.sync_miners()
        veterans = {m.role: m.to_dict() for m in old.miners if m.role in CAMP_ROLES}
        for m in w.miners:   # the camp's people come along as they were: same level, same record
            if m.role in veterans:
                m.apply_saved(veterans[m.role])
        w.enemy_timer = 4.0   # (the first monsters find the new shaft soon enough)
        w.notice = [f"Expedition {w.expedition + 1}: a new crew, a new shaft - the dig goes on at {w.display_depth}m",
                    6.0, ""]
        return w

    def art_mult(self, stat): return self.art_stats.get(stat, 1.0)

    def art_add(self, stat): return self.art_stats.get(stat, 0)

    def crew_size(self):
        """How many diggers (the foreman is extra)."""
        return miner_count(self.lv("miners")) + int(self.art_add("miners"))

    def workers(self):
        """Everyone the foreman supervises (the whole crew apart from the foreman)."""
        return [m for m in self.miners if not m.is_foreman]

    def diggers(self):
        """Crew who mine blocks: miners and drillers."""
        return [m for m in self.miners if m.digs]

    def wanted_crew(self):
        """How many of each role the upgrades call for."""
        return {"miner": self.crew_size(), "driller": self.lv("driller"), "guard": self.lv("guard"),
                "demolitionist": 1 if self.lv("demolition") else 0, "foreman": 1 if self.lv("foreman") else 0,
                "medic": 1 if self.lv("medic") else 0,   # (only ever one medic: levels make them better)
                **{hire: 1 for hire in getattr(self, "camp", ())}}   # (and the camp's people, once hired)

    def foreman(self):
        """The foreman on site and alive, or None (their bonuses only apply while they are)."""
        return next((m for m in self.miners if m.is_foreman and m.state != "down"), None)

    def miner_hit_damage(self):
        """Miner damage to blocks (before the Diamond Tips bonus on ore)."""
        team = 1 + 0.03 * self.lv("teamwork") * (len(self.diggers()) + len(self.ghosts))
        return (miner_damage(self.lv("power")) * team * masterwork_mult(self.lv("masterwork"))
                * self.art_mult("miner_dmg"))

    def miner_swing_time(self):
        t = swing_time(self.lv("speed"))
        if self.foreman():   # Foreman's crew-wide bonus only while the foreman is alive
            t *= 0.9 ** self.lv("foreman")
        if self.second_wind > 0:
            t /= 1 + second_wind_boost(self.lv("secondwind"))
        return max(0.1, t * self.art_mult("swing"))

    def click_hit_damage(self):
        """Your click damage to blocks."""
        return click_damage(self.lv("click")) * self.art_mult("click_dmg") * self.glove_scale()

    def glove_scale(self):
        """Power Gloves toughen with the rock: past GLOVES_TOUGHEN_FROM a click (and so every slam, blast and tap
        built on one) grows as the blocks do. Not with the deep's harder rock, though - past blocks.DEEP_ROCK_FROM
        your hands slow down along with the crew."""
        return HP_GROWTH ** max(0, self.depth - GLOVES_TOUGHEN_FROM)

    def monster_hit_damage(self):
        """Your click damage to monsters (Combat menu), before the Executioner minimum."""
        return monster_damage(self.lv("slayer")) * self.art_mult("monster_dmg")

    def fly_coins(self, x, y, count):
        """Send little coins arcing from (x, y) up into the HUD gold counter."""
        room = MAX_FLYING_COINS - len(self.coins)
        for i in range(min(count, room)):
            self.coins.append(CoinFly((x, y), GOLD_HUD_COIN, delay=i * 0.06))

    def earn(self, amount):
        """Add gold from any source (Midas Touch and the depth bonus apply to all of it). Returns the amount added."""
        amount *= midas_mult(self.lv("midas")) * self.art_mult("gold") * self.depth_gold_mult()
        self.gold += amount
        self.lifetime["gold"] += amount
        self.earn_log.append((self.clock, amount))
        return amount

    def depth_gold_mult(self):
        """Gold pays more the deeper you are, up to DEEP_GOLD at DEEP_GOLD_DEPTH."""
        return 1 + (DEEP_GOLD - 1) * min(1.0, self.depth / DEEP_GOLD_DEPTH)

    def gold_per_sec(self):
        now = self.clock
        self.earn_log = [(t, a) for t, a in self.earn_log if now - t < 15]
        if self.earn_log:
            span = max(5.0, now - self.earn_log[0][0])
            self.gps_cached = sum(a for _, a in self.earn_log) / span
        return self.gps_cached

    def sync_miners(self, announce=False):
        for m in self.miners:   # Hard Hats: raise max hp, keeping each miner's current share
            max_hp = self.max_hp_for(m.role)
            if m.max_hp != max_hp:
                m.hp *= max_hp / m.max_hp
                m.max_hp = max_hp
        for role, wanted in self.wanted_crew().items():
            while sum(1 for m in self.miners if m.role == role) < wanted:
                miner = self.recruit(role)
                self.miners.append(miner)
                if announce:
                    px, py = self.entity_screen(miner, 60)
                    text = (f"{miner.name} joins the crew!" if role == "miner"
                            else f"{role.capitalize()} {miner.name} arrives on site!")
                    self.floaters.append(Floater(text, px, py, GOOD if role == "miner" else GOLD,
                                                 life=2.2, size=24))

    def sync_ghosts(self, announce=True):
        """Graveyard Shift: a ghost per level, raised from the graveyard (the most experienced first)."""
        wanted = min(self.lv("graveyardshift"), len(self.graveyard))
        if len(self.ghosts) >= wanted:
            return
        risen = {g.name for g in self.ghosts}
        dead = sorted((r for r in self.graveyard if r["name"] not in risen), key=lambda r: -r.get("level", 1))
        for record in dead[:wanted - len(self.ghosts)]:
            ghost = Miner(role="ghost")
            ghost.apply_saved(record)
            ghost.draw_z = self.column_height(*self.cell_of(ghost.x, ghost.y))
            self.ghosts.append(ghost)
            if announce:
                px, py = self.entity_screen(ghost, 60)
                self.floaters.append(Floater(f"{ghost.name} rises for the graveyard shift", px, py, (170, 210, 255),
                                             life=2.4, size=24))
                for _ in range(14):
                    self.particles.append(Particle(px, py + 30, random.choice([(170, 210, 255), (230, 240, 255)])))

    def give_xp(self, m, amount):
        """Experience for a crew member doing their job; levels up as it adds up (to MAX_LEVEL)."""
        if m.level >= MAX_LEVEL or m.role == "ghost":   # (ghosts stay at the level they died at)
            return
        m.xp += amount * self.art_mult("xp")   # (Veteran's Medal)
        while m.level < MAX_LEVEL and m.xp >= xp_to_next(m.level):
            m.xp -= xp_to_next(m.level)
            m.level += 1
            px, py = self.entity_screen(m, 70)
            text = f"{m.name} is a master!" if m.level == MAX_LEVEL else f"{m.name} reached level {m.level}!"
            self.floaters.append(Floater(text, px, py, GOLD, life=1.8, size=24))
            self.rings.append([px, py + 40, 0.0, 50, GOLD])
            for _ in range(10):
                self.particles.append(Particle(px, py + 30, random.choice([GOLD, (255, 255, 220)])))
        if m.level >= MAX_LEVEL:
            m.xp = 0.0

    def max_hp_for(self, role):
        return miner_max_hp(self.lv("hardhats")) * ROLES[role]["hp"] * self.art_mult("miner_hp")

    def recruit(self, role="miner"):
        """A brand-new miner. Shares a fallen miner's name? They become 'Gus II', 'Gus III', ..."""
        miner = Miner(taken_names={base_name(m.name) for m in self.miners}, role=role)
        fallen = sum(1 for g in self.graveyard if base_name(g["name"]) == miner.name)
        if fallen:
            miner.name = numbered_name(miner.name, fallen)
        miner.max_hp = miner.hp = self.max_hp_for(role)
        miner.stats = new_stats(self.display_depth, self.clock)
        miner.level = min(MAX_LEVEL, veteran_level(self.lv("veterans")) + int(self.art_add("start_level")))
        # (Veterans: they turn up already trained)
        if role in CAMP_LOOKS:   # one of the camp's people: always the same face (and starting fresh)
            miner.apply_look(CAMP_LOOKS[role])
            miner.level = 1
        return miner

    def column_height(self, cx, cy):
        return 2 if (cx, cy) in self.current else 1

    @staticmethod
    def cell_of(x, y):
        return int(min(GRID - 1, max(0, x))), int(min(GRID - 1, max(0, y)))

    def cell_screen(self, cell):
        return iso(cell[0] + 0.5, cell[1] + 0.5, 2 + self.rise)

    def entity_screen(self, e, lift=0):
        """Screen position of a miner/enemy, `lift` pixels above its feet."""
        x, y = iso(e.x, e.y, e.draw_z + self.rise)
        return x, y - lift

    # ----- combat ---------------------------------------------------------
    def nearest_free_miner(self, x, y):
        fired = "kiln" in self.camp_items
        free = [m for m in self.miners if m.state == "working" and m.role != "hero"   # (no grip holds a hero...
                and getattr(m, "task", "") != "leaping"                               # ...or Mitts in mid-air...
                and not (fired and m.role == "claygolem")]                            # ...or once he's fired)
        return min(free, key=lambda m: (m.x - x) ** 2 + (m.y - y) ** 2, default=None)

    def spawn_wave(self):
        """Top the board up to the enemy cap for this depth. Returns how many spawned."""
        count = self.enemy_cap() - len(self.enemies)
        if count <= 0:
            return 0
        kinds = [choose_kind(self.depth) for _ in range(count)]
        elites = 0
        for i, cell in enumerate(edge_cells(count)):
            # stagger the emergence so a big wave pops out one after another
            elite = random.random() < elite_chance(self.depth)
            elites += elite
            enemy = Enemy(kinds[i], self.depth, cell, self.column_height(*cell), delay=i * 0.35,
                          hp_mult=self.art_mult("enemy_hp"), elite=elite)
            if enemy.spec.get("lurk"):
                self.hide_mimic(enemy)
            self.enemies.append(enemy)
        if count == 1:
            e = self.enemies[-1]
            msg = f"{'AN' if e.elite else 'A'} {e.name.upper()} {e.spec['arrival'].upper()}!"
        else:
            msg = f"WAVE INCOMING: {count} ENEMIES!" + (f"  ({elites} ELITE)" if elites else "")
        self.cues.append("spawn")   # one sound per wave, not per monster
        self.announcement = [msg, 2.5]   # shown as the HUD banner title
        return count

    # ----- the deep's monsters ---------------------------------------------------------------------------------
    def hide_mimic(self, mimic, cell=None):
        """A Mimic takes its place on a block, disguised as a treasure chest (or, with no blocks, just hunts)."""
        if cell is None:
            free = [c for c in self.current if c not in self.hidden_cells()]
            if not free:
                return
            cell = random.choice(free)
        mimic.x, mimic.y = cell[0] + 0.5, cell[1] + 0.5
        mimic.draw_z = self.column_height(*cell)
        mimic.state, mimic.timer, mimic.lurk_cell = "lurking", 0.0, cell

    def lurker_at(self, cell):
        return next((e for e in self.enemies if e.state == "lurking" and e.lurk_cell == cell), None)

    def hidden_cells(self):
        """Blocks with a Mimic sitting on them."""
        return {e.lurk_cell for e in self.enemies if e.state == "lurking"}

    def surface_burrower(self, burrower, victim=None, quiet=False):
        """A Burrower bursts up out of the ground - under `victim` (grabbing them), or dug out early by a hit."""
        if burrower.state != "burrowing":
            return
        burrower.state = "hunting"
        px, py = self.entity_screen(burrower)
        for _ in range(16):
            self.particles.append(Particle(px, py, random.choice([(110, 84, 60), (80, 60, 44), (140, 110, 80)]),
                                           big=True))
        self.rings.append([px, py, 0.0, 50, (150, 110, 70)])
        self.spring_trap(burrower)
        if victim is None:
            if not quiet:
                self.floaters.append(Floater("Dug out!", px, py - 30, GOOD, life=1.0, size=24))
        elif burrower in self.enemies and victim.state == "working":
            self.grab(burrower, victim)

    def spring_mimic(self, mimic, victim=None):
        """The chest was a Mimic all along: it springs, biting `victim` (the miner digging its block) if any."""
        if mimic.state != "lurking":
            return
        mimic.state = "hunting"
        self.achieve("mimic")
        px, py = enemy_anchor(mimic, self.rise, time.time())
        poles = self.lv("poles") if not mimic.boss else 0   # Ten-Foot Poles: prodded from a safe distance
        self.floaters.append(Floater("Prodded - it's a MIMIC!" if poles else "It's a MIMIC!", px, py - 30,
                                     (230, 170, 90), life=1.4, size=28))
        for _ in range(14):
            self.particles.append(Particle(px, py, random.choice([(150, 100, 60), (230, 180, 60), (90, 55, 30)])))
        if poles:
            self.hit_enemy(mimic, mimic.max_hp * pole_share(poles) * mimic.pct_scale, floor=False,
                           ring=(200, 170, 120))
        elif victim is not None and victim in self.miners and victim.state == "working":
            self.grab(mimic, victim)

    def shade_target(self, shade):
        """Abyssal Shade: the crew member with the most of the crew at work around them (where it smothers most)."""
        working = [m for m in self.miners if m.state == "working"]
        if not working:
            return shade.x, shade.y
        near = lambda m: sum(1 for o in working if math.hypot(o.x - m.x, o.y - m.y) <= SHADE_RADIUS)
        best = max(working, key=lambda m: (near(m), -math.hypot(m.x - shade.x, m.y - shade.y)))
        return best.x, best.y

    def armour(self, enemy, heavy):
        """Rock Golem: how much of a hit gets through its armour. A heavy hit cracks it for good.
        The Mountain: each heavy hit knocks off one stone plate; until the last is gone, blows barely land."""
        if enemy.plates > 0:
            px, py = enemy_anchor(enemy, self.rise, time.time())
            if heavy:
                enemy.plates -= 1
                left = enemy.plates
                self.floaters.append(Floater("A PLATE FALLS!" + (f"  ({left} left)" if left else "  BARE STONE!"),
                                             px, py - 70, (255, 190, 90), life=1.6, size=30))
                self.shake, self.shake_power = 0.3, 5
                for _ in range(26):
                    self.particles.append(Particle(px, py - 30, random.choice([(98, 96, 112), (52, 50, 64),
                                                                               (255, 170, 80)]), big=True))
                return 1.0
            if self.clock - getattr(enemy, "clang_at", -9.0) > 0.8:
                enemy.clang_at = self.clock
                self.floaters.append(Floater("CLANG", px, py - 50, (190, 190, 200), life=0.6, size=22))
            if not self.mountain_tip:
                self.mountain_tip = True
                self.floaters.append(Floater("Its plates only fall to heavy hits - slam it or blast it!", W / 2, 230,
                                             (255, 190, 90), life=3.4, size=28))
            return MOUNTAIN_ARMOUR
        if not enemy.spec.get("armour") or getattr(enemy, "cracked", False):
            return 1.0
        px, py = enemy_anchor(enemy, self.rise, time.time())
        acid = not heavy and self.acid_etch(enemy)
        if heavy or acid:
            enemy.cracked = True
            self.floaters.append(Floater("ACID EATS THROUGH!" if acid else "ARMOUR CRACKED!", px, py - 40,
                                         (170, 240, 110) if acid else (255, 190, 90), life=1.4, size=28))
            for _ in range(20):
                self.particles.append(Particle(px, py, random.choice([(130, 128, 140), (90, 88, 100), (255, 170, 80)]),
                                               big=True))
            return 1.0
        if self.clock - getattr(enemy, "clang_at", -9.0) > 0.8:
            enemy.clang_at = self.clock
            self.floaters.append(Floater("CLANG", px, py - 30, (190, 190, 200), life=0.6, size=20))
        if not self.golem_tip and not self.lv("acid"):   # the first time: say how to get through it
            self.golem_tip = True
            self.floaters.append(Floater("Its stone armour shrugs off blows - slam it or blast it!", W / 2, 230,
                                         (255, 190, 90), life=3.2, size=28))
        return GOLEM_ARMOUR

    def enemy_cap(self):
        """Enemies alive after each wave at this depth (Casual mode: about half as many, never fewer than one)."""
        cap = max_enemies(self.depth)
        return max(1, math.ceil(cap * CASUAL_MONSTERS)) if self.casual else cap

    def wave_interval(self):
        """Seconds between waves at this depth."""
        return spawn_interval(self.depth)

    # ----- bosses ---------------------------------------------------------
    def boss(self):
        """The boss on the board, or None."""
        return next((e for e in self.enemies if e.boss), None)

    def combat_tip(self):
        """During the first boss fight (the Zombie King at 10m): while your clicks would still take a long while to
        bring it down and you can afford a Combat upgrade, (clicks needed, [those upgrades, best for a boss first]).
        Otherwise None. It keeps nudging after a visit to the upgrades: buying a little isn't always enough."""
        boss = self.boss()
        if boss is None or boss.kind != "zombieking" or self.depth != 10 or boss.state == "emerging":
            return None
        per_click = self.enemy_hit_damage(boss, self.monster_hit_damage())
        clicks = math.ceil(boss.hp / per_click)
        if clicks <= COMBAT_TIP_CLICKS:
            return None
        affordable = [u for u in UPGRADES if u["branch"] == "combat" and self.can_buy(u)]
        if not affordable:
            return None
        affordable.sort(key=lambda u: COMBAT_TIP_ORDER.index(u["key"]) if u["key"] in COMBAT_TIP_ORDER else 99)
        return clicks, affordable

    def hurt(self, m, dmg):
        """A crew member takes damage (and won't start healing again until they've had a breather)."""
        m.hp -= dmg
        m.last_hurt = self.clock

    def nearest_crew(self, x, y):
        """Nearest crew member still standing (bosses go for anyone, grabbed or not)."""
        alive = [m for m in self.miners if m.state != "down"]
        return min(alive, key=lambda m: (m.x - x) ** 2 + (m.y - y) ** 2, default=None)

    def spawn_boss(self):
        """The boss guarding this depth rises in the middle of the board."""
        kind = boss_for(self.depth)
        if not kind or self.boss():
            return
        cell = (GRID // 2, GRID // 2)
        hp_mult = self.art_mult("enemy_hp") * (CASUAL_BOSS_HP if self.casual else 1)
        self.enemies.append(Enemy(kind, self.depth, cell, self.column_height(*cell), delay=1.2, hp_mult=hp_mult))
        self.boss_fight_start = self.clock
        spec = ENEMY_TYPES[kind]
        self.announcement = [f"{the(spec['name']).upper()} {spec['arrival'].upper()}!", 4.0]
        self.notice = [f"Boss! Defeat {the(spec['name'])} within {int(self.boss_time_limit())}s for a trophy", 6.0, ""]
        self.boss_gate_told = False
        self.shake, self.shake_power = 0.6, 6
        self.cues.append("spawn")

    def boss_summon(self, boss):
        """The boss calls in a few of its kind around it."""
        if boss.mode == "pile":
            return
        minion = boss.spec["minion"]
        alive = sum(1 for e in self.enemies if not e.boss)
        # deeper bosses call a few more (and keep a few more around)
        count, cap = round(minion["count"] * boss_minion_mult(self.depth)), boss_minion_cap(self.depth)
        if self.casual:   # (half the minions, but always at least one)
            count, cap = max(1, round(count * CASUAL_MONSTERS)), max(1, round(cap * CASUAL_MONSTERS))
        count = min(count, cap - alive)
        if count <= 0:
            return
        cx, cy = self.cell_of(boss.x, boss.y)
        near = [(x, y) for x in range(cx - 2, cx + 3) for y in range(cy - 2, cy + 3)
                if 0 <= x < GRID and 0 <= y < GRID and (x, y) != (cx, cy)]
        kinds = [minion["kind"]] * count + ([minion["plus"]] if "plus" in minion else [])   # (Broodmother: + a spider)
        for i, (kind, cell) in enumerate(zip(kinds, random.sample(near, min(len(kinds), len(near))))):
            # (elite minions too, deep down - but never elite eggs)
            elite = kind != "eggsac" and random.random() < elite_chance(self.depth)
            minion_e = Enemy(kind, self.depth, cell, self.column_height(*cell), delay=i * 0.3,
                             hp_mult=self.art_mult("enemy_hp"), elite=elite)
            if minion_e.spec.get("lurk"):   # (Mimics hide among the blocks)
                self.hide_mimic(minion_e)
            self.enemies.append(minion_e)
        px, py = enemy_anchor(boss, self.rise, time.time())
        text = ("She lays her eggs! Break them!" if minion["kind"] == "eggsac"
                else f"{the(boss.spec['name'], True)} calls for help!")
        self.floaters.append(Floater(text, px, py - 70, BAD, life=1.8, size=24))

    def boss_slam(self, boss):
        """The wind-up ends: the ground around the boss caves in, hurting every crew member in reach."""
        self.cues += ["-windup", "slam"]   # (the growl ends as the slam lands)
        fx, fy = self.entity_screen(boss)
        self.shake, self.shake_power = 0.35, 7
        self.rings.append([fx, fy, 0.0, 150, (255, 90, 60)])
        self.rings.append([fx, fy, 0.0, 90, (255, 200, 150)])
        for _ in range(30):
            self.particles.append(Particle(fx, fy, random.choice([(110, 84, 60), (80, 60, 44), (255, 120, 70)]),
                                           big=True))
        self.floaters.append(Floater("SLAM!", fx, fy - 110, (255, 110, 80), life=1.0, size=36))
        if boss.kind == "broodmother":   # the ground she slams is left webbed over
            r = int(BOSS_SLAM_RADIUS)
            cx, cy = self.cell_of(boss.x, boss.y)
            for x in range(cx - r, cx + r + 1):
                for y in range(cy - r, cy + r + 1):
                    if 0 <= x < GRID and 0 <= y < GRID and math.hypot(x - cx, y - cy) <= BOSS_SLAM_RADIUS:
                        self.webs[(x, y)] = WEB_SECS
        self.slam_crew(boss, BOSS_SLAM_RADIUS)
        if boss.kind == "bonetyrant":   # it backs off to throw bones before coming in again
            self.start_stride(boss)
        elif boss.kind == "mountain":
            self.mountain_heave(boss)

    def slam_crew(self, e, radius):
        """Hurt every crew member within `radius` of a slamming monster (the Slime King's Core softens it)."""
        dmg = e.spec["slam"] * crew_hp_at(e.depth) * self.art_mult("slam_dmg")
        hit = 0
        for m in self.miners:
            if m.state == "down" or math.hypot(m.x - e.x, m.y - e.y) > radius:
                continue
            hit += 1
            self.hurt(m, dmg)
            if e.spec.get("lifesteal") and hit <= SLAM_FEED_MOST:   # the Vampire Lord feeds on the crew it hits
                e.hp = min(e.max_hp, e.hp + e.max_hp * e.spec["lifesteal"])          # (a few of them, at most)
            px, py = self.entity_screen(m, 50)
            self.floaters.append(Floater(f"-{dmg:.0f}", px, py, BAD, life=1.0, size=24))
            if m.hp <= 0:
                if m.attacker:   # whatever had hold of them lets go
                    m.attacker.release()
                self.miner_down(m, killer=e)
        return hit

    def chunk_slam(self, chunk):
        """A Slime King chunk comes down hard: a smaller, weaker slam of its own."""
        self.cues.append(("slam", 0.45))
        fx, fy = self.entity_screen(chunk)
        if self.shake < 0.15:
            self.shake, self.shake_power = 0.15, 3
        self.rings.append([fx, fy, 0.0, 90, (150, 230, 90)])
        for _ in range(12):
            self.particles.append(Particle(fx, fy, random.choice([(150, 220, 70), (90, 160, 50), (200, 250, 150)])))
        self.slam_crew(chunk, chunk.spec["slam_radius"])

    # ----- slimes -------------------------------------------------------------
    def fling_spots(self, slime, count):
        """Where the Slime King's chunks land: spread round him at CHUNK_FLING, on the board, kept CHUNK_APART."""
        spots = []
        for i in range(count):
            best = None
            for _ in range(12):   # (a few tries for a spot clear of the others)
                a = i / count * math.tau + random.uniform(-0.4, 0.4)
                r = random.uniform(*CHUNK_FLING)
                p = (min(GRID - 0.5, max(0.5, slime.x + math.cos(a) * r)),
                     min(GRID - 0.5, max(0.5, slime.y + math.sin(a) * r)))
                room = min((math.hypot(p[0] - q[0], p[1] - q[1]) for q in spots), default=99)
                if best is None or room > best[0]:
                    best = (room, p)
                if room >= CHUNK_APART:
                    break
            spots.append(best[1])
        return spots

    def chunk_landed(self, chunk):
        """A flung chunk hits the ground: a splat where it lands."""
        px, py = enemy_anchor(chunk, self.rise, time.time())
        gore = chunk.spec["gore"]
        for _ in range(8):
            self.particles.append(Particle(px, py, random.choice([gore, tuple(c // 2 for c in gore)])))
        self.rings.append([px, py + 10, 0.0, 40, gore])

    def chunk_target(self, chunk):
        """Who a Slime King chunk goes for: the nearest crew member - but one another chunk is already after counts
        as CHUNK_CROWD tiles further off, so they spread out over the crew instead of mobbing one."""
        crew = [m for m in self.miners if m.state != "down"]
        if not crew:
            return None
        claims = {}
        for e in self.enemies:
            aim = getattr(e, "aim", None) if e is not chunk and e.kind == chunk.kind else None
            if aim is not None:
                claims[id(aim)] = claims.get(id(aim), 0) + 1
        chunk.aim = min(crew, key=lambda m: math.hypot(m.x - chunk.x, m.y - chunk.y) + CHUNK_CROWD * claims.get(id(m), 0))
        return chunk.aim

    def split_slime(self, slime):
        """A slime at half health bursts into smaller blobs. The Slime King bursts into his chunks, and stays
        on (unseen) until they're all beaten."""
        split = slime.spec["split"]
        share = CHUNK_SPLIT_HP / split["count"] if slime.boss else SLIME_SPLIT_HP
        count = split["count"]
        if not slime.boss and self.lv("salt") and random.random() < salt_single(self.lv("salt")):
            count = 1   # Rock Salt: it only manages one
        v = slime.victim
        if v is not None and v.attacker is slime:   # whoever it had hold of slips free
            v.state, v.attacker = "working", None
        slime.victim = None
        cell = self.cell_of(slime.x, slime.y)
        spread = 0.9 if slime.boss else 0.3
        landing = self.fling_spots(slime, count) if slime.boss else []   # (the King's chunks: flung all over)
        children = []
        for i in range(count):
            a = i / count * math.tau + random.uniform(-0.3, 0.3)
            child = Enemy(split["into"], self.depth, cell, self.column_height(*cell), elite=slime.elite)
            child.max_hp = child.hp = slime.max_hp * share
            child.state = "hunting"
            child.x = min(GRID - 0.05, max(0.05, slime.x + math.cos(a) * spread))
            child.y = min(GRID - 0.05, max(0.05, slime.y + math.sin(a) * spread))
            if landing:
                child.fling_to = landing[i]
            child.cooldown = random.uniform(1.5, 3.5)   # (chunks: not all slamming at once)
            child.flash = 0.2
            children.append(child)
        self.enemies += children
        px, py = enemy_anchor(slime, self.rise, time.time())
        gore = slime.spec["gore"]
        for _ in range(40 if slime.boss else 16):
            self.particles.append(Particle(px, py, random.choice([gore, tuple(c // 2 for c in gore)]), big=True))
        self.rings.append([px, py + 18, 0.0, 160 if slime.boss else 50, gore])
        if slime.boss:
            self.cues.append("-windup")
            slime.mode, slime.chunks = "split", children
            slime.windup, slime.slam_at = 0.0, None
            self.floaters.append(Floater("The Slime King bursts apart!", W / 2, 200, BAD, life=2.4, size=34))
            self.shake, self.shake_power = 0.4, 6
        else:
            self.enemies.remove(slime)
            self.floaters.append(Floater("Splat!", px, py - 30, (170, 240, 120), life=0.9, size=24))

    def update_split_boss(self, boss):
        """The Slime King in pieces: it sits among its chunks, its health their health; it falls with the last."""
        alive = [c for c in boss.chunks if c in self.enemies]
        if not alive:
            boss.hp = 0
            self.kill_enemy(boss)
            return
        boss.hp = sum(c.hp for c in alive)
        boss.x = sum(c.x for c in alive) / len(alive)
        boss.y = sum(c.y for c in alive) / len(alive)

    def boss_target(self):
        """What the crew should be pelting with rocks: the boss, or (Slime King in pieces) one of its chunks."""
        boss = self.boss()
        if boss and boss.mode == "split":
            return next((c for c in boss.chunks if c in self.enemies), None)
        return boss

    # ----- boss tricks ------------------------------------------------------
    def boss_auras(self):
        """Each frame: the Zombie King rallies the zombies around him; wisps shield the Archlich."""
        for e in self.enemies:
            e.dmg_taken = 1.0
            e.rallied = False
        boss = self.boss()
        if not boss or boss.state == "emerging":
            return
        if boss.kind == "voidmaw":
            boss.dmg_taken = VOID_GLANCE
        if boss.kind == "zombieking":
            for e in self.enemies:
                if e.kind == "zombie" and math.hypot(e.x - boss.x, e.y - boss.y) <= RALLY_RADIUS:
                    e.rallied = True
                    e.dmg_taken = RALLY_TOUGH
                    e.speed_mult = getattr(e, "speed_mult", 1.0) * RALLY_SPEED
        elif boss.kind == "lich":
            boss.dmg_taken = 1 - min(SHIELD_MAX, SHIELD_PER_WISP * len(self.shield_wisps()))

    def shield_wisps(self):
        """Wisps linked to the Archlich, shielding him."""
        return [e for e in self.enemies if e.kind == "wisp" and e.state != "emerging"]

    def boss_special(self, boss, dt):
        """Run the boss's own trick. Returns True while it's busy with it (no stalking or slamming)."""
        self.boss_second_trick(boss, dt)
        if boss.kind == "zombieking":
            if not boss.enraged and boss.hp < boss.max_hp * ENRAGE_AT:
                boss.enraged = True
                px, py = enemy_anchor(boss, self.rise, time.time())
                self.floaters.append(Floater("THE ZOMBIE KING IS ENRAGED!", W / 2, 200, BAD, life=2.4, size=36))
                self.rings.append([px, py, 0.0, 120, BAD])
                self.shake, self.shake_power = 0.4, 6
        elif boss.kind == "vampirelord":
            return self.update_vampire_lord(boss, dt)
        elif boss.kind == "lich":
            self.update_lich(boss, dt)
        elif boss.kind == "greatbat":
            self.update_great_bat(boss, dt)
        elif boss.kind == "bonetyrant":
            return self.update_bone_tyrant(boss, dt)
        elif boss.kind == "burrowbros":
            self.update_burrow_bros(boss, dt)
        elif boss.kind == "voidmaw":
            return self.update_void_maw(boss, dt)
        return False

    # ----- every boss's second trick ------------------------------------------------------------------------------
    def boss_second_trick(self, boss, dt):
        """Every SECOND_TRICK_EVERY seconds, the boss's second trick (only while it's itself and not mid-slam)."""
        if not boss.targetable or boss.mode in ("split", "bats", "bite", "pile") or boss.windup > 0 \
                or getattr(boss, "inhale", None) is not None or getattr(boss, "gaze", None):
            return
        boss.trick2 = getattr(boss, "trick2", SECOND_TRICK_FIRST) - dt
        if boss.trick2 > 0:
            return
        boss.trick2 = SECOND_TRICK_EVERY.get(boss.kind, 15.0)
        trick = {"zombieking": self.grasping_dead, "broodmother": self.silk_lash, "greatbat": self.wing_gust,
                 "bonetyrant": self.rib_cage, "slimeking": self.belly_flop, "vampirelord": self.mesmerise,
                 "lich": self.raise_the_fallen, "burrowbros": self.sinkholes, "mountain": self.rockslide,
                 "voidmaw": self.void_gaze}.get(boss.kind)
        if trick:
            trick(boss)

    def free_crew(self):
        """Crew a boss can single out: at work, not already held."""
        return [m for m in self.miners if m.state == "working" and not getattr(m, "held", None)
                and not getattr(m, "pulled", None)]

    def boss_says(self, boss, text):
        px, py = enemy_anchor(boss, self.rise, time.time())
        self.floaters.append(Floater(text, px, py - 70, (255, 200, 150), life=1.6, size=30))

    def mark(self, x, y, kind, boss):
        """A spot that glows for HAZARD_WARN seconds, then goes off (HAZARDS[kind])."""
        self.hazards.append([x, y, kind, HAZARD_WARN, boss])

    def grasping_dead(self, boss):
        """Zombie King: hands burst up out of the ground under a couple of the crew, holding whoever's still there."""
        for m in random.sample(self.free_crew(), min(2, len(self.free_crew()))):
            self.mark(m.x, m.y, "grasp", boss)
        self.boss_says(boss, "RISE, MY SUBJECTS!")

    def sinkholes(self, boss):
        """Burrow Brothers: their tunnels give way under the crew."""
        for m in random.sample(self.free_crew(), min(2, len(self.free_crew()))):
            self.mark(m.x, m.y, "sinkhole", boss)
        self.boss_says(boss, "The ground gives way!")

    def rockslide(self, boss):
        """The Mountain: boulders come down on the crew (and one somewhere else, for luck)."""
        for m in random.sample(self.free_crew(), min(2, len(self.free_crew()))):
            self.mark(m.x, m.y, "rock", boss)
        self.mark(random.uniform(0.5, GRID - 0.5), random.uniform(0.5, GRID - 0.5), "rock", boss)
        self.shake, self.shake_power = max(self.shake, 0.3), 4
        self.boss_says(boss, "ROCKSLIDE!")

    def silk_lash(self, boss):
        """Broodmother: a strand of silk at the crew member furthest off - and she reels them in to her."""
        crew = [m for m in self.free_crew() if math.hypot(m.x - boss.x, m.y - boss.y) > 2.0]
        if not crew:
            return
        m = max(crew, key=lambda c: math.hypot(c.x - boss.x, c.y - boss.y))
        m.pulled = [boss, SILK_SECS]
        self.cues.append(("hit", 0.5))
        self.boss_says(boss, "SILK LASH!")

    def wing_gust(self, boss):
        """Fanged Behemoth: one great wingbeat, and the crew near it are blown back, dazed."""
        if boss.slam_at:
            boss.trick2 = 2.0   # (mid-dive: in a moment)
            return
        hit = False
        for m in self.miners:
            dx, dy = m.x - boss.x, m.y - boss.y
            dist = math.hypot(dx, dy)
            if m.state == "down" or dist > GUST_RADIUS:
                continue
            ux, uy = (dx / dist, dy / dist) if dist > 0.05 else (1.0, 0.0)
            m.x = min(GRID - 0.3, max(0.3, m.x + ux * GUST_PUSH))
            m.y = min(GRID - 0.3, max(0.3, m.y + uy * GUST_PUSH))
            if m.state == "grabbed" and m.attacker:   # (blown clean out of a monster's grip)
                self.break_grip(m.attacker)
            m.stun = max(m.stun, GUST_STUN)
            hit = True
        px, py = enemy_anchor(boss, self.rise, time.time())
        for r in (90, 150, 210):
            self.rings.append([px, py + 30, 0.0, r, (230, 230, 245)])
        self.cues.append(("slam", 0.4))
        if hit:
            self.boss_says(boss, "WING GUST!")

    def rib_cage(self, boss):
        """Bone Tyrant: a cage of ribs bursts up round a crew member - click them free before it crushes them."""
        crew = self.free_crew()
        if crew:
            m = random.choice(crew)
            m.held = dict(kind="cage", left=CAGE_SECS, clicks=CAGE_CLICKS, boss=boss)
            self.cues.append(("smash", 0.4))
            self.boss_says(boss, f"{m.name} is caged!")

    def mesmerise(self, boss):
        """Vampire Lord: one of the crew falls under his gaze and drifts towards him - a click snaps them out of it."""
        crew = self.free_crew()
        if crew:
            m = random.choice(crew)
            m.held = dict(kind="trance", left=TRANCE_SECS, clicks=1, boss=boss)
            self.boss_says(boss, f"{m.name}, come to me...")

    def belly_flop(self, boss):
        """Slime King: he bounces high and comes down on a crew member's spot (the red marks where)."""
        crew = self.free_crew()
        if not crew:
            return
        m = max(crew, key=lambda c: math.hypot(c.x - boss.x, c.y - boss.y))
        boss.slam_at = (m.x, m.y)
        boss.windup = boss.windup_total = FLOP_WINDUP
        self.cues.append("windup")
        self.boss_says(boss, "BELLY FLOP!")

    def raise_the_fallen(self, boss):
        """Archlich: skeletons claw their way up out of the rock beside the crew."""
        if sum(1 for e in self.enemies if e.kind == "skeleton") >= RAISE_MAX or not self.current:
            return
        for _ in range(RAISE_COUNT):
            crew = self.free_crew()
            near = random.choice(crew) if crew else None
            cells = sorted(self.current, key=lambda c: math.hypot(c[0] + 0.5 - near.x, c[1] + 0.5 - near.y))[:6] \
                if near else list(self.current)
            cell = random.choice(cells)
            self.enemies.append(Enemy("skeleton", self.depth, cell, self.column_height(*cell), delay=0.4,
                                      hp_mult=self.art_mult("enemy_hp")))
        self.boss_says(boss, "RISE, AND SERVE!")

    def void_gaze(self, boss):
        """The Void Maw: its open eye fixes on a crew member - strike the eye before the gaze sears them."""
        crew = self.free_crew()
        if not crew or boss.eye is None:
            boss.trick2 = 2.0   # (its eye's shut: in a moment)
            return
        m = random.choice(crew)
        boss.gaze = [m, 0.0]
        self.boss_says(boss, f"Its eye fixes on {m.name}!")

    def update_boss_tricks(self, dt):
        """Marked spots going off, crew being reeled in, and The Void Maw's gaze."""
        for hz in self.hazards:
            hz[3] -= dt
            if hz[3] <= 0:
                self.hazard_lands(hz)
        self.hazards = [hz for hz in self.hazards if hz[3] > 0]
        for m in self.miners:
            pulled = getattr(m, "pulled", None)
            if not pulled:
                continue
            boss, left = pulled
            if boss not in self.enemies or m.state != "working" or left <= 0:
                m.pulled = None
                continue
            pulled[1] -= dt
            dx, dy = boss.x - m.x, boss.y - m.y
            dist = math.hypot(dx, dy)
            stop = boss.spec["reach"] * 1.1
            if dist > stop:
                step = min(dist - stop, 6.0 * dt)
                m.x += dx / dist * step
                m.y += dy / dist * step
            m.stun = max(m.stun, 0.15)   # (dragged along, not digging)
        for boss in [e for e in self.enemies if getattr(e, "gaze", None)]:
            m, age = boss.gaze
            if m.state == "down" or not boss.targetable:
                boss.gaze = None
                continue
            boss.gaze[1] += dt
            if boss.gaze[1] >= GAZE_SECS:
                boss.gaze = None
                self.hurt(m, GAZE_HURT * crew_hp_at(boss.depth))
                px, py = self.entity_screen(m, 40)
                self.floaters.append(Floater("SEARED!", px, py - 20, (200, 140, 255), life=1.2, size=28))
                for _ in range(14):
                    self.particles.append(Particle(px, py, random.choice([(170, 120, 255), (60, 40, 110)])))
                if m.hp <= 0:
                    if m.attacker:
                        m.attacker.release()
                    self.miner_down(m, killer=boss)

    def hazard_lands(self, hz):
        x, y, kind, _, boss = hz
        spec = HAZARDS[kind]
        cx, cy = iso(x, y, self.column_height(*self.cell_of(x, y)) + self.rise)
        colours = {"grasp": [(110, 160, 80), (70, 100, 50)], "sinkhole": [(110, 84, 60), (60, 44, 32)],
                   "rock": [(130, 128, 136), (90, 88, 96)]}[kind]
        for _ in range(16):
            self.particles.append(Particle(cx, cy, random.choice(colours), big=True))
        self.rings.append([cx, cy, 0.0, 60, colours[0]])
        self.cues.append(("smash" if kind != "grasp" else "hit", 0.35))
        for m in self.miners:
            if m.state == "down" or math.hypot(m.x - x, m.y - y) > spec["radius"]:
                continue
            self.hurt(m, spec["hurt"] * crew_hp_at(boss.depth))
            if spec["stun"]:
                m.stun = max(m.stun, spec["stun"])
            if m.hp <= 0:
                if m.attacker:
                    m.attacker.release()
                self.miner_down(m, killer=boss if boss in self.enemies else None)

    def update_held(self, m, dt, speed):
        """A crew member caged (Bone Tyrant) or entranced (Vampire Lord): no work till they're clicked free."""
        held = m.held
        held["left"] -= dt
        m.anim = 0.0
        boss = held["boss"]
        if held["kind"] == "trance" and boss in self.enemies:   # drifting towards him, a step at a time
            if math.hypot(boss.x - m.x, boss.y - m.y) > boss.spec["reach"]:
                self.walk_to(m, boss.x, boss.y, speed * 0.4, dt)
        if held["left"] > 0 and boss in self.enemies:
            return
        m.held = None
        px, py = self.entity_screen(m, 40)
        if held["kind"] == "cage" and boss in self.enemies:   # (too slow: the ribs close)
            self.hurt(m, CAGE_CRUSH * crew_hp_at(boss.depth))
            self.floaters.append(Floater("CRUSHED!", px, py - 20, BAD, life=1.2, size=28))
            if m.hp <= 0:
                self.miner_down(m, killer=boss)
        else:
            self.floaters.append(Floater("...where am I?", px, py - 20, MUTED, life=1.2, size=20))

    def free_held(self, m):
        """You click a caged or entranced crew member: a blow at the cage, or a snap of the fingers."""
        held = m.held
        held["clicks"] -= 1
        px, py = self.entity_screen(m, 40)
        for _ in range(8):
            self.particles.append(Particle(px, py, (235, 228, 205) if held["kind"] == "cage" else (255, 160, 220)))
        if held["clicks"] > 0:
            self.floaters.append(Floater("CRACK!", px, py - 20, (235, 228, 205), life=0.6, size=22))
            return
        m.held = None
        self.floaters.append(Floater("Free!" if held["kind"] == "cage" else "Snapped out of it!", px, py - 30, GOOD,
                                     life=1.3, size=26))
        self.rings.append([px, py, 0.0, 60, GOOD])

    def break_gaze(self, boss, eye):
        if getattr(boss, "gaze", None):
            boss.gaze = None
            self.floaters.append(Floater("GAZE BROKEN!", eye[0], eye[1] - 60, (230, 220, 255), life=1.2, size=28))

    # ----- the deep's bosses --------------------------------------------------------------------------------------
    def update_burrow_bros(self, boss, dt):
        """The Burrow Brothers: one fights above while the other's mound tunnels towards the crew; every BRO_SWAP
        seconds they swap, the tunneller bursting up in a slam. Once one has fallen, the other fights on above."""
        if boss.bro_hp is None:   # (each brother has half the health)
            boss.bro_hp = [boss.max_hp / 2, boss.max_hp / 2]
            boss.mound = [min(GRID - 0.5, boss.x + 2.5), boss.y]
        boss.surface_t += dt
        if boss.bro_hp[1 - boss.up] <= 0:   # the other's fallen: no more tunnelling
            boss.mound, boss.peek = None, None
            return
        if boss.peek is not None:   # the tunneller has popped his head up for a look (and stays put meanwhile)
            boss.peek += dt
            if boss.peek >= BRO_PEEK_SECS:
                boss.peek = None
        elif boss.peek_at is not None and boss.swap_timer <= boss.peek_at:
            self.bro_peek(boss)
        crew = [m for m in self.miners if m.state == "working"]
        if crew and boss.peek is None:   # the mound creeps towards whoever is nearest
            target = min(crew, key=lambda m: math.hypot(m.x - boss.mound[0], m.y - boss.mound[1]))
            dx, dy = target.x - boss.mound[0], target.y - boss.mound[1]
            dist = math.hypot(dx, dy)
            if dist > 0.3:
                step = min(dist - 0.3, BRO_MOUND_SPEED * dt)
                boss.mound[0] += dx / dist * step
                boss.mound[1] += dy / dist * step
        boss.swap_timer -= dt
        if boss.swap_timer <= 0 and boss.windup <= 0:
            self.bro_swap(boss)

    def bro_swap(self, boss, text=None):
        """The brother above dives; the other bursts up out of his mound, slamming the crew around him."""
        (boss.x, boss.y), boss.mound = boss.mound, [boss.x, boss.y]
        boss.up = 1 - boss.up
        boss.swap_timer, boss.surface_t, boss.windup = BRO_SWAP, 0.0, 0.0
        boss.peek = None
        boss.peek_at = random.uniform(BRO_SWAP * 0.45, BRO_SWAP * 0.7) if random.random() < BRO_PEEK_CHANCE else None
        boss.cooldown = max(boss.cooldown, 1.5)
        px, py = self.entity_screen(boss)
        for _ in range(30):
            self.particles.append(Particle(px, py, random.choice([(110, 84, 60), (80, 60, 44), (140, 110, 80)]),
                                           big=True))
        self.rings.append([px, py, 0.0, 110, (150, 110, 70)])
        self.shake, self.shake_power = 0.3, 5
        self.cues.append(("slam", 0.7))
        self.floaters.append(Floater(text or f"{BRO_NAMES[boss.up]} bursts up!", px, py - 110, (230, 190, 140),
                                     life=1.4, size=28))
        self.slam_crew(boss, BRO_SURFACE_RADIUS)

    def bro_peek(self, boss):
        """The brother below pops his head up out of his mound to see how the fight's going, then ducks back."""
        boss.peek, boss.peek_at = 0.0, None
        px, py = iso(boss.mound[0], boss.mound[1], self.column_height(*self.cell_of(*boss.mound)) + self.rise)
        for _ in range(12):
            self.particles.append(Particle(px, py, random.choice([(110, 84, 60), (80, 60, 44), (140, 110, 80)])))
        self.floaters.append(Floater(f"{BRO_NAMES[1 - boss.up]} pops up for a look!", px, py - 120,
                                     (230, 190, 140), life=1.4, size=24))

    def bro_hit(self, boss, dealt):
        """A blow on the brother above. If he falls with the other still going, the other comes up to fight alone."""
        up, other = boss.up, 1 - boss.up
        boss.bro_hp[up] -= dealt
        if boss.bro_hp[up] > 0:
            return
        boss.bro_hp[up] = 0.0
        if boss.bro_hp[other] > 0:
            boss.hp = boss.bro_hp[other]   # (no spill-over: the other brother is untouched)
            if boss.mound is None:
                boss.mound = [boss.x, boss.y]
            self.bro_swap(boss, f"{BRO_NAMES[up]} is down! {BRO_NAMES[other]} fights on alone!")
            boss.mound = None

    def mountain_heave(self, boss):
        """The Mountain's stomp heaves new stone blocks up out of the ground around it."""
        cx, cy = self.cell_of(boss.x, boss.y)
        empty = [(x, y) for x in range(cx - 2, cx + 3) for y in range(cy - 2, cy + 3)
                 if 0 <= x < GRID and 0 <= y < GRID and (x, y) != (cx, cy) and (x, y) not in self.current]
        for cell in random.sample(empty, min(MOUNTAIN_HEAVE, len(empty))):
            self.current[cell] = Block("stone", self.depth)
            px, py = self.cell_screen(cell)
            for _ in range(6):
                self.particles.append(Particle(px, py, random.choice([(120, 118, 132), (80, 78, 92)])))
        if empty:
            px, py = enemy_anchor(boss, self.rise, time.time())
            self.floaters.append(Floater("The ground heaves up!", px, py - 120, (190, 180, 160), life=1.4, size=24))

    def update_void_maw(self, boss, dt):
        """The Void Maw: its eyes open one at a time, blinking shut between; pools of darkness spread under the crew
        and eat at them; and every so often it inhales, dragging the crew in to bite. True while it's inhaling."""
        self.void_pool_drain(boss, dt)
        if boss.inhale is not None:
            return self.void_inhale(boss, dt)
        boss.inhale_timer -= dt
        if boss.inhale_timer <= 0 and boss.windup <= 0:
            from .boss_sprites import VOID_EYES
            boss.inhale, boss.inhale_timer = 0.0, VOID_INHALE_EVERY
            boss.eye = random.choice([i for i in range(len(VOID_EYES)) if i != getattr(boss, "last_eye", -1)])
            boss.last_eye, boss.eye_timer = boss.eye, VOID_INHALE_SECS + 0.6   # (wide open the whole time)
            self.cues.append("windup")
            self.floaters.append(Floater("IT INHALES - STRIKE THE EYE!", W / 2, 230, (200, 170, 255), life=2.2,
                                         size=32))
            return True
        boss.eye_timer -= dt
        if boss.eye_timer <= 0:
            if boss.eye is None:   # a new eye opens somewhere else
                from .boss_sprites import VOID_EYES
                boss.eye = random.choice([i for i in range(len(VOID_EYES)) if i != getattr(boss, "last_eye", -1)])
                boss.last_eye, boss.eye_timer = boss.eye, VOID_EYE_OPEN
            else:                  # ...and blinks shut
                boss.eye, boss.eye_timer = None, VOID_EYE_SHUT
        boss.trick_timer -= dt
        if boss.trick_timer <= 0:
            boss.trick_timer = VOID_POOL_EVERY
            crew = [m for m in self.miners if m.state == "working"]
            if crew and len(self.void_pools) < VOID_POOLS:
                m = random.choice(crew)
                self.void_pools.append([m.x, m.y, 0.0])
                px, py = self.entity_screen(m)
                self.floaters.append(Floater("Darkness spreads...", px, py - 60, (170, 140, 230), life=1.4, size=22))
        for p in self.void_pools:
            p[2] += dt
        self.void_pools = [p for p in self.void_pools if p[2] < VOID_POOL_SECS]
        return False

    def void_pool_drain(self, boss, dt):
        """The Void Maw's pools of darkness eat at whoever's standing in them (a share of their own health, so even
        a tough late crew feels it)."""
        if not self.void_pools:
            return
        for m in self.miners:
            if m.state == "down" or not any(math.hypot(m.x - p[0], m.y - p[1]) <= SHADE_RADIUS
                                             for p in self.void_pools):
                continue
            self.hurt(m, m.max_hp * VOID_POOL_DRAIN * dt)
            if random.random() < dt * 6:   # wisps of them drifting down into the dark
                px, py = self.entity_screen(m, 30)
                self.particles.append(Particle(px, py, random.choice([(120, 80, 200), (60, 40, 110)])))
            if m.hp <= 0:
                if m.attacker:
                    m.attacker.release()
                self.miner_down(m, killer=boss)

    def void_inhale(self, boss, dt):
        """The Void Maw inhales: crew close by are dragged in, reeling; when it's done, it bites. True (busy)."""
        boss.inhale += dt
        for m in self.void_pulled(boss):
            dx, dy = boss.x - m.x, boss.y - m.y
            dist = math.hypot(dx, dy)
            if dist > VOID_BITE_RADIUS * 0.6:
                step = min(dist - VOID_BITE_RADIUS * 0.6, VOID_INHALE_PULL * dt)
                m.x = min(GRID - 0.05, max(0.05, m.x + dx / dist * step))
                m.y = min(GRID - 0.05, max(0.05, m.y + dy / dist * step))
            m.stun = max(m.stun, 0.2)   # (no digging while you're being sucked in)
        if boss.inhale < VOID_INHALE_SECS:
            return True
        boss.inhale = None
        boss.eye, boss.eye_timer = None, VOID_EYE_SHUT
        self.cues += ["-windup", "slam"]
        fx, fy = self.entity_screen(boss)
        self.shake, self.shake_power = 0.4, 8
        self.rings.append([fx, fy, 0.0, 170, (150, 100, 230)])
        self.rings.append([fx, fy, 0.0, 100, (230, 210, 255)])
        self.floaters.append(Floater("GULP!", fx, fy - 120, (200, 160, 255), life=1.2, size=40))
        for m in self.miners:
            if m.state == "down" or math.hypot(m.x - boss.x, m.y - boss.y) > VOID_BITE_RADIUS:
                continue
            dmg = m.max_hp * VOID_BITE
            self.hurt(m, dmg)
            px, py = self.entity_screen(m, 50)
            self.floaters.append(Floater(f"-{dmg:.0f}", px, py, BAD, life=1.0, size=24))
            if m.hp <= 0:
                if m.attacker:
                    m.attacker.release()
                self.miner_down(m, killer=boss)
        return True

    def void_pulled(self, boss):
        """Crew the inhaling Void Maw is dragging in."""
        return [m for m in self.miners if m.state != "down" and m.state != "grabbed"
                and math.hypot(m.x - boss.x, m.y - boss.y) <= VOID_INHALE_RADIUS]

    def pick_void_pool(self, pos):
        """One of The Void Maw's pools of darkness under the mouse, or None."""
        for p in self.void_pools:
            cx, cy = iso(p[0], p[1], self.column_height(*self.cell_of(p[0], p[1])) + self.rise)
            rx, ry = SHADE_RADIUS * TILE_W * 0.71, SHADE_RADIUS * TILE_H * 0.71
            if ((pos[0] - cx) / rx) ** 2 + ((pos[1] - cy) / ry) ** 2 <= 1:
                return p
        return None

    def dispel_void_pool(self, pool):
        """You drive a pool of darkness back."""
        self.void_pools.remove(pool)
        cx, cy = iso(pool[0], pool[1], self.column_height(*self.cell_of(pool[0], pool[1])) + self.rise)
        self.rings.append([cx, cy, 0.0, 90, (200, 170, 255)])
        for _ in range(16):
            self.particles.append(Particle(cx, cy, random.choice([(200, 170, 255), (255, 255, 255), (120, 80, 200)])))
        self.floaters.append(Floater("The dark recoils!", cx, cy - 40, (200, 170, 255), life=1.1, size=24))

    def void_eye_hit(self, boss, pos):
        """How hard a click on The Void Maw lands: full (and then some) on its open eye, a glance anywhere else."""
        from .boss_sprites import void_eye_screen
        eye = void_eye_screen(boss, self.rise)
        if eye and pos and math.hypot(pos[0] - eye[0], pos[1] - eye[1]) <= eye[2] + 10:
            self.break_gaze(boss, eye)
            if boss.inhale is not None:   # struck mid-breath: it chokes, and nobody gets bitten
                boss.inhale = None
                boss.eye, boss.eye_timer = None, VOID_EYE_SHUT
                self.cues.append("-windup")
                self.floaters.append(Floater("IT CHOKES!", eye[0], eye[1] - 40, (230, 220, 255), life=1.4, size=36))
                self.rings.append([eye[0], eye[1], 0.0, 120, (230, 220, 255)])
                return VOID_EYE / VOID_GLANCE
            self.floaters.append(Floater("EYE!", eye[0], eye[1] - 20, (230, 220, 255), life=0.7, size=26))
            return VOID_EYE / VOID_GLANCE
        if self.clock - self.void_tip_at > 6:   # every so often, a reminder where to aim
            self.void_tip_at = self.clock
            self.floaters.append(Floater("It barely feels that - strike the open eye!", W / 2, 230, (200, 170, 255),
                                         life=2.2, size=26))
        return 1.0

    def update_vampire_lord(self, boss, dt):
        """Every so often: scatter into bats, fly to a crew member, land and feed on them to heal."""
        if boss.mode == "stalk":
            boss.trick_timer -= dt
            prey = [m for m in self.miners if m.state == "working"]
            if boss.trick_timer > 0 or boss.windup > 0 or not prey:
                return False
            far = sorted(prey, key=lambda m: -math.hypot(m.x - boss.x, m.y - boss.y))
            boss.goal = random.choice(far[:3])   # one of the crew furthest from him
            boss.mode = "bats"
            self.bat_puff(boss)
            px, py = enemy_anchor(boss, self.rise, time.time())
            self.floaters.append(Floater("He scatters into bats!", px, py - 80, (190, 120, 230), life=1.6, size=26))
            return True
        if boss.mode == "bats":
            if boss.goal is None or boss.goal.state != "working":   # the target was grabbed or died: pick another
                prey = [m for m in self.miners if m.state == "working"]
                if not prey:
                    boss.mode, boss.trick_timer = "stalk", BAT_FORM_EVERY
                    self.bat_puff(boss)
                    return False
                boss.goal = min(prey, key=lambda m: math.hypot(m.x - boss.x, m.y - boss.y))
            v = boss.goal
            if self.walk_to(boss, v.x + 0.45, v.y - 0.45, BAT_FORM_SPEED, dt, stop=0.1):
                boss.mode, boss.victim, boss.goal = "bite", v, None
                boss.timer, boss.bite_hp = BITE_SECS, boss.hp
                boss.facing = -1
                v.state, v.attacker, v.target = "grabbed", boss, None
                self.bat_puff(boss)
                px, py = self.entity_screen(v, 60)
                self.floaters.append(Floater(f"{v.name}: HELP!", px, py, BAD, life=1.2, size=26))
            return True
        # biting: drain the victim, heal, until time runs out or he's hit hard enough to let go
        v = boss.victim
        if v is None or v.state != "grabbed" or v.attacker is not boss:
            self.end_bite(boss)
            return False
        boss.x, boss.y = min(GRID - 0.05, v.x + 0.45), max(0.05, v.y - 0.45)
        self.hurt(v, BITE_SHARE * crew_hp_at(boss.depth) * dt * self.art_mult("grab_dmg"))
        boss.hp = min(boss.max_hp, boss.hp + boss.max_hp * BITE_HEAL * dt)
        self.blood_drip(v, boss)
        boss.timer -= dt
        if v.hp <= 0:
            self.end_bite(boss)
            self.miner_down(v, killer=boss)
        elif boss.timer <= 0 or boss.hp <= boss.bite_hp - boss.max_hp * BITE_BREAK:
            if boss.timer > 0:
                px, py = enemy_anchor(boss, self.rise, time.time())
                self.floaters.append(Floater("He lets go!", px, py - 70, GOOD, life=1.3, size=26))
            self.end_bite(boss)
        return True

    def end_bite(self, boss):
        """The Vampire Lord stops feeding (or never was): free his victim, back to stalking."""
        v = boss.victim
        if v is not None and v.attacker is boss:
            v.attacker = None
            if v.state == "grabbed":
                v.state = "working"
        boss.victim = None
        if boss.mode != "stalk":
            boss.mode, boss.trick_timer, boss.cooldown = "stalk", BAT_FORM_EVERY, 1.0

    def bat_puff(self, boss):
        px, py = enemy_anchor(boss, self.rise, time.time())
        for _ in range(26):
            self.particles.append(Particle(px, py, random.choice([(120, 60, 160), (80, 40, 110), (40, 30, 50)]),
                                           big=True))

    def update_great_bat(self, boss, dt):
        """Every so often it screeches: crew close by are stunned and stand reeling for a moment."""
        boss.trick_timer -= dt
        if boss.trick_timer > 0 or boss.windup > 0:
            return
        boss.trick_timer = SCREECH_EVERY
        px, py = enemy_anchor(boss, self.rise, time.time())
        for r in (80, 150, 220):
            self.rings.append([px, py, 0.0, r, (190, 150, 230)])
        self.floaters.append(Floater("SCREEEECH!", px, py - 70, (200, 160, 240), life=1.4, size=34))
        self.shake, self.shake_power = 0.3, 4
        for m in self.miners:
            if m.state == "working" and math.hypot(m.x - boss.x, m.y - boss.y) <= SCREECH_RADIUS:
                m.stun = SCREECH_STUN

    def update_bone_tyrant(self, boss, dt):
        """After each slam it strides off and hurls a volley of bones at the crew, then marches back in (and if
        the crew keep away from its slams, it throws a volley from where it stands). As a bone pile it just lies
        there until it pulls itself together - or is smashed first. Returns True while busy with any of that."""
        if boss.mode == "pile":
            boss.pile_timer -= dt
            if boss.pile_timer <= 0:
                boss.mode, boss.trick_timer = "stalk", STALK_PATIENCE
                boss.hp = boss.max_hp * REFORM_HP
                px, py = enemy_anchor(boss, self.rise, time.time())
                self.floaters.append(Floater("The Bone Tyrant pulls itself back together!", W / 2, 200, BAD,
                                             life=2.4, size=30))
                self.rings.append([px, py, 0.0, 110, (235, 228, 205)])
            return True
        if boss.mode == "stride":
            if self.walk_to(boss, *boss.goal, STRIDE_SPEED, dt, stop=0.1):
                self.start_volley(boss)
            return True
        if boss.mode == "volley":
            self.update_volley(boss, dt)
            return True
        boss.trick_timer -= dt
        if boss.trick_timer <= 0 and boss.windup <= 0:
            self.start_volley(boss)
            return True
        return False

    def start_stride(self, boss):
        """The Bone Tyrant backs off: somewhere about STRIDE_RANGE from the nearest crew member, to throw from."""
        crew = [m for m in self.miners if m.state != "down"]
        if not crew:
            return
        def score(spot):
            near = min(math.hypot(m.x - spot[0], m.y - spot[1]) for m in crew)
            return abs(near - STRIDE_RANGE)
        spots = [(random.uniform(1.0, GRID - 1.0), random.uniform(1.0, GRID - 1.0)) for _ in range(16)]
        boss.mode, boss.goal = "stride", min(spots, key=score)

    def start_volley(self, boss):
        boss.mode = "volley"
        boss.volley = BONE_VOLLEY_HURT if boss.hp < boss.max_hp * 0.5 else BONE_VOLLEY
        boss.throw_anim, boss.trick_timer, boss.goal = 0.0, 0.3, None
        px, py = enemy_anchor(boss, self.rise, time.time())
        self.floaters.append(Floater("Incoming bones!", px, py - 90, (235, 228, 205), life=1.4, size=26))

    def update_volley(self, boss, dt):
        """Throw the volley's bones one after another, each with a wind-up and a whip of the arm."""
        if boss.throw_anim > 0:
            before = boss.throw_anim
            boss.throw_anim = max(0.0, boss.throw_anim - dt)
            release = THROW_ANIM_SECS * (1 - THROW_RELEASE)   # (the animation counts down)
            if before > release >= boss.throw_anim:
                self.throw_bone(boss)
            return
        if boss.volley <= 0:   # done: march back in
            boss.mode, boss.trick_timer, boss.cooldown = "stalk", STALK_PATIENCE, 0.0
            return
        boss.trick_timer -= dt
        if boss.trick_timer > 0:
            return
        crew = [m for m in self.miners if m.state != "down"]
        if not crew:
            return
        boss.volley -= 1
        boss.throw_anim, boss.trick_timer = THROW_ANIM_SECS, VOLLEY_GAP
        targeted = {id(b[1]) for b in self.bone_throws}   # spread the volley around the crew, furthest first
        far = sorted(crew, key=lambda m: (id(m) in targeted, -math.hypot(m.x - boss.x, m.y - boss.y)))
        boss.throw_at = random.choice(far[:3])
        dx, dy = boss.throw_at.x - boss.x, boss.throw_at.y - boss.y
        boss.facing = 1 if (dx - dy) >= 0 else -1

    def throw_bone(self, boss):
        target = boss.throw_at
        if target is None or target.state == "down":
            target = self.nearest_crew(boss.x, boss.y)
        if target is None:
            return
        ax, ay = enemy_anchor(boss, self.rise, time.time())
        hand = (ax + boss.facing * 22, ay - 46)   # (where the throwing hand is when it lets go)
        self.bone_throws.append([hand, target, 0.0, self.entity_screen(boss)])
        self.cues.append(("hit", 0.4))

    def bone_collapse(self, boss):
        """The Bone Tyrant falls apart - for now: a heap of bones you have a few seconds to smash."""
        self.cues.append("-windup")   # (a growl mid-wind-up stops with it)
        boss.reformed = True
        boss.mode, boss.pile_timer = "pile", PILE_SECS
        boss.hp = boss.max_hp * PILE_HP
        boss.windup, boss.slam_at = 0.0, None
        boss.volley, boss.throw_anim, boss.goal = 0, 0.0, None
        fx, fy = self.entity_screen(boss)
        for _ in range(30):
            self.particles.append(Particle(fx, fy - 30, random.choice([(235, 228, 205), (200, 190, 165)]), big=True))
        self.floaters.append(Floater("It collapses... smash the bones before they rise!", W / 2, 200, GOLD,
                                     life=2.6, size=30))
        self.shake, self.shake_power = 0.3, 5

    def update_lich(self, boss, dt):
        """Curse a crew member every so often; a curse not lifted in time bursts, hurting everyone near."""
        boss.trick_timer -= dt
        if boss.trick_timer <= 0:
            boss.trick_timer = CURSE_EVERY
            free = [m for m in self.miners if m.state != "down" and m.curse <= 0]
            if free:
                m = random.choice(free)
                m.curse = CURSE_SECS
                px, py = self.entity_screen(m, 70)
                self.floaters.append(Floater(f"{m.name} is CURSED! Click them!", px, py - 10, (190, 120, 255),
                                             life=1.8, size=24))
        for m in self.miners:
            if m.curse > 0 and m.state != "down":
                m.curse -= dt
                if m.curse <= 0:
                    self.curse_burst(m, boss)

    def curse_burst(self, cursed, boss):
        dmg = CURSE_SHARE * crew_hp_at(boss.depth)
        cursed.curse = 0.0
        px, py = self.entity_screen(cursed, 30)
        self.rings.append([px, py, 0.0, 120, (190, 120, 255)])
        self.rings.append([px, py, 0.0, 70, (240, 220, 255)])
        for _ in range(28):
            self.particles.append(Particle(px, py, random.choice([(190, 120, 255), (120, 60, 200), (240, 220, 255)]),
                                           big=True))
        self.floaters.append(Floater("The curse bursts!", px, py - 50, (190, 120, 255), life=1.4, size=26))
        if dmg <= 0:
            return
        for m in self.miners:
            if m.state == "down" or math.hypot(m.x - cursed.x, m.y - cursed.y) > CURSE_RADIUS:
                continue
            self.hurt(m, dmg)
            if m.hp <= 0:
                if m.attacker:
                    m.attacker.release()
                    if m.attacker and m.attacker.boss:
                        self.end_bite(m.attacker)
                self.miner_down(m, killer=boss)

    def pick_cursed(self, pos):
        """A crew member under the mouse who needs a click (cursed, caged or entranced), or None."""
        for m in self.miners:
            if (m.curse > 0 or getattr(m, "held", None)) and m.state != "down":
                x, y = self.entity_screen(m, 30)
                if math.hypot(pos[0] - x, pos[1] - y) <= 26:
                    return m
        return None

    def lift_curse(self, m):
        m.curse = 0.0
        px, py = self.entity_screen(m, 40)
        self.floaters.append(Floater("Curse lifted!", px, py - 30, GOOD, life=1.3, size=26))
        self.rings.append([px, py, 0.0, 60, (240, 220, 255)])
        for _ in range(14):
            self.particles.append(Particle(px, py, random.choice([(240, 220, 255), (255, 255, 255)])))

    def web_slow(self, m):
        return WEB_SLOW if self.cell_of(m.x, m.y) in self.webs else 1.0

    def hatch(self, egg):
        """An egg sac nobody broke in time bursts open into spiders."""
        self.enemies.remove(egg)
        cell = self.cell_of(egg.x, egg.y)
        kind = egg.spec["hatch"]["kind"]
        for _ in range(egg.spec["hatch"]["count"]):
            spider = Enemy(kind, self.depth, cell, self.column_height(*cell), hp_mult=self.art_mult("enemy_hp"))
            spider.state = "hunting"
            spider.x += random.uniform(-0.3, 0.3)
            spider.y += random.uniform(-0.3, 0.3)
            self.enemies.append(spider)
        px, py = self.entity_screen(egg, 8)
        for _ in range(18):
            self.particles.append(Particle(px, py, random.choice([(230, 230, 210), (190, 220, 150)]), big=True))
        self.floaters.append(Floater("It hatched!", px, py - 30, BAD, life=1.2, size=24))

    def boss_retreat(self, boss):
        """Time's up: the boss withdraws into the dark. No trophy, but the dig can go on."""
        self.cues.append("-windup")   # (a growl mid-wind-up stops with it)
        self.achieve("boss_fled")
        self.enemies.remove(boss)
        for chunk in boss.chunks:   # (the Slime King's chunks ooze away with him)
            if chunk in self.enemies:
                self.enemies.remove(chunk)
        self.end_bite(boss)
        px, py = enemy_anchor(boss, self.rise, time.time())
        for _ in range(8):
            self.smoke.append(Smoke(px, py, size=16))
        self.floaters.append(Floater(f"{the(boss.spec['name'], True)} retreats into the dark...", W / 2, 168, BAD,
                                     life=3.0, size=32))
        self.finish_boss_fight()
        if self.depth >= EXPEDITION_DEPTH:   # the bottom: there's no way on but through it - it will be back
            self.boss_done = self.depth - 1
            self.boss_return = 30.0
            self.notice = [f"{the(boss.spec['name'], True)} will rise again in 30s - be ready", 6.0, ""]

    def boss_defeated(self, boss):
        """A boss falls: its trophy the first time, otherwise an artifact still out there, or more gold."""
        self.cues.append("-windup")   # (a growl mid-wind-up stops with it)
        self.floaters.append(Floater(f"{boss.spec['name'].upper()} DEFEATED!", W / 2, 210, GOLD, life=3.0, size=44))
        self.cues.append("victory")
        self.shake, self.shake_power = 0.5, 6
        self.flash = 0.12
        px, py = enemy_anchor(boss, self.rise, time.time())
        trophy = TROPHY_OF.get(boss.kind)
        if trophy and trophy not in self.artifacts:
            self.award_artifact(trophy, px, py)
        else:
            self.find_artifact(px, py)
        self.lifetime["bosses"] += 1
        if boss.kind not in self.feats["bosses"]:
            self.feats["bosses"].append(boss.kind)
        if boss.fight_time <= QUICK_KILL_SECS:
            self.achieve("quick_kill")
        start = self.boss_fight_start
        if all(m.last_hurt < start for m in self.miners) and not any(g.get("died_clock", 0) >= start
                                                                     for g in self.graveyard):
            self.achieve("untouchable")
        if not any(self.levels[u["key"]] for u in UPGRADES if u["branch"] == "combat"):
            self.achieve("hold_beer")   # (not one Combat upgrade to your name)
        self.finish_boss_fight()
        if self.depth >= EXPEDITION_DEPTH:   # the bottom of the expedition: the shaft comes down, there and then
            self.start_collapse()

    def finish_boss_fight(self):
        """The boss is gone (beaten or fled): waves resume, and an already-cleared layer gives way."""
        self.boss_done = self.depth
        self.hazards = []
        for m in self.miners:   # (cages crumble, trances lift, the silk goes slack)
            m.held, m.pulled = None, None
        self.enemy_timer = self.wave_interval()
        self.void_pools = []
        for m in self.miners:   # the Archlich's curses die with him
            m.curse = 0.0
        if not self.current:
            self.descend()

    def tell_boss_gate(self):
        if not self.boss_gate_told:
            self.boss_gate_told = True
            boss = self.boss()
            self.notice = [f"{the(boss.spec['name'], True)} bars the way down - defeat it to dig deeper!", 5.0, ""]

    # ----- artifacts ------------------------------------------------------
    def undiscovered(self):
        """Artifacts still buried somewhere below: the common ones, and those of the camp's hires you have."""
        return [k for k in COMMON if k not in self.artifacts] + \
            [k for k, a in ARTIFACTS.items() if a.get("crew") in self.camp and k not in self.artifacts]

    def bury_artifact(self, layer, depth):
        """Now and then a new layer hides an artifact in one of its blocks (a glint gives it away). The layer at
        FIRST_ARTIFACT_BY always does if none has turned up yet, so every player finds one early on."""
        if depth < ARTIFACT_MIN_DEPTH or not layer or not self.undiscovered():
            return
        first = depth == FIRST_ARTIFACT_BY and not self.artifacts
        chance = DIVINING_CHANCE if "divining" in self.camp_items else ARTIFACT_CHANCE   # (Rocco's Divining Rod)
        if not first and random.random() >= chance:
            return
        layer[random.choice(list(layer))].artifact = True

    def find_artifact(self, px, py):
        """An artifact turns up at (px, py): one not yet found, or - with every one found - a hoard of gold."""
        left = self.undiscovered()
        if left:
            self.award_artifact(random.choice(left), px, py)
            return
        hoard = self.earn(max(self.gold_per_sec(), 10) * 60)
        self.floaters.append(Floater(f"ANCIENT HOARD! +{fmt(hoard)}", px, py - 60, GOLD, life=2.4, size=32, coin=True))
        self.fly_coins(px, py, 16)

    def award_artifact(self, key, px, py):
        self.artifacts.append(key)
        self.new_artifacts.add(key)
        self.refresh_artifacts()
        self.reveals.append([key, 0.0])
        color = ARTIFACTS[key]["color"]
        self.rings.append([px, py, 0.0, 140, color])
        self.rings.append([px, py, 0.0, 80, (255, 255, 255)])
        for _ in range(30):
            self.particles.append(Particle(px, py, random.choice([color, (255, 255, 255), GOLD]), big=True))
        self.sync_miners(announce=True)   # the Lantern's extra miner turns up straight away

    def spring_trap(self, enemy):
        """Booby Traps: spikes punch up into a monster arriving on the ground."""
        if not self.lv("traps") or enemy not in self.enemies:
            return
        self.spike_fx.append([self.cell_of(enemy.x, enemy.y), 0.0])
        self.hit_enemy(enemy, enemy.max_hp * trap_share(self.lv("traps")) * enemy.pct_scale, floor=False,
                       ring=(200, 200, 210))

    def enemy_burst(self, enemy):
        """A zombie breaks through the ground."""
        px, py = self.entity_screen(enemy)
        for _ in range(22):
            self.particles.append(Particle(px, py, random.choice([(110, 84, 60), (80, 60, 44), (140, 110, 80)]),
                                           big=True))
        self.rings.append([px, py, 0.0, 60, (150, 110, 70)])
        self.spring_trap(enemy)

    def enemy_materialise(self, enemy):
        """A ghost or wisp forms out of cold mist."""
        px, py = self.entity_screen(enemy, 14)
        for _ in range(16):
            self.particles.append(Particle(px, py, random.choice([(200, 225, 255), (150, 190, 240), (255, 255, 255)])))
        self.rings.append([px, py + 12, 0.0, 50, (170, 210, 255)])

    def enemy_landed(self, enemy):
        """A spider drops onto the board."""
        px, py = self.entity_screen(enemy)
        for _ in range(10):
            self.particles.append(Particle(px, py, (150, 145, 160)))
        self.rings.append([px, py, 0.0, 40, (200, 195, 210)])
        self.spring_trap(enemy)
        if self.lv("torches") and enemy.kind == "spider" and enemy in self.enemies:   # Torches: singed on landing
            for _ in range(14):
                self.particles.append(Particle(px, py - 8, random.choice([(255, 170, 60), (255, 230, 120), (220, 80, 40)])))
            self.floaters.append(Floater("Singed!", px, py - 30, (255, 170, 60), life=0.9, size=22))
            self.hit_enemy(enemy, enemy.max_hp * torch_singe(self.lv("torches")) * enemy.pct_scale, floor=False,
                           ring=(255, 150, 60))

    # ----- specialist counters (regular monsters only: bosses shrug them off) ---------------------------------
    def grip_ward(self, enemy):
        """How hard a grabbing monster still drains (and a vampire heals): Garlic Garlands, Torches."""
        if enemy.kind == "vampire" and self.lv("garlic"):
            return 1 - garlic_ward(self.lv("garlic"))
        if enemy.kind == "spider" and self.lv("torches"):
            return torch_grip(self.lv("torches"))
        return 1.0

    def turn_delay(self):
        """Garlic Garlands: bats take this many times longer to turn into vampires."""
        return garlic_delay(self.lv("garlic")) if self.lv("garlic") else 1.0

    def tremor_bells(self, burrower, dt):
        """Tremor Bells: a Burrower closing in on the crew (or tunnelling a while) is heard, and stamped out of the
        ground before it can burst up under anyone. True if it was."""
        if not self.lv("bells") or burrower.boss:
            return False
        burrower.tunnel_t += dt
        target = self.nearest_free_miner(burrower.x, burrower.y)
        near = target is not None and math.hypot(target.x - burrower.x, target.y - burrower.y) <= BELL_RANGE
        if not near and burrower.tunnel_t < BELL_HEARD:
            return False
        px, py = self.entity_screen(burrower)
        self.floaters.append(Floater("Ding! Flushed out!", px, py - 50, (240, 210, 120), life=1.1, size=24))
        self.rings.append([px, py, 0.0, 70, (240, 210, 120)])
        self.surface_burrower(burrower, quiet=True)
        return True

    def acid_etch(self, enemy):
        """Acid Edge: a hit on a Rock Golem's armour eats into it. True once it's eaten through."""
        if not self.lv("acid"):
            return False
        enemy.etch += 1
        px, py = enemy_anchor(enemy, self.rise, time.time())
        for _ in range(3):   # it sizzles
            self.particles.append(Particle(px, py, random.choice([(150, 230, 90), (200, 255, 140), (90, 170, 60)])))
        return enemy.etch >= ACID_HITS

    def flare_drag(self, m, shades):
        """How much slower a crew member swings in the dark: an Abyssal Shade's (Flares help) or the Void Maw's
        pools (they don't - it's a boss). 1.0 = not in the dark."""
        if any(math.hypot(m.x - p[0], m.y - p[1]) <= SHADE_RADIUS for p in self.void_pools):
            return SHADE_SLOW
        if any(math.hypot(m.x - s.x, m.y - s.y) <= SHADE_RADIUS for s in shades):
            return 1 + (SHADE_SLOW - 1) * max(0.0, 1 - flare_ease(self.lv("flares")))
        return 1.0

    def shade_chill(self, dt):
        """Abyssal Shades: the darkness round each eats at the crew standing in it (Flares keep some of it off)."""
        shades = [e for e in self.enemies if e.spec.get("aura") and e.targetable]
        if not shades:
            return
        ease = max(0.0, 1 - flare_ease(self.lv("flares")))
        for m in self.miners:
            if m.state == "down":
                continue
            shade = next((s for s in shades if math.hypot(m.x - s.x, m.y - s.y) <= SHADE_RADIUS), None)
            if shade is None:
                continue
            dps = SHADE_DPS * max(1.0, crew_hp_at(shade.depth) / crew_hp_at(GRIP_FROM))
            if shade.elite and shade.humbled is None:
                dps *= ELITE_GRIP
            self.hurt(m, dps * ease * dt)
            if random.random() < dt * 4:   # the cold seeping into them
                px, py = self.entity_screen(m, 30)
                self.particles.append(Particle(px, py, random.choice([(110, 90, 170), (60, 50, 90)])))
            if m.hp <= 0:
                if m.attacker:
                    m.attacker.release()
                self.miner_down(m, killer=shade)

    def flare_burn(self, shade, dt):
        """Flares: an Abyssal Shade burns away in the glare."""
        if not self.lv("flares") or shade.boss or not shade.targetable:
            return
        shade.hp -= shade.max_hp * flare_burn(self.lv("flares")) * dt
        if random.random() < dt * 5:   # white-hot sparks off it
            px, py = enemy_anchor(shade, self.rise, time.time())
            self.particles.append(Particle(px, py, random.choice([(255, 255, 230), (255, 230, 150)])))
        if shade.hp <= 0:
            self.kill_enemy(shade)

    def cut_down(self, enemy):
        """Cut Down to Size: a badly hurt elite shrinks back to an ordinary monster (at the same share of its
        health), grips like one and takes share-of-health hits in full - but still pays an elite's bounty."""
        enemy.humbled = enemy.anim_t
        enemy.max_hp /= ELITE_HP
        enemy.hp /= ELITE_HP
        px, py = enemy_anchor(enemy, self.rise, time.time())
        self.floaters.append(Floater("CUT DOWN TO SIZE!", px, py - 60, (255, 120, 100), life=1.4, size=26))
        self.rings.append([px, py, 0.0, 90, (235, 60, 40)])
        for _ in range(18):
            self.particles.append(Particle(px, py, random.choice([(235, 60, 40), (255, 170, 140), (255, 255, 255)]),
                                           big=True))

    def holy(self, enemy):
        """Holy Water: how much harder the undead (zombies and skeletons, never a boss) are hit."""
        if enemy.kind in ("zombie", "skeleton") and self.lv("holywater"):
            return 1 + holy_bonus(self.lv("holywater"))
        return 1.0

    def shrivel(self, enemy, dt):
        """Rock Salt: slimelings dry up and shrivel away."""
        if enemy.kind == "slimeling" and self.lv("salt") and enemy.targetable:
            enemy.hp -= enemy.max_hp * salt_shrivel(self.lv("salt")) * dt
            if random.random() < dt * 4:   # flecks of salt crust flaking off
                px, py = enemy_anchor(enemy, self.rise, time.time())
                self.particles.append(Particle(px, py, (240, 240, 230)))
            if enemy.hp <= 0:
                self.kill_enemy(enemy)

    def transform_enemy(self, enemy, into):
        """e.g. a bat that flew free too long becomes a vampire (full health for the new form)."""
        enemy.become(into)
        enemy.state = "transforming"
        enemy.timer = 0.0
        px, py = enemy_anchor(enemy, self.rise, time.time())
        for _ in range(24):
            self.particles.append(Particle(px, py, random.choice([(120, 60, 160), (80, 40, 110), (170, 120, 200)]),
                                           big=True))
        self.floaters.append(Floater(f"The bat becomes a {enemy.spec['name'].upper()}!", px, py - 40,
                                     (190, 120, 230), life=1.8, size=26))

    def blood_drip(self, miner, enemy):
        """Red drops flying from a drained miner's neck."""
        if random.random() < 0.25:
            px, py = self.entity_screen(miner, 27 + miner.height)
            self.particles.append(Particle(px, py, (200, 20, 40)))

    def grab(self, enemy, miner):
        if miner.role == "hero":   # (no monster can get a grip on the Hero Miner)
            return
        style = enemy.spec["grab"]
        if style in ("head", "orbit", "engulf"):
            enemy.grab_offset = (0.0, 0.0)          # on / around the miner themselves
        else:
            # beside the miner on screen (screen-x follows x - y) so the attack is visible
            side = 1 if (enemy.x - miner.x) - (enemy.y - miner.y) >= 0 else -1
            reach = enemy.spec["reach"] * (0.6 if style == "neck" else 1.15)
            enemy.grab_offset = (side * reach, -side * reach)
            enemy.facing = -side
        enemy.victim = miner
        enemy.state = "attacking"
        if self.clock - self.grab_sound_at >= GRAB_SOUND_GAP:   # one alert, however many grabs at once
            self.grab_sound_at = self.clock
            self.cues.append("grab")
        miner.state = "grabbed"
        miner.attacker = enemy
        px, py = self.entity_screen(miner, 60)
        self.floaters.append(Floater(f"{miner.name}: HELP!", px, py, BAD, life=1.2, size=26))

    def miner_down(self, miner, killer=None):
        """Death is permanent: the miner is buried, and a new recruit arrives when the timer runs out.
        (The camp's people are only ever knocked out: they get back up after upgrades.ko_secs - Smelling Salts.)"""
        if miner.role in CAMP_ROLES:
            miner.state, miner.ko, miner.respawn = "down", True, ko_secs(self.lv("salts"))
            miner.curse, miner.attacker, miner.target = 0.0, None, None
            px, py = self.entity_screen(miner, 40)
            self.floaters.append(Floater(f"{miner.name} is knocked out!", px, py - 20, (255, 210, 120), life=1.8,
                                         size=26))
            for _ in range(10):
                self.particles.append(Particle(px, py, random.choice([(255, 230, 120), (255, 255, 255)])))
            return
        miner.state = "down"
        miner.curse = 0.0
        miner.respawn = RESPAWN_SECS
        self.run["no_deaths"] = False
        if self.lv("switch"):
            self.dead_mans_switch(miner)
        miner.attacker = None
        miner.target = None
        self.bury(miner, killer)
        px, py = self.entity_screen(miner, 30)
        if miner.is_foreman:
            self.floaters.append(Floater(f"Foreman {miner.name} has died! The crew has lost their orders",
                                         px, py - 20, BAD, life=2.4, size=26))
        else:
            self.floaters.append(Floater(f"{miner.name} has died!", px, py - 20, BAD, life=1.8, size=26))
        for _ in range(12):
            self.particles.append(Particle(px, py, miner.shirt, big=True))

    def dead_mans_switch(self, miner):
        """Dead Man's Switch: a fallen crew member's charge goes off - the monsters close by take a share of their
        health (bosses shrug most of it off), and the blocks round where they fell take a share of theirs. (Unlike
        other charges, deep rock doesn't shrug it off: it's an end-game upgrade, and the deep is all it knows.)"""
        rank = self.lv("switch")
        px, py = self.entity_screen(miner, 20)
        self.explosions.append([px, py, 0.0, 70])
        self.cues.append(("boom", 0.6))
        self.shake, self.shake_power = max(self.shake, 0.25), 5
        for e in list(self.enemies):
            if e.targetable and math.hypot(e.x - miner.x, e.y - miner.y) <= SWITCH_RADIUS:
                self.hit_enemy(e, e.max_hp * SWITCH_MONSTERS[rank - 1] * e.pct_scale, floor=False, ring=(255, 150, 60),
                               heavy=True)
        cx, cy = self.cell_of(miner.x, miner.y)
        depth, share = self.depth, SWITCH_BLOCKS[rank - 1]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                block = self.current.get((cx + dx, cy + dy))
                if block and self.depth == depth:
                    self.damage((cx + dx, cy + dy), block.max_hp * share, sparks=4)

    def bury(self, miner, killer=None):
        self.graveyard.append({
            **miner.to_dict(),
            "killer": killer.spec["name"] if killer else "Unknown",
            "died_depth": self.display_depth,
            "died_clock": self.clock,
        })

    def revive(self, m, quiet=False):
        """One of the camp's people comes round, back on their feet at full health."""
        m.state, m.ko, m.hp, m.respawn = "working", False, m.max_hp, 0.0
        if not quiet:
            px, py = self.entity_screen(m, 50)
            self.floaters.append(Floater(f"{m.name} is back on their feet!", px, py, GOOD, life=1.6, size=22))

    def respawn_miner(self, miner):
        """The fallen miner's grave is replaced by a brand-new recruit."""
        recruit = self.recruit(miner.role)
        recruit.x, recruit.y = miner.x, miner.y
        recruit.draw_z = self.column_height(*self.cell_of(miner.x, miner.y))
        self.miners[self.miners.index(miner)] = recruit
        px, py = self.entity_screen(recruit, 50)
        self.floaters.append(Floater(f"{recruit.name} takes {miner.name}'s place", px, py, GOOD,
                                     life=2.0, size=22))

    def enemy_hit_damage(self, enemy, dmg):
        """Player hits (clicks, dynamite) always take at least an Executioner-scaled share of max hp."""
        return max(dmg, enemy.max_hp * enemy_hit_floor(self.lv("executioner")) * enemy.pct_scale)

    def hit_enemy(self, enemy, dmg, floor=True, ring=BAD, by=None, heavy=False):
        """Apply damage to an enemy. `floor` applies the player's Executioner minimum.
        `by` is the miner landing the hit (None = you / your dynamite), credited with the kill."""
        if enemy not in self.enemies or enemy.mode == "split":   # (the split Slime King: hit its chunks)
            return
        if enemy.state == "lurking":   # a Mimic, found out
            self.spring_mimic(enemy)
        if enemy.state == "burrowing":   # a Burrower's mound: dug out
            self.surface_burrower(enemy)
        if enemy not in self.enemies:   # (Ten-Foot Poles or Booby Traps finished it off as it came up)
            return
        holy = self.holy(enemy)
        dealt = ((self.enemy_hit_damage(enemy, dmg) if floor else dmg) * enemy.dmg_taken * holy
                 * self.armour(enemy, heavy))
        enemy.hp -= dealt
        if enemy.bro_hp:   # The Burrow Brothers: the blow lands on the one above ground
            self.bro_hit(enemy, dealt)
        enemy.flash = 0.12
        px, py = enemy_anchor(enemy, self.rise, time.time())
        self.rings.append([px, py + 18, 0.0, 30, ring])
        for _ in range(6):
            self.particles.append(Particle(px, py, enemy.spec["gore"]))
        if holy > 1 and random.random() < 0.5:   # a hiss of holy water
            self.particles.append(Particle(px, py, random.choice([(220, 235, 255), (255, 245, 200)])))
        if enemy.elite and enemy.humbled is None and not enemy.boss and self.lv("cutdown") and \
                0 < enemy.hp <= enemy.max_hp * CUTDOWN_AT:
            self.cut_down(enemy)
        split = enemy.spec.get("split")   # slimes burst apart at half health (the King always does)
        if split and enemy.mode != "split" and enemy.hp <= enemy.max_hp * SLIME_SPLIT_AT and \
                (enemy.hp > 0 or enemy.boss):
            self.split_slime(enemy)
            return
        if enemy.hp <= 0:
            if enemy.kind == "bonetyrant" and not enemy.reformed:
                self.bone_collapse(enemy)
                return
            self.kill_enemy(enemy, by)

    def player_hit_enemy(self, enemy, pos=None):
        """You click a monster: Monster Slayer damage, Critical Smite, then Cleave onto neighbours.
        `pos` is where you clicked (The Void Maw only really feels a click on its open eye)."""
        self.run["no_monster_clicks"] = False
        dmg = self.monster_hit_damage() * self.combo_mult()
        if random.random() < 0.05 * self.lv("smite"):
            dmg *= 3
            px, py = enemy_anchor(enemy, self.rise, time.time())
            self.floaters.append(Floater("SMITE!", px, py - 30, (255, 120, 120), life=0.7, size=24))
        dealt = self.enemy_hit_damage(enemy, dmg)
        if enemy.kind == "voidmaw":   # (after Executioner's minimum, so even that only bites on the eye)
            dealt *= self.void_eye_hit(enemy, pos)
        if self.lv("golddust") and enemy in self.enemies:   # Gold Dust: the share of its bounty this hit takes
            px, py = enemy_anchor(enemy, self.rise, time.time())
            self.gold_dust(min(dealt, enemy.hp) / enemy.max_hp * self.bounty_worth(enemy), px, py)
        self.hit_enemy(enemy, dealt, floor=False)
        if self.lv("cleave"):
            for other in list(self.enemies):
                if other is not enemy and other.targetable and \
                        math.hypot(other.x - enemy.x, other.y - enemy.y) <= 1.5:
                    self.hit_enemy(other, dealt * 0.2 * self.lv("cleave"), floor=False, ring=(255, 160, 160))

    def miner_strike(self, miner):
        """A grabbed miner hits back at whatever has hold of them (Self Defense / Last Stand)."""
        enemy = miner.attacker
        share = miner_strike(self.lv("defense"))
        if not enemy or share <= 0 or not enemy.targetable:
            return
        if miner.hp < miner.max_hp * LAST_STAND_HP:
            share *= last_stand_mult(self.lv("laststand"))
        miner.anim = 1.0
        self.give_xp(miner, share * XP_PER_MONSTER)
        share *= level_mult(miner.level)
        self.hit_enemy(enemy, enemy.max_hp * share * enemy.pct_scale, floor=False, ring=miner.shirt, by=miner)

    def bounty_worth(self, enemy):
        """What killing this monster pays (before Midas Touch)."""
        return (enemy.bounty_base * value_mult(self.lv("value")) * bounty_mult(self.lv("bounty"))
                * self.art_mult("bounty"))

    def kill_credit(self, enemy, by):
        """Who gets the kill: a guard still standing who was fighting it in the last GUARD_ASSIST_SECS, even if
        you or the miner it grabbed landed the last blow; otherwise the crew member who did (None = you)."""
        hit = getattr(enemy, "guard_hit", None)
        if hit:
            guard, when = hit
            if self.clock - when <= GUARD_ASSIST_SECS and guard in self.miners and guard.state != "down":
                return guard
        return by

    def kill_bonus(self, enemy):
        """Trophy Hunter and Killing Spree: how many times its bounty this kill pays (bosses: just the bounty)."""
        if enemy.boss:
            return 1.0
        mult = 1.0
        px, py = enemy_anchor(enemy, self.rise, time.time())
        if enemy.elite and self.lv("trophy"):
            mult *= trophy_mult(self.lv("trophy"))
            self.floaters.append(Floater("TROPHY!", px, py - 48, GOLD, life=1.4, size=32))
            self.rings.append([px, py, 0.0, 90, GOLD])
            for _ in range(24):
                self.particles.append(Particle(px, py, random.choice([GOLD, (255, 235, 150), (255, 255, 255)]), big=True))
        if self.lv("spree"):
            self.spree = self.spree + 1 if self.clock - self.spree_at <= SPREE_WINDOW else 1
            self.spree_at = self.clock
            n = min(self.spree, SPREE_CAP)
            mult *= 1 + spree_step(self.lv("spree")) * (n - 1)
            if n >= 2:
                self.floaters.append(Floater(f"SPREE x{n}", px, py - 70, (255, 120, 90), life=1.0, size=22 + 2 * n))
        return mult

    def kill_enemy(self, enemy, by=None):
        self.enemies.remove(enemy)
        self.lifetime["monsters"] += 1
        if enemy.elite and not enemy.boss:
            self.achieve("elite")
        bounty = self.earn(self.bounty_worth(enemy) * self.kill_bonus(enemy))
        credit = self.kill_credit(enemy, by)
        if credit:   # a guard who was fighting it, or a miner who fought it off themselves
            credit.stats["monsters"] += 1
            credit.stats["gold"] += bounty
        px, py = enemy_anchor(enemy, self.rise, time.time())
        self.floaters.append(Floater(f"+{fmt(bounty)}", px, py - 20, GOLD, size=28, coin=True))
        self.fly_coins(px, py, 4)
        self.rings.append([px, py + 18, 0.0, 60, GOOD])
        gore = enemy.spec["gore"]
        for _ in range(26):
            self.particles.append(Particle(px, py, random.choice([gore, tuple(c // 2 for c in gore), (200, 60, 60)]),
                                           big=True))
        victim = enemy.victim
        if victim and victim.attacker is enemy:
            victim.state = "working"
            victim.attacker = None
            vx, vy = self.entity_screen(victim, 60)
            if credit is victim:
                self.floaters.append(Floater("Fought it off!", vx, vy, GOOD, life=1.3, size=26))
            else:
                victim.stats["saved"] += 1
                # (your click landing the blow is your rescue, whoever helped - they still get the kill and its xp)
                text = f"Saved by {credit.name}!" if credit and credit.role == "guard" and by is credit else "Saved!"
                self.floaters.append(Floater(text, vx, vy, GOOD, life=1.3, size=28))
        if self.lv("volatile") and not enemy.boss:
            self.volatile_blast(enemy)
        if enemy.boss:
            self.boss_defeated(enemy)

    def volatile_blast(self, enemy):
        """Volatile Remains: a dying monster bursts, blasting the block under it for VOLATILE_BLAST times its max
        health and the eight around that for half (about a fifth of a late crew's digging). (Kept small on screen - deep down monsters die every second.)"""
        cell = self.cell_of(enemy.x, enemy.y)
        dmg = enemy.max_hp * VOLATILE_BLAST
        px, py = enemy_anchor(enemy, self.rise, time.time())
        self.explosions.append([px, py, 0.0, 30 + (14 if enemy.elite else 0)])
        self.cues.append(("boom", 0.25))
        depth = self.depth
        if not self.damage(cell, dmg, sparks=6):
            return
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (dx, dy) != (0, 0) and self.depth == depth:
                    self.damage((cell[0] + dx, cell[1] + dy), dmg * 0.5, sparks=2)

    # ----- upgrades -------------------------------------------------------
    def available(self, up):
        """Prerequisites owned, depth milestone reached - and for the camp people's upgrades, someone hired."""
        return is_unlocked(up, self.levels) and depth_reached(up, self.depth) and (bool(self.camp) or not up["camp"])

    def can_buy(self, up):
        return self.available(up) and not is_maxed(up, self.levels) and self.gold >= self.cost(up)

    def cost(self, up):
        off = 1 - ROUNDING_OFF if "rounding" in self.camp_items else 1.0   # (Rounding Errors: always in your favour)
        return math.ceil(self.base_cost(up) * self.art_mult("cost") * off)

    def base_cost(self, up):
        return upgrade_cost(up, self.levels)

    def buy(self, up):
        if not self.can_buy(up):
            return False
        cost = self.cost(up)
        self.ledger_lost = "ledger" in self.camp_items and random.random() < LEDGER_CHANCE
        if not self.ledger_lost:   # (the Crooked Ledger: it never made it onto the page)
            self.gold -= cost
        self.levels[up["key"]] += 1
        if up["key"] in HIRE_UPGRADES or (up["key"] == "miners" and self.levels["miners"] > 1):
            self.run["one_miner"] = False   # (Protect Mr. President)
        if "ledger" in self.camp_items:
            self.feats["ledger"] += self.ledger_lost
            self.feats["ledger_streak"] = self.feats["ledger_streak"] + 1 if self.ledger_lost else 0
            if self.feats["ledger_streak"] >= 3:
                self.achieve("lucky")
        self.sync_miners(announce=True)
        return True

    # ----- mining ---------------------------------------------------------
    def damage(self, cell, dmg, sparks=3, by=None):
        """Apply damage to one block. Returns False if the layer changed (stop chaining).
        `by` is the miner responsible, credited with the block and its gold if it breaks."""
        block = self.current.get(cell)
        if not block:
            return True
        lurker = self.lurker_at(cell)
        if lurker:   # a Mimic was sitting on it: it springs, and bites whoever was digging
            self.spring_mimic(lurker, by)
        if by:
            self.give_xp(by, min(dmg, block.hp) / block.max_hp * XP_PER_BLOCK)
        block.hp -= dmg
        px, py = self.cell_screen(cell)
        spec = BLOCKS[block.kind]
        for _ in range(sparks):
            self.particles.append(Particle(px, py, spec.get("fleck") or block_color(block.kind, self.depth)))
        if block.hp <= 0:
            depth = self.depth
            self.break_block(cell, block, by)
            return depth == self.depth
        return True

    def splash(self, cell, dmg, color, by=None):
        targets = [(cell[0] + dx, cell[1] + dy) for dx, dy in NEIGHBOURS]
        depth = self.depth
        for t in targets:
            if self.depth != depth:
                return
            if t in self.current:
                self.damage(t, dmg, sparks=2, by=by)
        px, py = self.cell_screen(cell)
        self.rings.append([px, py, 0.0, 70, color])

    def miner_hit(self, cell, miner=None):
        block = self.current.get(cell)
        if not block:
            return
        dmg = self.miner_hit_damage() * self.pick_bonus(miner, cell, 1.0) * (level_mult(miner.level) if miner else 1)
        if miner and miner.role == "ghost":
            dmg *= GHOST_POWER
        elif miner and miner.role == "hero":   # the Hero Miner: a legend with a pick
            dmg *= HERO_POWER * self.art_mult("hero")
        if miner and "fringe" in self.camp_items and self.under_banner(miner):   # (the Gold Fringe)
            dmg *= 1 + FRINGE_POWER
        if is_ore(block):
            dmg *= ore_damage_mult(self.lv("diamond"))
        crit = random.random() < 0.05 * self.lv("crit") + self.art_add("crit")
        if crit:
            dmg *= 3
            self.crit_effects(cell, miner)
        below = self.next.get(cell)
        if below and self.lv("deepstrike"):   # Deep Strike: crack the block underneath (never breaks it)
            below.hp = max(below.max_hp * 0.05, below.hp - dmg * 0.1 * self.lv("deepstrike"))
        if not self.damage(cell, dmg, by=miner):
            return
        if miner and miner.role == "hero" and "heirloom" in self.camp_items:   # the Heirloom Pickaxe
            miner.blows = getattr(miner, "blows", 0) + 1
            if miner.blows % HEIRLOOM_EVERY == 0 and not self.heirloom_split(cell, dmg, miner):
                return
        if miner and getattr(miner, "forged", 0) > 0:   # an explosive pick from the Goblin Engineer
            if not self.forge_blast(cell, dmg, miner):
                return
        if crit and self.lv("quake"):
            self.splash(cell, dmg * 0.25 * self.lv("quake"), BRANCHES["tools"]["color"], by=miner)

    def forge_blast(self, cell, dmg, miner):
        """An explosive pick goes off: the 8 blocks round the one it hit take a share of the blow, and the 3x3
        underneath is cracked (never broken). False if the layer changed (stop chaining)."""
        depth = self.depth
        share = miner.blast
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                c = (cell[0] + dx, cell[1] + dy)
                below = self.next.get(c)
                if below:
                    below.hp = max(below.max_hp * 0.05, below.hp - dmg * FORGE_BELOW * share / FORGE_BLAST)
                if (dx or dy) and c in self.current:
                    self.damage(c, dmg * share, sparks=0, by=miner)
                    if self.depth != depth:
                        return False
        if self.clock - getattr(miner, "blast_fx", -1e9) >= FORGE_FX_GAP:   # a puff of flame and smoke
            miner.blast_fx = self.clock
            px, py = self.cell_screen(cell)
            self.rings.append([px, py, 0.0, 60, (255, 150, 60)])
            for _ in range(8):
                self.particles.append(Particle(px, py, random.choice([(255, 200, 90), (255, 120, 40), (90, 80, 76)]),
                                               big=True))
        return True

    def is_glazed(self, cell):
        """Glazed Fists: is this block still glazed from one of Mitts' slams?"""
        mark = self.glazed.get(cell)
        return bool(mark) and mark[0] == self.depth and mark[1] > self.clock

    def pick_bonus(self, miner, cell, weight):
        """Hot Streak (hits in a row on one block), a freshly sharpened pick (Whetstone) and a block Mitts has
        glazed (Glazed Fists). `weight` = how much one hit counts towards the streak (a drill's rattle is a fraction)."""
        if not miner:
            return 1.0
        glaze = 1 + GLAZE_BONUS if self.glazed and self.is_glazed(cell) else 1.0
        if miner.streak_cell != cell:
            miner.streak_cell, miner.streak = cell, 0.0
        bonus = 1 + streak_bonus(self.lv("streak")) * miner.streak
        if self.lv("streak"):
            miner.streak = min(STREAK_CAP, miner.streak + weight)
            if miner.streak >= STREAK_CAP / 2 and random.random() < 0.5 * weight:   # on a roll: flames
                px, py = self.cell_screen(cell)
                self.particles.append(Particle(px, py - 4, random.choice([(255, 150, 40), (255, 210, 80)])))
        if miner.sharp > 0:
            bonus *= 1 + whetstone_boost(self.lv("whetstone"))
        return bonus * glaze

    def crit_effects(self, cell, miner):
        """The look of a critical strike: the miner's overhead slam, an impact starburst, and with Seismic Strikes
        a small wave rippling out to the blocks it shakes. A late crew crits dozens of times a second, so it's kept
        light: no label (a crew critting every few frames would bury the screen in text), a few waves at once, no screen
        jolt."""
        px, py = self.cell_screen(cell)
        if miner:
            miner.crit = CRIT_ANIM_SECS
        self.crit_bursts.append([px, py, 0.0])
        for _ in range(6):
            color = random.choice([(255, 230, 150), (255, 160, 70), (255, 255, 255)])
            self.particles.append(Particle(px, py, color, big=True))
        if self.lv("quake") and sum(1 for q in self.quakes if q[4] == CRIT_QUAKE_REACH) < CRIT_QUAKES_SHOWN:
            self.quakes.append([cell[0] + 0.5, cell[1] + 0.5, 0.0, set(), CRIT_QUAKE_REACH])

    def player_hit(self, cell, sparks=6, ring_color=(255, 255, 255), manual=False):
        """A click on a block - yours (manual) or the Auto-Tapper's."""
        block = self.current.get(cell)
        if not block:
            return
        dmg = self.click_hit_damage()
        px, py = self.cell_screen(cell)
        if manual:
            self.run["no_block_clicks"] = False
            dmg *= self.combo_mult()
            if self.golden and self.golden[0] == cell:
                self.golden_jackpot(cell, block)
        if random.random() < 0.05 * self.lv("steady"):
            dmg *= 3
        if manual and self.lv("golden"):   # Golden Touch: your own clicks earn as you dig
            self.earn(block.value * value_mult(self.lv("value")) * 0.05 * self.lv("golden"))
            for _ in range(3):
                self.particles.append(Particle(px, py, GOLD))
        if manual and self.lv("golddust"):   # Gold Dust: paid for the share of the block the click knocks off
            self.gold_dust(min(dmg, block.hp) / block.max_hp * block.value * value_mult(self.lv("value")), px, py)
        self.rings.append([px, py, 0.0, 26, ring_color])
        if manual and block.bones and dmg >= block.hp:   # you clicked the bones out yourself: a little extra
            bonus = self.earn(block.value * value_mult(self.lv("value")) * BONE_BONUS)
            self.floaters.append(Floater(f"Bones! +{fmt(bonus)}", px, py - 36, (235, 228, 205), size=22, coin=True))
        if self.damage(cell, dmg, sparks) and self.lv("shockwave"):
            self.splash(cell, dmg * 0.2 * self.lv("shockwave"), BRANCHES["hands"]["color"])

    def gold_dust(self, worth, px, py):
        """Gold Dust: a click earns a share of what the damage it dealt was worth."""
        self.earn(worth * dust_share(self.lv("golddust")))
        for _ in range(2):
            self.particles.append(Particle(px, py, random.choice([GOLD, (255, 240, 170)])))

    def mitts_click(self, cell):
        """One of your clicks, at `cell`, counts towards Mitts' next leap (he goes for the latest one) - unless
        something has hold of him (or he's out cold): then he's not listening."""
        for golem in self.miners:
            if golem.role == "claygolem" and golem.state == "working":
                golem.clicks = min(MITTS_CLICKS, getattr(golem, "clicks", 0) + 1)
                golem.leap_to, golem.idle = cell, 0.0

    def combo_click(self):
        """Count one of your clicks towards the combo - any click, hit or miss, keeps it going."""
        self.feats["clicks"] += 1
        if not self.lv("combo"):
            return
        self.combo = self.combo + 1 if self.combo_timer > 0 else 1
        self.combo_timer = COMBO_WINDOW
        if self.combo >= 20:
            self.achieve("combo_max")

    def combo_mult(self):
        """Damage multiplier the current combo gives your clicks."""
        if not self.lv("combo"):
            return 1.0
        return 1 + combo_step(self.lv("combo")) * min(self.combo, COMBO_CAP)

    def golden_jackpot(self, cell, block):
        """Golden Blocks: a jackpot of this layer's average block many times over - or of the golden block itself,
        if it's richer (so it's never a let-down for having landed on plain rock)."""
        self.cues.append("jackpot")
        self.feats["jackpots"] += 1
        base = max(block.value, self.layer_value / (GRID * GRID))
        jackpot = self.earn(base * value_mult(self.lv("value")) * golden_payout(self.lv("goldblock")))
        px, py = self.cell_screen(cell)
        self.floaters.append(Floater(f"JACKPOT! +{fmt(jackpot)}", px, py - 50, GOLD, life=2.2, size=36, coin=True))
        self.fly_coins(px, py, 14)
        self.rings.append([px, py, 0.0, 120, GOLD])
        for _ in range(24):
            self.particles.append(Particle(px, py, random.choice([GOLD, (255, 240, 170), (255, 255, 255)]), big=True))
        self.golden = None

    def slam(self, cell, charge, target=None, held=None):
        """Charged Slam: a huge hit on `cell` (charge 0..1) that shakes the blocks around it.
        Monsters in the blast - and `target`, the one under the cursor - take up to 2x a monster click.
        `held`: seconds you held the button for it (None: not yours - Phantom Slam's ghostly hand)."""
        if cell not in self.current:
            return
        yours = held is not None
        if self.golden and self.golden[0] == cell:   # slammed, not clicked: the jackpot is still yours
            self.golden_jackpot(cell, self.current[cell])
        if yours:
            self.run["no_block_clicks"] = False
            if charge >= 1:
                self.achieve("full_slam")
            if charge >= MITTS_FOLLOW:   # (the Clay Golem comes in right behind it)
                self.mitts_follow(cell)
        power = 0.3 + 0.7 * charge
        dmg = self.click_hit_damage() * slam_mult(self.lv("slam")) * power
        if yours:   # holding for a slam costs you the clicks you'd have made: it pays for them as clicks would
            self.slam_pay(cell, dmg, max(slam_mult(self.lv("slam")) * power, held * SLAM_CLICK_RATE))
        click = self.monster_hit_damage() * self.combo_mult()
        for e in list(self.enemies):
            in_blast = max(abs(e.x - (cell[0] + 0.5)), abs(e.y - (cell[1] + 0.5))) <= 1.5
            if e.targetable and (in_blast or e is target):
                if yours:
                    self.run["no_monster_clicks"] = False
                self.hit_enemy(e, self.enemy_hit_damage(e, click) * SLAM_MONSTER_MULT * power, floor=False,
                               heavy=True)
        px, py = self.cell_screen(cell)
        self.crit_bursts.append([px, py, 0.0])
        self.quakes.append([cell[0] + 0.5, cell[1] + 0.5, 0.0, set(), QUAKE_RADIUS])
        self.shake, self.shake_power = 0.25, 4 + 4 * charge
        self.cues.append(("smash", 0.6 + 0.4 * charge))   # (louder the longer it was charged)
        self.floaters.append(Floater("SLAM!", px, py - 70, (220, 160, 255), life=1.0, size=30 + int(14 * charge)))
        depth = self.depth
        around = [(cell[0] + dx, cell[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
        if not self.damage(cell, dmg, sparks=10):
            return
        for c in around:   # the shock rolls into the blocks around it at half strength
            if self.depth != depth:
                return
            self.damage(c, dmg * 0.5, sparks=2)

    def slam_pay(self, cell, dmg, clicks):
        """A Charged Slam of yours earns what clicking would have: Golden Touch for every one of the `clicks` it
        stands for, and Gold Dust for the share of the block it knocks off."""
        block = self.current[cell]
        worth = block.value * value_mult(self.lv("value"))
        px, py = self.cell_screen(cell)
        if self.lv("golden"):
            self.earn(worth * 0.05 * self.lv("golden") * clicks)
            for _ in range(6):
                self.particles.append(Particle(px, py, GOLD))
        if self.lv("golddust"):
            self.gold_dust(min(dmg, block.hp) / block.max_hp * worth, px, py)

    def vent_boiler(self):
        """Steam Boiler: a full head of steam scalds every monster on the board (bosses, and the Slime King's
        chunks, stand firm). Bounties are paid, anyone grabbed is freed, and the next wave holds back."""
        if self.boiler < 1.0:
            return False
        self.boiler, self.steam = 0.0, 0.0
        self.achieve("boiler")
        self.cues += [("fuse", 1.0), ("boom", 0.5)]
        self.shake, self.shake_power = 0.4, 5
        for e in list(self.enemies):
            if not e.boss and not e.spec.get("slam") and e in self.enemies:
                self.kill_enemy(e)
        self.enemy_timer = max(self.enemy_timer, self.wave_interval())   # a reprieve before the next wave
        self.floaters.append(Floater("STEAM!", W / 2, 230, (225, 235, 245), life=1.6, size=48))
        return True

    def phantom_target(self):
        """Where a slam does the most: the block with the most (ore counting extra) in the 3x3 around it."""
        def score(c):
            around = [self.current.get((c[0] + dx, c[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            return sum(1.5 if is_ore(b) else 1.0 for b in around if b) + random.random() * 0.5
        return max(self.current, key=score) if self.current else None

    def update_phantom(self, dt):
        """Phantom Slam: the ghostly hand picks a block, hangs over it charging, then slams it."""
        self.phantom_timer += dt
        interval = phantom_interval(self.lv("phantom")) / self.tick()
        if self.phantom_timer < interval - PHANTOM_WINDUP:
            return
        if self.phantom is None or self.phantom[0] not in self.current:   # (its block broke: find another)
            cell = self.phantom_target()
            self.phantom = [cell, 0.0] if cell else None
            if not self.phantom:
                return
        self.phantom[1] += dt
        if self.phantom_timer >= interval:
            cell = self.phantom[0]
            self.phantom, self.phantom_timer = None, 0.0
            self.slam(cell, PHANTOM_CHARGE)

    def throw_dynamite(self):
        """Toss a lit bundle onto a random block; it goes off when the fuse burns down."""
        if not self.current:
            return
        bomb = Bomb(random.choice(list(self.current)), 1 + self.lv("bigbombs"))
        self.bombs.append(bomb)
        px, py = self.cell_screen(bomb.cell)
        self.floaters.append(Floater("Fire in the hole!", px, py - 60, (255, 170, 80), life=1.6, size=26))

    def detonate(self, bomb):
        cx, cy = bomb.cell
        radius = bomb.radius
        dmg = self.click_hit_damage() * 10
        z = self.column_height(cx, cy) + self.rise
        px, py = iso(cx + 0.5, cy + 0.5, z)
        charge = bomb.owner is not None   # a demolitionist's planted charge: smaller and targeted
        self.cues.append(("boom", CHARGE_BOOM if charge else 1.0))
        size = 36 if charge else 46 + 26 * radius
        self.explosions.append([px, py - 10, 0.0, size])
        if self.shake < 0.25:
            self.shake, self.shake_power = (0.2, 4) if charge else (0.35 + 0.1 * radius, 5 + 3 * radius)
        self.flash = 0.06 if charge else 0.12
        self.floaters.append(Floater("BOOM!", px, py - 40, (255, 120, 60), life=1.3,
                                     size=34 if charge else 44 + 10 * radius))
        self.rings.append([px, py, 0.0, 120 * radius, (255, 150, 60)])
        self.rings.append([px, py, 0.0, 70 * radius, (255, 240, 200)])
        for _ in range(30 * radius):   # embers and debris
            self.particles.append(Particle(px, py - 10, random.choice([(255, 220, 120), (255, 140, 40),
                                                                       (220, 70, 30), (70, 60, 60)]), big=True))
        for _ in range(8 + 6 * radius):
            self.smoke.append(Smoke(px, py - 14, size=8 + 4 * radius))
        for e in list(self.enemies):   # dynamite hurts monsters caught in the blast too
            if e.targetable and max(abs(e.x - (cx + 0.5)), abs(e.y - (cy + 0.5))) <= radius + 0.6:
                if charge:
                    self.hit_enemy(e, e.max_hp * 0.25 * e.pct_scale, floor=False, by=bomb.owner, heavy=True)
                else:   # (Bunker Buster: shaped charges, far deadlier - Executioner's minimum and all)
                    self.hit_enemy(e, self.enemy_hit_damage(e, self.monster_hit_damage() * 3) * (1 + self.lv("bunker")),
                                   floor=False, heavy=True)
        depth = self.depth
        if charge:   # a planted charge levels every block in the 3x3 around it
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    block = self.current.get((cx + dx, cy + dy))
                    if self.depth != depth:
                        return
                    if block:
                        # (it levels them - though deep rock only cracks: see blocks.crack_share)
                        blast = block.hp + 1e-9 if self.depth <= DEEP_ROCK_FROM else block.max_hp * crack_share(self.depth)
                        self.damage((cx + dx, cy + dy), blast, sparks=2, by=bomb.owner)
            return
        if self.lv("bunker"):   # Bunker Buster: the blast goes on down into the next layer (cracking, never breaking)
            below = dmg * BUNKER_BELOW * self.lv("bunker")
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    block = self.next.get((cx + dx, cy + dy))
                    if block:
                        block.hp = max(block.max_hp * 0.05, block.hp - below)
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if self.depth != depth:
                    return
                self.damage((cx + dx, cy + dy), dmg, sparks=2)

    def break_block(self, cell, block, by=None):
        del self.current[cell]
        self.lifetime["blocks"] += 1
        earned = block.value * value_mult(self.lv("value"))
        if is_ore(block):
            earned *= 1 + 0.1 * self.lv("treasure")
        if by and "fringe" in self.camp_items and self.under_banner(by):   # (dug under the Gold Fringe)
            earned *= 1 + FRINGE_VALUE
        px, py = self.cell_screen(cell)
        if random.random() < 0.04 * self.lv("double"):
            earned *= 2
            self.floaters.append(Floater("x2!", px + 26, py - 34, GOOD, size=22))
        if random.random() < 0.02 * self.lv("goldrush"):
            nugget = block.value * value_mult(self.lv("value")) * 25
            earned += nugget
            self.floaters.append(Floater(f"NUGGET! +{fmt(nugget)}", px, py - 50, GOLD, life=1.8, size=30,
                                         coin=True))
            self.fly_coins(px, py, 6)
            self.rings.append([px, py, 0.0, 90, GOLD])
        if block.chest:   # Buried Treasure
            self.feats["chests"] += 1
            self.cues.append("chest")
            treasure = block.value * value_mult(self.lv("value")) * CHEST_PAYOUT
            earned += treasure
            self.chest_fx.append([px, py, 0.0])
            self.floaters.append(Floater(f"TREASURE! +{fmt(treasure)}", px, py - 56, GOLD, life=2.0, size=30,
                                         coin=True))
            self.fly_coins(px, py, 8)
        if self.golden and self.golden[0] == cell:   # broken before anyone clicked it
            if by is None:   # your own splash (shockwave, slam, dynamite) broke it: the jackpot is still yours
                self.golden_jackpot(cell, block)
            self.golden = None
        if self.casual:
            earned *= CASUAL_BLOCK_GOLD
        earned = self.earn(earned)
        self.total_blocks += 1
        if by:
            by.stats["blocks"] += 1
            by.stats["gold"] += earned
        spec = BLOCKS[block.kind]
        for _ in range(14):
            self.particles.append(Particle(px, py, block_color(block.kind, self.depth), big=True))
        if block.bones:   # bone chips flying
            for _ in range(8):
                self.particles.append(Particle(px, py, random.choice([(235, 228, 205), (200, 190, 165)]), big=True))
            if spec.get("fleck"):
                self.particles.append(Particle(px, py, spec["fleck"], big=True))
        self.floaters.append(Floater(f"+{fmt(earned)}", px, py - 10, GOLD, coin=True))
        self.fly_coins(px, py, 2 if is_ore(block) else 1)
        for m in self.miners:
            if m.target == cell:
                m.target = None
        if by and by.digs and is_ore(block) and self.lv("vein") and not self.in_vein:
            self.follow_vein(cell, block.kind, by)
        if block.artifact:
            self.find_artifact(px, py)
        if not self.current:
            if self.boss():
                self.tell_boss_gate()
            else:
                self.descend()

    def follow_vein(self, cell, kind, miner):
        """Vein Follower: crack every block of the same ore connected to the one just broken."""
        vein, frontier = set(), [cell]
        while frontier:
            cx, cy = frontier.pop()
            for dx, dy in NEIGHBOURS:
                n = (cx + dx, cy + dy)
                if n not in vein and n in self.current and self.current[n].kind == kind:
                    vein.add(n)
                    frontier.append(n)
        if not vein:
            return
        self.in_vein = True   # cracks that break more ore don't start veins of their own
        depth = self.depth
        try:
            for n in sorted(vein, key=lambda c: abs(c[0] - cell[0]) + abs(c[1] - cell[1])):
                block = self.current.get(n)
                if self.depth != depth:
                    return
                if block:
                    px, py = self.cell_screen(n)
                    self.rings.append([px, py, 0.0, 34, BLOCKS[kind].get("fleck", GOLD)])
                    self.damage(n, block.max_hp * vein_share(self.lv("vein")) * crack_share(self.depth), sparks=4,
                                by=miner)
        finally:
            self.in_vein = False

    def descend(self, award=True):
        if self.depth >= EXPEDITION_DEPTH:   # the bottom of the expedition: only the collapse leads on
            return
        if award:
            self.layer_clear_bonus(self.depth + 1)
        self.depth += 1
        self.current = self.next
        self.layer_value = layer_value(self.current)
        self.next = self.new_layer(self.depth + 1, ore_mult(self.lv("prospector")) * self.art_mult("ore"),
                                   chest_chance(self.lv("chests")), richness=ore_richness(self.lv("prospector")))
        self.lifetime["deepest"] = max(self.lifetime["deepest"], self.display_depth)
        self.bury_artifact(self.next, self.depth + 1)
        self.rise = -1.0
        for m in self.miners:
            m.draw_z += 1
            m.target = None
            if m.digs:   # (done skirmishing with a boss, if they were)
                m.goal = None
        for e in self.enemies:
            e.draw_z += 1
        self.floaters.append(Floater(f"Depth {self.display_depth}m", W / 2, 120, TEXT, life=2.0, size=40))
        biome = biome_at(self.depth)
        if biome is not biome_at(self.depth - 1):   # broke through into a new biome
            self.floaters.append(Floater(biome["name"].upper(), W / 2, 260, biome["accent"], life=3.5, size=48))
            self.floaters.append(Floater("You've broken into a new part of the mine", W / 2, 300, TEXT, life=3.5,
                                         size=24))
        unlocked = [u for u in UPGRADES if u["depth"] == self.depth and (self.camp or not u["camp"])]
        if unlocked:   # depth milestone: new upgrades open up
            self.new_unlocks.update(u["key"] for u in unlocked)
            names = ", ".join(u["name"] for u in unlocked)
            self.notice = [f"{self.display_depth}m reached - new upgrades: {names}", 5.0]
        if self.depth == ENEMY_START_DEPTH:   # first time this deep: the monsters find you, right away
            self.enemy_timer = 0.0
        if boss_for(self.depth) and self.boss_done < self.depth:
            self.spawn_boss()
        if self.lv("secondwind"):
            self.second_wind = SECOND_WIND_SECS
            self.floaters.append(Floater("Second wind!", W / 2, 160, BRANCHES["crew"]["color"], life=1.6, size=28))

    def layer_clear_bonus(self, new_depth):
        """Gold for clearing a layer: a share of everything it held, doubled on every 5th metre."""
        milestone = new_depth % MILESTONE_EVERY == 0
        surveyor = self.lv("surveyor")
        share = clear_share(surveyor) * (milestone_mult(surveyor) if milestone else 1)
        bonus = self.earn(self.layer_value * value_mult(self.lv("value")) * share * self.art_mult("clear"))
        title = f"{self.shown(new_depth)}m MILESTONE!" if milestone else "LAYER CLEAR!"
        self.floaters.append(Floater(f"{title} +{fmt(bonus)}", W / 2, 168, GOLD, life=2.6,
                                     size=40 if milestone else 34, coin=True))
        self.fly_coins(W / 2, 168, 16 if milestone else 10)
        self.rings.append([W / 2, 176, 0.0, 160 if milestone else 110, GOLD])

    def pick_target(self, miner):
        if not self.current:
            return None
        claimed = {m.target for m in self.miners + self.ghosts if m is not miner and m.target}
        seek_ore = self.lv("treasure") > 0
        dowsing = miner.role == "hero" and "divining" in self.camp_items   # (Rocco's Divining Rod: artifacts first)
        best, best_d = None, 1e9
        for cell, block in self.current.items():
            d = (cell[0] + 0.5 - miner.x) ** 2 + (cell[1] + 0.5 - miner.y) ** 2
            if cell in claimed:
                d += 6
            if seek_ore and is_ore(block) and cell not in claimed:   # Treasure Map: unclaimed ore first
                d -= 1000
            if dowsing and block.artifact:
                d -= 5000
            if self.golden and self.golden[0] == cell:   # leave the golden block for the player
                d += 5000
            d += random.random() * 0.3
            if d < best_d:
                best, best_d = cell, d
        if dowsing and best and self.current[best].artifact and self.dowsed != self.depth:
            self.dowsed = self.depth   # (once a layer: the rod's found something)
            px, py = self.entity_screen(miner, 50)
            self.floaters.append(Floater("The rod twitches!", px, py, GOLD, life=1.6, size=22))
        return best

    # ----- foreman --------------------------------------------------------
    def update_foreman(self, boss, dt, speed):
        """Walk from miner to miner, stop to supervise each one, and shout orders."""
        crew = [m for m in self.workers() if m.state == "working"]
        boss.walk_timer -= dt
        if boss.inspecting not in crew or boss.walk_timer <= 0:
            others = [m for m in crew if m is not boss.inspecting] or crew
            boss.inspecting = random.choice(others) if others else None
            boss.walk_timer = random.uniform(4.0, 7.0)
        boss.anim = max(0.0, boss.anim - dt * 2)
        if not boss.inspecting:   # (no crew at work to supervise: he paces about)
            self.stroll(boss, dt, speed)
        if boss.inspecting:
            dx, dy = boss.inspecting.x - boss.x, boss.inspecting.y - boss.y
            dist = math.hypot(dx, dy)
            if dist > 0.03:
                boss.facing = 1 if (dx - dy) >= 0 else -1
            if dist > FOREMAN_STAND_OFF:   # stroll over (a bit slower than the crew)
                step = min(dist - FOREMAN_STAND_OFF, speed * dt)
                boss.x += dx / dist * step
                boss.y += dy / dist * step
        boss.bark_timer -= dt
        if boss.bark_timer <= 0:
            boss.bark_timer = random.uniform(3.0, 6.0)
            boss.anim = 1.0   # jabs the clipboard
            boss.stats["orders"] = boss.stats.get("orders", 0) + 1
            self.give_xp(boss, XP_PER_ORDER)
            line = random.choice(FOREMAN_BARKS)
            if "{name}" in line:
                line = line.format(name=boss.inspecting.name if boss.inspecting else "everyone")
            px, py = self.entity_screen(boss, 62 + boss.height)
            self.floaters.append(Floater(line, px, py, (255, 255, 255), life=1.8, size=20))

    # ----- specialists ------------------------------------------------------
    def driller_hit(self, cell, driller):
        """One rattle of the jackhammer: a slice of a miner's hit (Diamond Tips still applies)."""
        block = self.current.get(cell)
        if not block:
            return
        dmg = (self.miner_hit_damage() * DRILL_SHARE * self.pick_bonus(driller, cell, 1 / DRILL_HITS_PER_SWING)
               * level_mult(driller.level))
        if is_ore(block):
            dmg *= ore_damage_mult(self.lv("diamond"))
        if random.random() < 0.3:   # dust and chips flying off the bit
            px, py = self.cell_screen(cell)
            chip = random.choice([(160, 140, 120), (200, 190, 170)])
            self.particles.append(Particle(px + random.uniform(-6, 6), py, chip))
        self.damage(cell, dmg, sparks=0, by=driller)

    def stroll(self, m, dt, speed):
        """Nothing to do: amble about near the crew - a few steps somewhere, a breather, then somewhere else - rather
        than stand stock still. (Leaves the helper's own task and goal alone: whatever they do comes first.)"""
        m.stroll_timer = getattr(m, "stroll_timer", 0.0) - dt
        if m.stroll_timer <= 0:
            m.stroll_timer = random.uniform(*STROLL_EVERY)
            crew = [o for o in self.miners if o is not m and o.state == "working"]
            near = random.choice(crew) if crew else m
            m.stroll_to = None if random.random() < STROLL_PAUSE else                 (min(GRID - 0.5, max(0.5, near.x + random.uniform(-1.5, 1.5))),
                 min(GRID - 0.5, max(0.5, near.y + random.uniform(-1.5, 1.5))))
        m.strolling = False
        if getattr(m, "stroll_to", None) is not None:
            was = (m.x, m.y)
            if self.walk_to(m, *m.stroll_to, speed * STROLL_PACE, dt, stop=0.1):
                m.stroll_to = None
            m.strolling = (m.x, m.y) != was

    def walk_to(self, m, gx, gy, speed, dt, stop=0.05):
        """Step towards (gx, gy). Returns True once within `stop` tiles."""
        dx, dy = gx - m.x, gy - m.y
        dist = math.hypot(dx, dy)
        if dist > 0.03:
            m.facing = 1 if (dx - dy) >= 0 else -1
        if dist <= stop + 1e-3:   # (tolerance: stepping exactly to `stop` can leave a float hair short)
            return True
        step = min(dist - stop, speed * dt)
        m.x = min(GRID - 0.05, max(0.05, m.x + dx / dist * step))
        m.y = min(GRID - 0.05, max(0.05, m.y + dy / dist * step))
        return False

    def update_guard(self, guard, dt, speed):
        """Fight the nearest monster - anyone being grabbed first - otherwise patrol around the crew."""
        guard.anim = max(0.0, guard.anim - dt * 4)
        threats = [e for e in self.enemies if e.targetable]
        if threats:
            target = min(threats, key=lambda e: (e.state != "attacking",
                                                 math.hypot(e.x - guard.x, e.y - guard.y)))
            guard.task, guard.goal = "fighting", target
            if self.walk_to(guard, target.x, target.y, speed * GUARD_RUSH, dt, stop=GUARD_REACH):
                guard.swing -= dt
                if guard.swing <= 0:
                    guard.swing = GUARD_SWING
                    self.guard_strike(guard, target)
            return
        guard.task_timer -= dt
        if guard.task != "patrol" or guard.task_timer <= 0 or guard.goal is None:
            crew = [m for m in self.workers() if m is not guard and m.state != "down"]
            near = random.choice(crew) if crew else guard
            guard.task, guard.task_timer = "patrol", random.uniform(4.0, 8.0)
            guard.goal = (min(GRID - 0.5, max(0.5, near.x + random.uniform(-1.5, 1.5))),
                          min(GRID - 0.5, max(0.5, near.y + random.uniform(-1.5, 1.5))))
        self.walk_to(guard, *guard.goal, speed * 0.6, dt)

    # ----- the camp's people (Base Camp hires) ----------------------------------------------------------------
    # ----- achievements ---------------------------------------------------------------------------------------
    def achieve(self, key, quiet=False):
        """Earn an achievement (once): it's announced on the dig, unless `quiet`."""
        if key in self.achievements:
            return
        self.achievements.append(key)
        if not quiet:
            self.achievement_queue.append(key)
            self.cues.append("chest")

    def check_achievements(self, quiet=False):
        for key in CHECKED:
            if key not in self.achievements and ACHIEVEMENTS[key]["check"](self):
                self.achieve(key, quiet)

    def expedition_won(self):
        """The Void Maw has fallen: the achievements that take a whole expedition."""
        r = self.run
        self.achieve("voidmaw")
        if not any(self.levels[u["key"]] for u in UPGRADES if u["branch"] == "fortune"):
            self.achieve("no_fortune")   # (upgrades can't be sold: what's owned now is all that was bought)
        if not r["clean"]:   # (tracked from part-way through: it can't count)
            return
        if r["one_miner"] and r["no_deaths"]:
            self.achieve("president")
        if r["no_block_clicks"] and r["no_monster_clicks"]:
            self.achieve("hands_off")
        if r["no_deaths"]:
            self.achieve("flawless")
        if self.clock - r["start"] < SPEED_DEMON_SECS:
            self.achieve("speed_demon")
        if self.clock - r["start"] < BLINK_SECS:
            self.achieve("blink")

    def take_camp_item(self, key):
        """Take one of the camp's items (instead of a new hire, this visit): yours from now on, for good."""
        if key not in self.camp_items:
            self.camp_items.append(key)
        self.visit_hire = key

    def hire_at_camp(self, hire):
        """Take someone on at Base Camp: they're with you from this moment (saved straight away by the camp),
        whatever happens before you set off."""
        if hire not in self.camp:
            self.camp.append(hire)
        self.visit_hire = hire
        self.sync_miners()

    def under_banner(self, m):
        """Is this crew member within reach of Rocco's banner (further with the Gold Fringe)?"""
        if not self.banner:
            return False
        reach = FRINGE_RADIUS if "fringe" in self.camp_items else BANNER_RADIUS
        return math.hypot(m.x - self.banner[0], m.y - self.banner[1]) <= reach

    def heirloom_split(self, cell, dmg, hero):
        """The Heirloom Pickaxe: Rocco's blow splits the rock - the blocks in line beyond the one he hit, the way he's
        facing (whichever way there's more rock), take it too. False if the layer changed (stop chaining)."""
        ways = [(1, 0), (0, -1)] if hero.facing >= 0 else [(-1, 0), (0, 1)]
        def line(step):
            return [(cell[0] + step[0] * k, cell[1] + step[1] * k) for k in range(1, HEIRLOOM_DEEP + 1)]
        step = max(ways, key=lambda w: sum(c in self.current for c in line(w)))
        depth = self.depth
        px, py = self.cell_screen(cell)
        self.cues.append(("smash", 0.25))
        self.floaters.append(Floater("SPLIT!", px, py - 40, GOLD, life=0.9, size=22))
        for c in line(step):
            if c in self.current:
                cx, cy = self.cell_screen(c)
                for _ in range(6):   # a gold crack running through the rock
                    self.particles.append(Particle(cx, cy, random.choice([GOLD, (255, 240, 170)])))
                self.damage(c, dmg, sparks=4, by=hero)
                if self.depth != depth:
                    return False
        return True

    def plant_banner(self):
        """The Banner of the Deep: Rocco plants it beside the block he's digging, and moves it on once he's digging
        well away from it. Returns where it stands (None without it)."""
        if "banner" not in self.camp_items:
            self.banner = None
            return None
        hero = next((m for m in self.miners if m.role == "hero" and m.state == "working"), None)
        if hero and hero.target and hero.task != "rescuing":
            tx, ty = hero.target[0] + 0.5, hero.target[1] + 0.5
            there = math.hypot(tx - hero.x, ty - hero.y) < 0.6   # (once he's got to it)
            if there and (self.banner is None or math.hypot(tx - self.banner[0], ty - self.banner[1]) > BANNER_REPLANT):
                self.banner = [hero.x, hero.y]
                px, py = self.entity_screen(hero, 30)
                for _ in range(8):   # (a puff of dust as it goes in)
                    self.particles.append(Particle(px, py, random.choice([(150, 130, 110), (90, 170, 240)])))
        return self.banner

    def update_hero(self, hero, dt, speed):
        """The Hero Miner drops their pick to rescue anyone close by a monster has hold of. True while on a rescue."""
        grabbing = [e for e in self.enemies if e.targetable and e.state == "attacking" and not e.boss
                    and math.hypot(e.x - hero.x, e.y - hero.y) <= HERO_RESCUE_RANGE + self.art_add("hero_reach")]
        if not grabbing:
            if hero.task == "rescuing":
                hero.task, hero.target, hero.goal = "idle", None, None
            return False
        foe = min(grabbing, key=lambda e: math.hypot(e.x - hero.x, e.y - hero.y))
        hero.task, hero.goal = "rescuing", foe
        hero.anim = max(0.0, hero.anim - dt * 4)
        if self.walk_to(hero, foe.x, foe.y, speed * GUARD_RUSH, dt, stop=GUARD_REACH):
            hero.swing -= dt
            if hero.swing <= 0:
                hero.swing = HERO_SWING
                hero.anim = 1.0
                share = HERO_STRIKE * level_mult(hero.level) * self.art_mult("hero")
                self.give_xp(hero, share * XP_PER_MONSTER * GUARD_XP_SHARE)
                self.hit_enemy(foe, foe.max_hp * share * foe.pct_scale, floor=False, ring=GOLD, by=hero, heavy=True)
        return True

    def update_engineer(self, smith, dt, speed):
        if "rod" in self.camp_items:   # (the camp's Lightning Rod: one planted now and then)
            smith.rod_timer = getattr(smith, "rod_timer", ROD_EVERY * 0.4) - dt
            if smith.rod_timer <= 0 and not self.rods:
                smith.rod_timer = ROD_EVERY / self.tick()
                self.plant_rod(smith)
        self.rig_picks(smith, dt, speed)

    def rig_picks(self, smith, dt, speed):
        """The Goblin Engineer: trots to whichever digger's pick has gone longest unrigged, and rigs it on
        the spot - a couple of seconds of hammering, then every blow it lands explodes for FORGE_SECS."""
        if smith.task == "forging" and smith.goal in self.miners and smith.goal.state == "working":
            smith.task_timer -= dt
            smith.anim = 1.0 if (self.clock * 5) % 1 < 0.5 else 0.2   # (hammering away)
            if random.random() < dt * 12:   # sparks off the anvil
                px, py = self.entity_screen(smith, 12)
                self.particles.append(Particle(px + 8 * smith.facing, py, random.choice([(255, 200, 90), (255, 140, 50)])))
            if smith.task_timer <= 0:
                m = smith.goal
                m.forged, m.blast = FORGE_SECS * self.art_mult("rig"), FORGE_BLAST * level_mult(smith.level) * self.art_mult("rig")
                px, py = self.entity_screen(m, 56)
                self.floaters.append(Floater("Explosive pick!", px, py, (255, 170, 80), life=1.1, size=20))
                self.give_xp(smith, XP_PER_BLOCK * 0.5)
                smith.task, smith.goal, smith.anim = "idle", None, 0.0
            return
        pool = [m for m in self.diggers() if m.state == "working"]
        if not pool:   # (nobody's pick to reforge: he potters about)
            self.stroll(smith, dt, speed)
            return
        if smith.task != "heading" or smith.goal not in pool:
            smith.goal = min(pool, key=lambda m: (getattr(m, "forged", 0.0), math.hypot(m.x - smith.x, m.y - smith.y)))
            smith.task = "heading"
        m = smith.goal
        if self.walk_to(smith, m.x + 0.35, m.y + 0.35, speed, dt, stop=0.15):
            smith.task, smith.task_timer = "forging", FORGE_WORK
            smith.facing = 1 if (m.x - smith.x) - (m.y - smith.y) >= 0 else -1

    def update_clay_golem(self, golem, dt, speed):
        """Mitts the Clay Golem works off your clicks: every MITTS_CLICKS of them, he leaps to where you last
        clicked, fists up, and comes down in a full Charged Slam of his own - upgrade or no upgrade. With no clicks
        from you for MITTS_IDLE seconds, he goes anyway, to wherever the blocks are thickest."""
        if golem.task == "leaping":
            golem.task_timer -= dt
            q = min(1.0, 1 - golem.task_timer / MITTS_LEAP)
            (x0, y0), (x1, y1) = golem.leap_from, (golem.goal[0] + 0.5, golem.goal[1] + 0.5)
            golem.x, golem.y = x0 + (x1 - x0) * q, y0 + (y1 - y0) * q
            golem.hop, golem.anim = math.sin(q * math.pi), min(1.0, q * 2)   # (up and over, fists going up)
            if golem.task_timer <= 0:
                self.golem_slam(golem, golem.goal)
                golem.task, golem.goal, golem.anim, golem.hop = "idle", None, 0.0, 0.0
            return
        golem.anim, golem.hop = 0.0, 0.0
        golem.fired = "kiln" in self.camp_items   # (how he looks)
        golem.glazed = "glaze" in self.camp_items
        golem.clicks = getattr(golem, "clicks", 0)   # (so his click meter shows from the start)
        golem.idle = getattr(golem, "idle", 0.0) + dt
        if golem.clicks >= MITTS_CLICKS and getattr(golem, "leap_to", None) is not None:
            golem.clicks, golem.goal, golem.leap_to = 0, golem.leap_to, None
        elif golem.idle >= MITTS_IDLE / self.tick() and self.current:   # no clicks from you for a while: off he goes anyway
            golem.goal = self.phantom_target()
        else:   # (waiting on your clicks: a plod about meanwhile)
            self.stroll(golem, dt, speed)
            return
        if golem.goal is not None:
            self.golem_leap(golem, golem.goal)

    def golem_leap(self, golem, cell):
        """Mitts launches himself at `cell`, to come down on it in a slam (update_clay_golem flies him there)."""
        golem.goal, golem.idle = cell, 0.0
        golem.task, golem.task_timer, golem.leap_from = "leaping", MITTS_LEAP, (golem.x, golem.y)
        dx, dy = cell[0] + 0.5 - golem.x, cell[1] + 0.5 - golem.y
        golem.facing = 1 if dx - dy >= 0 else -1
        self.cues.append(("hit", 0.3))

    def mitts_follow(self, cell):
        """A good Charged Slam of yours: Mitts comes leaping in after it, to the same spot (if he's free to)."""
        for golem in self.miners:
            if golem.role == "claygolem" and golem.state == "working" and golem.task != "leaping":
                self.golem_leap(golem, cell)

    def break_grip(self, enemy):
        """A monster loses its hold: whoever it had is free again (both sides of the grip let go)."""
        v = enemy.victim
        if v is not None and v.attacker is enemy:
            v.state, v.attacker = "working", None
        enemy.release()

    def plant_rod(self, smith):
        """Grizzle hammers a Lightning Rod into the rock beside him."""
        x = min(GRID - 0.4, max(0.4, smith.x + 0.4 * smith.facing))
        y = min(GRID - 0.4, max(0.4, smith.y + 0.2))
        self.rods.append(LightningRod(x, y))
        px, py = self.entity_screen(smith, 40)
        self.floaters.append(Floater("Stand back!", px, py - 10, (170, 220, 255), life=1.2, size=22))

    def update_rods(self, dt):
        """Lightning Rods: every ROD_ARC seconds an arc jumps to a block or monster within ROD_RANGE (monsters half the
        time, when there are any) - until the rod burns out."""
        for rod in self.rods:
            rod.left -= dt
            rod.arc -= dt
            if rod.arc > 0:
                continue
            rod.arc = ROD_ARC
            near = lambda x, y: math.hypot(x - rod.x, y - rod.y) <= ROD_RANGE
            foes = [e for e in self.enemies if e.targetable and near(e.x, e.y)]
            cells = [c for c in self.current if near(c[0] + 0.5, c[1] + 0.5)]
            if foes and (not cells or random.random() < 0.5):
                e = random.choice(foes)
                self.arcs.append([rod, (e.x, e.y), 0.0])
                self.hit_enemy(e, e.max_hp * ROD_MONSTER * e.pct_scale, floor=False, ring=(170, 220, 255))
            elif cells:
                c = random.choice(cells)
                self.arcs.append([rod, (c[0] + 0.5, c[1] + 0.5), 0.0])
                if not self.damage(c, self.current[c].max_hp * ROD_BLOCK, sparks=4):
                    break
            self.cues.append(("hit", 0.25))
        for rod in [r for r in self.rods if r.left <= 0]:   # burnt out: a last fizzle
            px, py = iso(rod.x, rod.y, self.column_height(*self.cell_of(rod.x, rod.y)) + self.rise)
            for _ in range(8):
                self.particles.append(Particle(px, py - 30, random.choice([(170, 220, 255), (255, 255, 255)])))
        self.rods = [r for r in self.rods if r.left > 0]
        for arc in self.arcs:
            arc[2] += dt
        self.arcs = [a for a in self.arcs if a[2] < ARC_SECS and a[0] in self.rods]

    def kiln_shove(self, cell):
        """Kiln: a fired golem lands hard - ordinary monsters close by are shoved back, losing any grip they had."""
        cx, cy = cell[0] + 0.5, cell[1] + 0.5
        for e in self.enemies:
            dx, dy = e.x - cx, e.y - cy
            dist = math.hypot(dx, dy)
            if e.boss or not e.targetable or dist > KILN_RADIUS:
                continue
            if e.state == "attacking":
                self.break_grip(e)
            ux, uy = (dx / dist, dy / dist) if dist > 0.05 else (1.0, 0.0)
            e.x = min(GRID - 0.1, max(0.1, e.x + ux * KILN_SHOVE))
            e.y = min(GRID - 0.1, max(0.1, e.y + uy * KILN_SHOVE))

    def update_mudlings(self, dt):
        """Clay Pit mudlings: waddle to the nearest block and dig at it, until they crumble back into mud."""
        hit = self.miner_hit_damage() * MUDLING_POWER
        for mud in self.mudlings:
            mud.left -= dt
            mud.anim = max(0.0, mud.anim - dt * 4)
            if mud.target not in self.current:
                mud.target = min(self.current, key=lambda c: math.hypot(c[0] + 0.5 - mud.x, c[1] + 0.5 - mud.y)) \
                    if self.current else None
            if mud.target is None:
                continue
            if self.walk_to(mud, mud.target[0] + 0.5, mud.target[1] + 0.5, MUDLING_SPEED, dt, stop=0.55):
                mud.swing -= dt
                if mud.swing <= 0:
                    mud.swing, mud.anim = MUDLING_SWING, 1.0
                    if not self.damage(mud.target, hit, sparks=2):
                        break   # (the layer changed: they'll find new blocks next time)
        for mud in [m for m in self.mudlings if m.left <= 0]:   # crumbling back into mud
            px, py = iso(mud.x, mud.y, self.column_height(*self.cell_of(mud.x, mud.y)) + self.rise)
            for _ in range(10):
                self.particles.append(Particle(px, py - 6, random.choice([(186, 116, 74), (132, 80, 50)])))
        self.mudlings = [m for m in self.mudlings if m.left > 0]

    def golem_slam(self, golem, cell):
        """Mitts' fists come down: the block under them is levelled and the eight round it lose MITTS_CRACK of
        their health - or, if it's more, a full Charged Slam's worth of your click damage (half for the eight) -
        and monsters close by are walloped. (Where he lands, the block may be gone by now: the ones round it still
        take the blow.)"""
        if "kiln" in self.camp_items:
            self.kiln_shove(cell)
        wheel = "wheel" in self.camp_items   # (the Potter's Wheel: proper clay soldiers)
        if "claypit" in self.camp_items and len(self.mudlings) < (WHEEL_MAX if wheel else MUDLING_MAX):
            self.mudlings.append(Mudling(cell[0] + 0.5 + random.uniform(-0.3, 0.3), cell[1] + 0.5 + random.uniform(-0.3, 0.3),
                                         MUDLING_SECS * (WHEEL_LIFE if wheel else 1.0)))
        if "glaze" in self.camp_items:   # Glazed Fists: the nine blocks round where he lands
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    self.glazed[(cell[0] + dx, cell[1] + dy)] = (self.depth, self.clock + GLAZE_SECS)
        power = slam_mult(self.lv("slam")) * level_mult(golem.level) * self.art_mult("mitts")
        dmg = self.click_hit_damage() * power
        for e in list(self.enemies):
            if e.targetable and not e.boss and max(abs(e.x - (cell[0] + 0.5)), abs(e.y - (cell[1] + 0.5))) <= 1.5:
                self.hit_enemy(e, self.enemy_hit_damage(e, self.monster_hit_damage()) * SLAM_MONSTER_MULT, floor=False,
                               ring=(200, 130, 90), by=golem, heavy=True)
        px, py = self.cell_screen(cell)
        self.crit_bursts.append([px, py, 0.0])
        self.quakes.append([cell[0] + 0.5, cell[1] + 0.5, 0.0, set(), 1.6])
        if self.shake < 0.12:
            self.shake, self.shake_power = 0.12, 3
        self.cues.append(("smash", 0.5))
        self.floaters.append(Floater("THUD!", px, py - 60, (215, 150, 105), life=0.8, size=26))
        self.give_xp(golem, XP_PER_BLOCK)
        depth, crack = self.depth, crack_share(self.depth)
        block = self.current.get(cell)
        if block:
            level = block.hp + 1e-9 if depth <= DEEP_ROCK_FROM else block.max_hp * crack
            if not self.damage(cell, max(dmg, level), sparks=10, by=golem):
                return
        share = MITTS_CRACK * level_mult(golem.level) * crack * self.art_mult("mitts")
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                around = self.current.get((cell[0] + dx, cell[1] + dy))
                if (dx, dy) != (0, 0) and around and self.depth == depth:
                    self.damage((cell[0] + dx, cell[1] + dy), max(dmg * 0.5, around.max_hp * share), sparks=2,
                                by=golem)

    def update_archer(self, archer, dt, speed):
        """The Archer: shoots whatever's grabbing someone first, then the nearest monster, from a distance;
        with no monsters about, keeps close to the crew. (With the camp's Target Dummy, she plants one now and
        then.)"""
        if "dummy" in self.camp_items:
            archer.dummy_timer = getattr(archer, "dummy_timer", DUMMY_EVERY * 0.5) - dt
            if archer.dummy_timer <= 0 and not self.dummies:
                archer.dummy_timer = DUMMY_EVERY / self.tick()
                self.plant_dummy(archer)
        targets = [e for e in self.enemies if e.targetable]
        if targets:
            foe = min(targets, key=lambda e: (e.state != "attacking", math.hypot(e.x - archer.x, e.y - archer.y)))
            archer.task, archer.goal = "shooting", foe
            if math.hypot(foe.x - archer.x, foe.y - archer.y) > ARCHER_RANGE:
                self.walk_to(archer, foe.x, foe.y, speed, dt)
                return
            archer.facing = 1 if (foe.x - archer.x) - (foe.y - archer.y) >= 0 else -1
            archer.swing -= dt
            archer.anim = min(1.0, 1 - archer.swing / (ARCHER_DRAW * self.art_mult("draw") / self.tick()))   # (drawing the bow back)
            if archer.swing <= 0:
                archer.swing, archer.anim = ARCHER_DRAW * self.art_mult("draw") / self.tick(), 0.0
                self.arrows.append([self.entity_screen(archer, 24), foe, 0.0, archer])
            return
        archer.anim = 0.0
        archer.task_timer -= dt
        if archer.task != "watching" or archer.task_timer <= 0 or not isinstance(archer.goal, tuple):
            crew = [m for m in self.diggers() if m.state != "down"]
            near = random.choice(crew) if crew else archer
            archer.task, archer.task_timer = "watching", random.uniform(5.0, 9.0)
            archer.goal = (min(GRID - 0.5, max(0.5, near.x + random.uniform(-2, 2))),
                           min(GRID - 0.5, max(0.5, near.y + random.uniform(-2, 2))))
        self.walk_to(archer, *archer.goal, speed * 0.6, dt)

    def fire_arrow(self, archer):
        """Fire Arrows: is this one of the lit ones (every FIRE_EVERY-th)?"""
        archer.arrows_loosed = getattr(archer, "arrows_loosed", 0) + 1
        return archer.arrows_loosed % FIRE_EVERY == 0

    def fire_burst(self, foe, dmg, archer):
        """A fire arrow bursts where it lands: the monsters round its target catch some of it too."""
        px, py = enemy_anchor(foe, self.rise, time.time())
        for _ in range(12):
            self.particles.append(Particle(px, py, random.choice([(255, 200, 80), (255, 120, 40), (200, 60, 30)])))
        self.rings.append([px, py, 0.0, 50, (255, 140, 50)])
        for e in list(self.enemies):
            if e is not foe and e.targetable and math.hypot(e.x - foe.x, e.y - foe.y) <= FIRE_RADIUS:
                self.hit_enemy(e, dmg * FIRE_SPLASH, floor=False, ring=(255, 140, 50), by=archer)

    def blast_arrow(self, foe, dmg, archer):
        """Explosive Arrows: a fire arrow blows up where it lands - every monster round its target takes the full hit
        (a blast heavy enough to crack armour), and the 3x3 of blocks round it is blasted too."""
        px, py = enemy_anchor(foe, self.rise, time.time())
        self.explosions.append([px, py - 6, 0.0, 44])
        self.cues.append(("boom", 0.3))
        for _ in range(14):
            self.particles.append(Particle(px, py, random.choice([(255, 200, 80), (255, 120, 40), (90, 80, 80)]),
                                           big=True))
        for e in list(self.enemies):
            if e is not foe and e.targetable and math.hypot(e.x - foe.x, e.y - foe.y) <= BLAST_ARROW_RADIUS:
                self.hit_enemy(e, dmg, floor=False, ring=(255, 140, 50), by=archer, heavy=True)
        cx, cy = self.cell_of(foe.x, foe.y)
        rock = self.click_hit_damage() * BLAST_ARROW_BLOCKS * level_mult(archer.level)
        depth = self.depth
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (cx + dx, cy + dy) in self.current and self.depth == depth:
                    self.damage((cx + dx, cy + dy), rock, sparks=3)

    def plant_dummy(self, archer):
        """Wren drives a Target Dummy into the ground beside her."""
        x = min(GRID - 0.4, max(0.4, archer.x + 0.45 * archer.facing))
        y = min(GRID - 0.4, max(0.4, archer.y - 0.2))
        self.dummies.append(TargetDummy(x, y))
        px, py = self.entity_screen(archer, 40)
        self.floaters.append(Floater("Dummy up!", px, py - 10, (230, 200, 140), life=1.2, size=22))
        for _ in range(10):
            self.particles.append(Particle(px, py + 30, random.choice([(200, 170, 110), (150, 120, 80)])))

    def lure(self, enemy):
        """Target Dummy: the dummy a monster goes for instead of the crew (if one's close enough), or None.
        Bosses, Shades and Burrowers pay it no mind."""
        if not self.dummies or enemy.boss or enemy.spec.get("aura") or enemy.spec.get("burrow"):
            return None
        d = min(self.dummies, key=lambda d: math.hypot(d.x - enemy.x, d.y - enemy.y))
        return d if math.hypot(d.x - enemy.x, d.y - enemy.y) <= DUMMY_LURE else None

    def dummy_grabbed(self, dummy, enemy):
        """A monster gets its hands on a Target Dummy - and it goes off: the monsters round it lose a share of
        their health, and the blocks beneath are blasted (the deep doesn't shrug this one off)."""
        if dummy not in self.dummies:
            return
        self.dummies.remove(dummy)
        archer = next((m for m in self.miners if m.role == "archer"), None)
        power = DUMMY_BLAST * (level_mult(archer.level) if archer else 1.0)
        px, py = iso(dummy.x, dummy.y, self.column_height(*self.cell_of(dummy.x, dummy.y)) + self.rise)
        self.explosions.append([px, py - 20, 0.0, 70])
        self.cues.append(("boom", 0.6))
        self.shake, self.shake_power = max(self.shake, 0.25), 5
        self.floaters.append(Floater("BOOM!", px, py - 70, (255, 170, 80), life=1.0, size=32))
        for e in list(self.enemies):
            if e.targetable and math.hypot(e.x - dummy.x, e.y - dummy.y) <= DUMMY_RADIUS:
                self.hit_enemy(e, e.max_hp * power * e.pct_scale, floor=False, ring=(255, 150, 60), by=archer,
                               heavy=True)
        cx, cy = self.cell_of(dummy.x, dummy.y)
        depth = self.depth
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                block = self.current.get((cx + dx, cy + dy))
                if block and self.depth == depth:
                    self.damage((cx + dx, cy + dy), block.max_hp * (0.5 if (dx or dy) else 1.0) * 0.5, sparks=4)

    def update_arrows(self, dt):
        """Arrows in flight: each lands on its target like one of your clicks (times the archer's level bonus)."""
        for arrow in self.arrows:
            arrow[2] += dt
            _, foe, age, archer = arrow
            if age >= ARROW_SECS and foe in self.enemies and foe.targetable:
                dmg = self.enemy_hit_damage(foe, self.monster_hit_damage()) * level_mult(archer.level)
                self.give_xp(archer, min(1.0, dmg / foe.max_hp) * XP_PER_MONSTER * GUARD_XP_SHARE)
                fire = "brazier" in self.camp_items and self.fire_arrow(archer)
                self.hit_enemy(foe, dmg, floor=False, ring=(255, 140, 50) if fire else (180, 220, 140), by=archer)
                if fire and "explosive" in self.camp_items:
                    self.blast_arrow(foe, dmg, archer)
                elif fire:
                    self.fire_burst(foe, dmg, archer)
        self.arrows = [a for a in self.arrows if a[2] < ARROW_SECS]

    def update_taxman(self, tax, dt, speed):
        """The Tax Collector does his rounds: he walks up to each crew member in turn (the nearest one he hasn't
        been to yet this round), stops to collect their dues and write them in the ledger, and moves on. When
        everyone's paid, a new round starts."""
        if tax.task == "collecting":
            tax.task_timer -= dt
            tax.anim = 1.0 if tax.task_timer > TAX_PAUSE * 0.35 else 0.0   # (writing it in the ledger)
            if tax.task_timer <= 0:
                tax.task, tax.anim = "idle", 0.0
            return
        tax.anim = 0.0
        if "taxes" in self.camp_items and self.tax_monsters(tax, dt, speed):   # (Death and Taxes: them first)
            return
        crew = [m for m in self.miners if m is not tax and m.state == "working"]
        if not crew:
            self.stroll(tax, dt, speed)
            return
        if tax.task != "visiting" or tax.goal not in crew:   # on to the next one on the round
            last = getattr(tax, "last_payer", None)   # (never the same one twice running)
            due = [m for m in crew if m not in tax.route and m is not last]
            if not due:   # everyone's paid up: a fresh round (starting with whoever's nearest)
                tax.route = set()
                due = [m for m in crew if m is not last]
            if not due:   # (nobody else free to pay: he waits rather than tax the same one twice running)
                tax.task = "waiting"
                self.stroll(tax, dt, speed)
                return
            tax.task = "visiting"
            tax.goal = min(due, key=lambda m: math.hypot(m.x - tax.x, m.y - tax.y))
        payer = tax.goal
        if self.walk_to(tax, payer.x + 0.3, payer.y - 0.3, speed, dt, stop=0.15):
            tax.facing = 1 if (payer.x - tax.x) - (payer.y - tax.y) >= 0 else -1
            tax.route.add(payer)
            tax.last_payer = payer
            self.collect_tax(tax, payer)
            tax.task, tax.task_timer = "collecting", TAX_PAUSE

    def tax_monsters(self, tax, dt, speed):
        """Death and Taxes: Mr. Pennyworth calls on any monster close by that hasn't paid yet - it hands over a share
        of its bounty, and loses a share of its health in sheer indignation. True while he's about it."""
        mark = getattr(tax, "mark", None)
        if mark not in self.enemies or not mark.targetable:
            due = [e for e in self.enemies if e.targetable and not e.boss and not getattr(e, "taxed", False)
                   and math.hypot(e.x - tax.x, e.y - tax.y) <= TAXES_REACH]
            mark = tax.mark = min(due, key=lambda e: math.hypot(e.x - tax.x, e.y - tax.y)) if due else None
        if mark is None:
            if tax.task == "auditing":
                tax.task = "idle"
            return False
        tax.task = "auditing"
        if self.walk_to(tax, mark.x + 0.3, mark.y - 0.3, speed, dt, stop=0.3):
            tax.facing = 1 if (mark.x - tax.x) - (mark.y - tax.y) >= 0 else -1
            mark.taxed, tax.mark = True, None
            paid = self.earn(self.bounty_worth(mark) * TAXES_SHARE)
            px, py = enemy_anchor(mark, self.rise, time.time())
            tx, ty = self.entity_screen(tax, 50)
            for k in range(6):   # its coins hopping over to his ledger
                q = k / 5
                self.particles.append(Particle(px + (tx - px) * q, py + (ty - py) * q - math.sin(q * math.pi) * 14,
                                               GOLD))
            self.floaters.append(Floater(f"Taxed! +{fmt(paid)}", tx, ty - 10, GOLD, life=1.3, size=22, coin=True))
            self.hit_enemy(mark, mark.max_hp * TAXES_HURT * mark.pct_scale, floor=False, ring=GOLD)
            self.give_xp(tax, XP_PER_BLOCK * 0.5)
            tax.task, tax.task_timer = "collecting", TAX_PAUSE
        return True

    def tax_due(self, tax):
        """What one crew member pays the Tax Collector: a few of this layer's average blocks, at what blocks pay
        right now (Fortune upgrades and all), a few more the deeper the dig - so the take keeps step with the depth
        (about a fifth on top of the crew's earnings all the way down), whatever's been broken lately."""
        block = self.layer_value / (GRID * GRID) * value_mult(self.lv("value"))
        return block * (TAX_BLOCKS + self.depth / TAX_DEEPER) * level_mult(tax.level) * self.art_mult("tax")

    def collect_tax(self, tax, payer):
        paid = self.earn(self.tax_due(tax))   # (Midas Touch and the depth bonus count, as for any gold)
        px, py = self.entity_screen(payer, 40)
        tx, ty = self.entity_screen(tax, 50)
        for k in range(6):   # coins hopping from their pocket to his ledger
            q = k / 5
            self.particles.append(Particle(px + (tx - px) * q, py + (ty - py) * q - math.sin(q * math.pi) * 14, GOLD))
        self.floaters.append(Floater(f"Tax +{fmt(paid)}", tx, ty - 10, GOLD, life=1.2, size=22, coin=True))
        self.give_xp(tax, XP_PER_BLOCK * 0.5)

    def coffee_break(self):
        """Coffee Break: a round of coffee - a few diggers at work down a mug and swing faster for a while."""
        thirsty = [m for m in self.diggers() if m.state == "working" and m.coffee <= 0 and m.stun <= 0]
        for m in random.sample(thirsty, min(len(thirsty), coffee_cups(self.lv("coffee")))):
            m.coffee = COFFEE_SECS
            px, py = self.entity_screen(m, 56)
            self.floaters.append(Floater("Coffee!", px, py, (230, 190, 130), life=1.2, size=22))

    def update_medic(self, medic, dt, speed):
        """Run to whoever is hurt - anyone in a monster's grip first, then the worst off - and patch them up;
        with no one to treat, keep close to the crew."""
        medic.anim = max(0.0, medic.anim - dt * 3)
        hurt = [m for m in self.miners if m is not medic and m.state != "down" and m.hp < m.max_hp]
        if hurt:
            patient = min(hurt, key=lambda m: (m.state != "grabbed", m.hp / m.max_hp))
            medic.task, medic.goal = "healing", patient
            grabbed = patient.state == "grabbed"
            if self.walk_to(medic, patient.x, patient.y, speed * (MEDIC_RUSH if grabbed else 1), dt,
                            stop=MEDIC_REACH):
                rate = medic_heal(self.lv("medic")) * (1 + (level_mult(medic.level) - 1) * MEDIC_XP_SHARE)
                healed = min(patient.max_hp - patient.hp,
                             rate * (MEDIC_GRABBED if grabbed else 1) * patient.max_hp * dt)
                patient.hp += healed
                medic.anim = 1.0
                self.give_xp(medic, healed / patient.max_hp * XP_PER_HEAL)
                if random.random() < dt * 6:   # little green crosses rising off the patient
                    px, py = self.entity_screen(patient, 34)
                    self.particles.append(Particle(px + random.uniform(-8, 8), py, (120, 230, 140)))
            return
        medic.task_timer -= dt
        if medic.task != "on call" or medic.task_timer <= 0 or not isinstance(medic.goal, tuple):
            crew = [m for m in self.workers() if m is not medic and m.state != "down"]
            near = random.choice(crew) if crew else medic
            medic.task, medic.task_timer = "on call", random.uniform(4.0, 8.0)
            medic.goal = (min(GRID - 0.5, max(0.5, near.x + random.uniform(-1.2, 1.2))),
                          min(GRID - 0.5, max(0.5, near.y + random.uniform(-1.2, 1.2))))
        self.walk_to(medic, *medic.goal, speed * 0.6, dt)

    def guard_strike(self, guard, enemy):
        if not enemy or enemy not in self.enemies or not enemy.targetable:
            return
        guard.anim = 1.0
        enemy.guard_hit = (guard, self.clock)   # (for the kill credit)
        self.give_xp(guard, GUARD_SHARE * XP_PER_MONSTER)
        share = GUARD_SHARE * (1 + (level_mult(guard.level) - 1) * GUARD_XP_SHARE)
        self.hit_enemy(enemy, enemy.max_hp * share * enemy.pct_scale, floor=False, ring=(120, 150, 220), by=guard)

    def charge_target(self, demo):
        """The block whose blast would take out the most: blocks (ore counting extra) in the 3x3 around it,
        not already claimed by another charge, with a little preference for somewhere close by."""
        lit = {b.cell for b in self.bombs}
        def score(c):
            around = [self.current.get((c[0] + dx, c[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            worth = sum(1.5 if is_ore(b) else 1.0 for b in around if b)
            return worth - 0.15 * math.hypot(c[0] + 0.5 - demo.x, c[1] + 0.5 - demo.y) - 5 * (c in lit)
        return max(self.current, key=score)

    def update_demolitionist(self, demo, dt, speed):
        """Every so often: pick where the blocks are thickest, walk over, plant a charge, run for cover."""
        demo.anim = max(0.0, demo.anim - dt * 2)
        if demo.task == "idle":
            demo.task_timer -= dt
            if demo.task_timer <= 0 and self.current:
                demo.task, demo.charge_cell = "walking", self.charge_target(demo)
            elif isinstance(demo.goal, tuple):
                self.walk_to(demo, *demo.goal, speed * 0.5, dt)
        elif demo.task == "walking":
            if demo.charge_cell not in self.current:   # broken by someone else first
                demo.task, demo.task_timer = "idle", 1.0
            elif self.walk_to(demo, demo.charge_cell[0] + 0.5, demo.charge_cell[1] + 0.5, speed, dt):
                demo.task, demo.task_timer = "planting", 0.9
        elif demo.task == "planting":   # kneeling over the charge
            demo.task_timer -= dt
            demo.anim = 1.0
            if demo.task_timer <= 0:
                self.bombs.append(Bomb(demo.charge_cell, 1, owner=demo))
                px, py = self.cell_screen(demo.charge_cell)
                self.floaters.append(Floater("Fire in the hole!", px, py - 60, (255, 170, 80), life=1.4, size=22))
                away = random.uniform(0, math.tau)   # run for cover
                demo.goal = (min(GRID - 0.5, max(0.5, demo.x + math.cos(away) * 2.5)),
                             min(GRID - 0.5, max(0.5, demo.y + math.sin(away) * 2.5)))
                demo.task = "taking cover"
                demo.task_timer = demo_interval(self.lv("demolition")) / level_mult(demo.level) / self.tick()
        elif demo.task == "taking cover":   # (the wait for the next charge starts as soon as this one is set)
            demo.task_timer -= dt
            if self.walk_to(demo, *demo.goal, speed * 1.3, dt):
                demo.task, demo.goal = "idle", None

    # ----- middle-path upgrade systems -----------------------------------------
    def ward(self, enemy):
        """Spirit Lantern: ghosts can't phase out."""
        enemy.warded = self.lv("spiritlantern") > 0
        enemy.speed_mult = self.art_mult("enemy_speed")

    def update_skirmish(self, m, boss, dt, speed):
        """A digger with no blocks left while a boss holds the layer: dart from spot to spot, keeping clear
        of its slams, and every couple of seconds stop to throw a rock at it."""
        m.anim = max(0.0, m.anim - dt * 4)
        if m.task != "skirmish":   # (a fresh spot to make for: whatever they were after before, it isn't one)
            m.task, m.task_timer, m.goal = "skirmish", random.uniform(*ROCK_EVERY), None
        from_boss = lambda x, y: math.hypot(x - boss.x, y - boss.y)
        spots = lambda: [(random.uniform(0.5, GRID - 0.5), random.uniform(0.5, GRID - 0.5)) for _ in range(12)]
        if m.goal is None or from_boss(*m.goal) < SKIRMISH_KEEP_AWAY:   # somewhere new, clear of the boss
            options = spots()
            safe = [s for s in options if from_boss(*s) >= SKIRMISH_KEEP_AWAY]
            m.goal = random.choice(safe) if safe else max(options, key=lambda s: from_boss(*s))
        elif from_boss(m.x, m.y) < SKIRMISH_KEEP_AWAY and from_boss(*m.goal) < from_boss(m.x, m.y) + 1:
            m.goal = max(spots(), key=lambda s: from_boss(*s))   # the boss is coming at them: run for it
        if self.walk_to(m, *m.goal, speed * 1.2, dt):   # a brisk trot
            m.goal = None
        m.task_timer -= dt
        if m.task_timer <= 0:
            m.task_timer = random.uniform(*ROCK_EVERY)
            if boss.targetable and math.hypot(m.x - boss.x, m.y - boss.y) <= ROCK_RANGE:
                m.anim = 1.0
                m.facing = 1 if (boss.x - m.x) - (boss.y - m.y) >= 0 else -1
                self.rocks.append([m, self.entity_screen(m, 34), boss, 0.0])
                self.give_xp(m, XP_PER_ROCK)

    def update_chompers(self, dt):
        """Chompers (and, with the Mimic Pup, its little one) on the dig."""
        if self.chomper is None:
            self.chomper = dict(x=0.5, y=0.5, timer=CHOMP_EVERY * 0.5, hop=None, chomp_at=-1e9, lift=0.0)
        self.update_mimic(self.chomper, dt, CHOMP_EVERY, CHOMP_PAYOUT)
        if "pup" not in self.camp_items:
            self.pup = None
            return
        if self.pup is None:
            self.pup = dict(x=self.chomper["x"], y=self.chomper["y"], timer=PUP_EVERY * 0.5, hop=None, chomp_at=-1e9,
                            lift=0.0)
        self.update_mimic(self.pup, dt, PUP_EVERY, PUP_PAYOUT, follow=self.chomper)

    def update_mimic(self, c, dt, every, payout, follow=None):
        """A camp Mimic waits a while, then hops over to the richest block in the layer and gobbles it whole. With
        the Spiked Collar, Chompers also bounds over to bite any monster that grabs someone. `follow`: the Mimic
        this one trots after (the pup, its parent)."""
        if c["hop"]:
            start, goal, age, job = c["hop"]
            age += dt
            q = min(1.0, age / CHOMP_HOP)
            c["x"] = start[0] + (goal[0] - start[0]) * q
            c["y"] = start[1] + (goal[1] - start[1]) * q
            c["lift"], c["hop"] = math.sin(q * math.pi), [start, goal, age, job]
            if q >= 1:
                c["hop"], c["lift"] = None, 0.0
                if job[0] == "bite":
                    self.collar_bite(c, job[1])
                else:
                    self.chomp(c, job[1], payout)
            return
        c["timer"] -= dt
        c["bite_cd"] = max(0.0, c.get("bite_cd", 0.0) - dt)
        if follow is None and "collar" in self.camp_items and c["bite_cd"] <= 0:
            foe = self.collar_target(c)
            if foe:   # (Spiked Collar: nobody grabs its people)
                c["hop"], c["bite_cd"] = [(c["x"], c["y"]), (foe.x, foe.y), 0.0, ("bite", foe)], COLLAR_EVERY
                c["facing"] = 1 if (foe.x - c["x"]) - (foe.y - c["y"]) >= 0 else -1
                return
        self.chomper_waddle(c, dt, follow)
        if c["timer"] <= 0 and self.current:
            wanted = {m["hop"][3][1] for m in (self.chomper, self.pup) if m and m is not c and m["hop"]
                      and m["hop"][3][0] == "block"}
            cells = [k for k in self.current if k not in wanted] or list(self.current)
            cell = max(cells, key=lambda k: (self.current[k].value, random.random()))   # (expensive tastes)
            c["hop"], c["timer"] = [(c["x"], c["y"]), (cell[0] + 0.5, cell[1] + 0.5), 0.0, ("block", cell)], \
                every / self.tick()
            c["facing"] = 1 if (cell[0] + 0.5 - c["x"]) - (cell[1] + 0.5 - c["y"]) >= 0 else -1

    def collar_target(self, c):
        """Spiked Collar: the monster with hold of someone nearest Chompers (bosses are too big to bite)."""
        grabbers = [e for e in self.enemies if e.state == "attacking" and e.victim is not None and not e.boss
                    and e.targetable]
        return min(grabbers, key=lambda e: math.hypot(e.x - c["x"], e.y - c["y"])) if grabbers else None

    def collar_bite(self, c, foe):
        """Chompers lands on a monster that's grabbed one of its people: a little one goes down whole (twice the
        bounty); anything bigger is knocked loose with a nasty bite."""
        if foe not in self.enemies or not foe.targetable:   # (gone already: it'll try again soon)
            c["bite_cd"] = 1.0
            return
        c["chomp_at"] = self.clock
        px, py = enemy_anchor(foe, self.rise, time.time())
        self.cues.append(("smash", 0.3))
        if foe.kind in COLLAR_SWALLOW and not foe.elite:
            extra = self.bounty_worth(foe)
            self.break_grip(foe)
            self.kill_enemy(foe)
            gained = self.earn(extra)
            self.floaters.append(Floater(f"GULP! +{fmt(gained)}", px, py - 50, GOLD, life=1.6, size=26, coin=True))
            return
        self.break_grip(foe)
        self.floaters.append(Floater("CHOMP!", px, py - 50, (255, 150, 120), life=1.2, size=26))
        self.hit_enemy(foe, foe.max_hp * COLLAR_BITE * foe.pct_scale, floor=False, ring=GOLD, heavy=True)

    def chomper_waddle(self, c, dt, follow=None):
        """A camp Mimic between gobbles: shuffling about a few tiles at a time on its stubby legs, little hops as it
        goes, stopping now and then to sit (the pup: never far behind its parent)."""
        c["waddle_timer"] = c.get("waddle_timer", 0.0) - dt
        if follow and math.hypot(follow["x"] - c["x"], follow["y"] - c["y"]) > 1.2:   # (catching up)
            c["waddle_to"] = (min(GRID - 0.5, max(0.5, follow["x"] + 0.5)), min(GRID - 0.5, max(0.5, follow["y"] + 0.4)))
            c["waddle_timer"] = 0.5
        elif c["waddle_timer"] <= 0:
            c["waddle_timer"] = random.uniform(*STROLL_EVERY)
            c["waddle_to"] = None if random.random() < STROLL_PAUSE else                 (min(GRID - 0.5, max(0.5, c["x"] + random.uniform(-2, 2))),
                 min(GRID - 0.5, max(0.5, c["y"] + random.uniform(-2, 2))))
        goal = c.get("waddle_to")
        c["lift"] = 0.0
        if goal is None:
            return
        dx, dy = goal[0] - c["x"], goal[1] - c["y"]
        dist = math.hypot(dx, dy)
        if dist < 0.05:
            c["waddle_to"] = None
            return
        step = min(dist, CHOMP_WADDLE * dt)
        c["x"] += dx / dist * step
        c["y"] += dy / dist * step
        c["facing"] = 1 if dx - dy >= 0 else -1
        c["lift"] = abs(math.sin(self.clock * 9)) * 0.15   # (little hops)

    def chomp(self, c, cell, payout):
        """A camp Mimic lands on its block and gobbles it whole: it breaks (paying as usual), and the Mimic coughs up
        the rest of `payout` times its worth."""
        block = self.current.get(cell)
        if block is None:   # (someone else got there first: it sulks, then tries again soon)
            c["timer"] = 2.0
            return
        c["chomp_at"] = self.clock
        self.feats["chomps"] += 1
        bonus = block.value * value_mult(self.lv("value")) * (payout - 1)
        px, py = self.cell_screen(cell)
        self.cues.append(("smash", 0.35))
        self.damage(cell, block.hp + 1e-9, sparks=12)
        gained = self.earn(bonus)
        self.floaters.append(Floater(f"CHOMP! +{fmt(gained)}", px, py - 60, GOLD, life=1.6, size=26, coin=True))
        self.fly_coins(px, py, 5)

    def throw_femur(self):
        """Tyrant's Femur: the crew member nearest a monster that has hold of someone hurls a bone at it
        (the one whose victim is worst off first). Bosses are left to you."""
        aimed = {id(f[2]) for f in self.femur_throws}
        grabbers = [e for e in self.enemies if e.state == "attacking" and e.victim is not None and not e.boss
                    and e.targetable and id(e) not in aimed]
        if not grabbers:
            return
        enemy = min(grabbers, key=lambda e: e.victim.hp / max(1e-9, e.victim.max_hp))
        crew = [m for m in self.miners if m.state == "working" and m is not enemy.victim]
        if not crew:
            return
        m = min(crew, key=lambda c: math.hypot(c.x - enemy.x, c.y - enemy.y))
        m.anim = 1.0
        m.facing = 1 if (enemy.x - m.x) - (enemy.y - m.y) >= 0 else -1
        self.femur_throws.append([m, self.entity_screen(m, 34), enemy, 0.0])
        self.femur_timer = self.art_add("femur")
        self.give_xp(m, XP_PER_ROCK)
        self.cues.append(("hit", 0.3))

    def update_whetstone_trip(self, m, dt, speed):
        sx, sy = WHETSTONE_POS
        if m.task == "whetstone":
            if self.walk_to(m, sx + 0.35, sy - 0.35, speed * ROLES[m.role]["speed"], dt):
                m.task, m.task_timer = "sharpening", WHET_SHARPEN_SECS
        else:
            m.task_timer -= dt
            m.anim = 0.5 + 0.5 * math.sin(self.clock * 30)
            if random.random() < dt * 25:   # sparks off the wheel
                px, py = self.entity_screen(_Spot(sx, sy, self.column_height(*self.cell_of(sx, sy))), 18)
                self.particles.append(Particle(px, py, random.choice([(255, 230, 140), (255, 255, 255)])))
            if m.task_timer <= 0:
                m.task, m.sharp, m.anim = "idle", WHET_SHARP_SECS, 0.0
                px, py = self.entity_screen(m, 56)
                self.floaters.append(Floater("Sharp!", px, py, (180, 230, 255), life=1.2, size=20))

    def update_upgrade_systems(self, dt, combat):
        # Combo Clicks: drops if you stop clicking (but not while you hold the mouse to charge a slam)
        if not self.combo_held:
            self.combo_timer = max(0.0, self.combo_timer - dt)
        if self.combo_timer <= 0:
            self.combo = 0
        # Golden Blocks
        if self.golden:
            self.golden[1] -= dt
            if self.golden[1] <= 0 or self.golden[0] not in self.current:
                self.golden = None
        elif self.lv("goldblock") and self.current:
            self.golden_timer -= dt
            if self.golden_timer <= 0:
                self.golden_timer = golden_interval(self.lv("goldblock")) / self.tick()
                cell = random.choice(list(self.current))
                self.golden = [cell, GOLDEN_SECS]
                px, py = self.cell_screen(cell)
                self.floaters.append(Floater("A golden block! Click it!", px, py - 60, GOLD, life=2.0, size=26))
        # Gold Vault: interest on banked gold, capped by what you earn
        if self.lv("vault"):
            self.vault_timer += dt
            if self.vault_timer >= VAULT_PERIOD:
                self.vault_timer = 0.0
                cap = max(50.0, self.gold_per_sec() * 60) * self.lv("vault")
                interest = min(self.gold * vault_rate(self.lv("vault")), cap)
                if interest >= 1:
                    interest = self.earn(interest)
                    x, y = GOLD_HUD_COIN
                    self.floaters.append(Floater(f"INTEREST +{fmt(interest)}", x + 130, y + 120, GOLD,
                                                 life=2.2, size=26, coin=True))
        # Whetstone: send the bluntest idle digger over every few seconds, one at a time
        if self.lv("whetstone"):
            self.whet_timer -= dt
            busy = any(m.task in ("whetstone", "sharpening") for m in self.miners)
            if self.whet_timer <= 0 and not busy:
                blunt = [m for m in self.diggers() if m.state == "working" and m.sharp <= 0]
                if blunt:
                    m = min(blunt, key=lambda c: math.hypot(c.x - WHETSTONE_POS[0], c.y - WHETSTONE_POS[1]))
                    m.task, m.target = "whetstone", None
                self.whet_timer = WHET_GAP
        if self.mudlings:   # (the Clay Pit's mudlings)
            self.update_mudlings(dt)
        if self.rods or self.arcs:   # (Grizzle's Lightning Rods)
            self.update_rods(dt)
        # Chompers, the camp's tame Mimic
        if "chompers" in self.camp_items:
            self.update_chompers(dt)
        # Tyrant's Femur
        if self.art_add("femur") and combat:
            self.femur_timer -= dt
            if self.femur_timer <= 0:
                self.throw_femur()
        # Ballista
        if self.lv("ballista") and combat:
            self.ballista_timer -= dt
            targets = [e for e in self.enemies if e.targetable]
            if targets:
                bx, by = BALLISTA_POS
                target = min(targets, key=lambda e: (e.state != "attacking", math.hypot(e.x - bx, e.y - by)))
                tx, ty = enemy_anchor(target, self.rise, time.time())
                sx, sy = self.ballista_screen()
                self.ballista_aim = math.atan2(ty - sy, tx - sx)
                if self.ballista_timer <= 0:
                    self.ballista_timer = ballista_interval(self.lv("ballista")) / self.tick()
                    self.bolts.append([(sx, sy), target, 0.0])
        for throw in self.bone_throws:
            throw[2] += dt
            target = throw[1]
            if throw[2] >= BONE_THROW_SECS and target.state != "down":
                dmg = BONE_THROW_SHARE * crew_hp_at(self.depth)
                self.hurt(target, dmg)
                px, py = self.entity_screen(target, 40)
                self.floaters.append(Floater(f"-{dmg:.0f}", px, py, BAD, life=1.0, size=22))
                self.cues.append(("hit", 0.8))
                self.rings.append([px, py + 10, 0.0, 40, (235, 228, 205)])
                for _ in range(10):   # the bone shatters
                    self.particles.append(Particle(px, py, random.choice([(235, 228, 205), (170, 160, 135)]),
                                                   big=True))
                if target.hp <= 0:
                    if target.attacker:
                        target.attacker.release()
                    self.miner_down(target, killer=self.boss())
        self.bone_throws = [b for b in self.bone_throws if b[2] < BONE_THROW_SECS]
        for rock in self.rocks:
            rock[3] += dt
            thrower, _, boss, age = rock
            if age >= ROCK_SECS and boss in self.enemies and boss.targetable:
                self.hit_enemy(boss, boss.max_hp * ROCK_SHARE * level_mult(thrower.level), floor=False,
                               ring=(170, 150, 130), by=thrower)
        self.rocks = [r for r in self.rocks if r[3] < ROCK_SECS]
        for throw in self.femur_throws:
            throw[3] += dt
            thrower, _, enemy, age = throw
            if age >= FEMUR_SECS and enemy in self.enemies and enemy.targetable:
                self.hit_enemy(enemy, enemy.max_hp * FEMUR_SHARE, floor=False, ring=(235, 228, 205), by=thrower)
                px, py = enemy_anchor(enemy, self.rise, time.time())
                for _ in range(8):   # the bone shatters
                    self.particles.append(Particle(px, py, random.choice([(235, 228, 205), (170, 160, 135)])))
        self.femur_throws = [f for f in self.femur_throws if f[3] < FEMUR_SECS]
        for bolt in self.bolts:
            bolt[2] += dt
            if bolt[2] >= BOLT_SECS:
                enemy = bolt[1]
                if enemy in self.enemies and enemy.targetable:
                    skewered = self.bolt_line(enemy)
                    for e in skewered:
                        if e in self.enemies:
                            self.hit_enemy(e, e.max_hp * ballista_share(self.lv("ballista")) * e.pct_scale,
                                           floor=False, ring=(220, 190, 130))
                    if len(skewered) > 1:
                        px, py = enemy_anchor(enemy, self.rise, time.time())
                        self.floaters.append(Floater(f"SKEWERED x{len(skewered)}!", px, py - 50, (230, 200, 140),
                                                     life=1.0, size=24))
        self.bolts = [b for b in self.bolts if b[2] < BOLT_SECS]
        for fx in self.chest_fx:
            fx[2] += dt
        self.chest_fx = [fx for fx in self.chest_fx if fx[2] < CHEST_FX_SECS]
        for cell in list(self.webs):
            self.webs[cell] -= dt
            if self.webs[cell] <= 0:
                del self.webs[cell]
        for fx in self.spike_fx:
            fx[1] += dt
        self.spike_fx = [fx for fx in self.spike_fx if fx[1] < SPIKE_FX_SECS]

    def bolt_line(self, target):
        """A Ballista bolt pierces: its target, and every monster in line with it out to PIERCE_PAST beyond."""
        bx, by = BALLISTA_POS
        dx, dy = target.x - bx, target.y - by
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        line = [target]
        for e in self.enemies:
            if e is target or not e.targetable:
                continue
            along = (e.x - bx) * ux + (e.y - by) * uy
            if 0 < along <= length + PIERCE_PAST and abs((e.x - bx) * uy - (e.y - by) * ux) <= PIERCE_WIDTH:
                line.append(e)
        return line

    def ballista_screen(self):
        """Where bolts leave the ballista on screen."""
        bx, by = BALLISTA_POS
        x, y = iso(bx, by, self.column_height(*self.cell_of(bx, by)) + self.rise)
        return x, y - 18

    # ----- update ---------------------------------------------------------
    # ----- the collapse (The Void Maw falls) ------------------------------------------------------------------
    def start_collapse(self):
        """The Void Maw has fallen at the bottom of the expedition: the dig ends there and then, blocks or no.
        The floor caves in from its hole outwards; a rope drops to each crew member just before the ground under
        them goes, and they climb out - every one in their own way. Monsters and graves go down with the floor."""
        self.collapse = 0.0
        self.expedition_won()
        self.bombs, self.bolts, self.rocks, self.bone_throws, self.femur_throws = [], [], [], [], []
        c = GRID / 2
        self.crumble = {(x, y): CRUMBLE_FROM + CRUMBLE_SPREAD * math.hypot(x + 0.5 - c, y + 0.5 - c)
                        + random.uniform(0, 0.35) for x in range(GRID) for y in range(GRID)}
        for e in self.enemies:   # whatever had hold of someone lets go
            if e.victim and e.victim.attacker is e:
                e.victim.attacker = None
            e.victim = None
        self.arrows = []
        for m in self.miners:   # (the camp's people, knocked out, come round to climb)
            if getattr(m, "ko", False) and m.state == "down":
                self.revive(m, quiet=True)
        styles = list(CLIMB_STYLES)
        random.shuffle(styles)
        crew = sorted((m for m in self.miners if m.state != "down"), key=lambda m: self.crumble[self.cell_of(m.x, m.y)])
        for i, m in enumerate(crew):
            if m.state == "grabbed":
                m.state = "working"
            m.attacker, m.stun, m.curse = None, 0.0, 0.0
            gives = self.crumble[self.cell_of(m.x, m.y)]
            rope = max(0.4, gives - random.uniform(1.4, 2.0))
            m.climb = dict(style=ROLE_CLIMB.get(m.role, styles[i % len(styles)]), rope=rope,
                           grab=rope + ROPE_DROP + random.uniform(0.1, 0.4), phase=random.uniform(0, math.tau))
        for g in self.ghosts:   # the Graveyard Shift's ghosts just drift up and away
            g.climb = dict(style="float", rope=None, grab=self.crumble[self.cell_of(g.x, g.y)] - 1.0, phase=0.0)
        self.shouts = 0
        self.cues.append(("boom", 0.8))
        self.floaters.append(Floater("THE SHAFT IS COMING DOWN!", W / 2, 250, (255, 190, 90), life=3.0, size=40))
        self.notice = ["The Void Maw's death-throes are bringing the shaft down - get the crew out!", COLLAPSE_SECS, ""]

    def update_collapse(self, dt):
        """The shaft coming down: the ground shakes harder as the floor goes, cells crumble away kicking up dust,
        the crew climb their ropes; when it's over, on to the camp."""
        was, self.collapse = self.collapse, self.collapse + dt
        t = self.collapse
        settle = max(0.0, 1 - max(0.0, t - (COLLAPSE_SECS - 2.5)) / 2.5)
        self.shake, self.shake_power = 0.2, (3 if t < CRUMBLE_FROM else 6) * settle
        falling = 0
        for cell, at in self.crumble.items():
            if was < at <= t:   # this cell just gave way
                falling += 1
                z = self.column_height(*cell) + self.rise
                px, py = iso(cell[0] + 0.5, cell[1] + 0.5, z)
                for _ in range(5):
                    self.particles.append(Particle(px, py, random.choice([(120, 100, 90), (80, 66, 60), (150, 130, 110)]),
                                                   big=random.random() < 0.4))
                if random.random() < 0.3:
                    self.smoke.append(Smoke(px, py, size=12))
        if falling and random.random() < 0.35:
            self.cues.append(("smash", 0.35))
        for m in self.miners:   # a few shouts as the ropes are grabbed
            plan = getattr(m, "climb", None)
            if plan and was < plan["grab"] <= t and self.shouts < 4 and random.random() < 0.35:
                self.shouts += 1
                px, py = self.entity_screen(m, 60)
                self.floaters.append(Floater(random.choice(["Go, go, go!", "Hold on!", "Pull me up!", "Climb!",
                                                            "Don't look down!", "Not without my pick!"]),
                                             px, py, TEXT, life=1.2, size=22))
        if t >= COLLAPSE_SECS:
            self.collapse, self.camp_ready = None, True

    def update(self, dt, combat=True):
        """Advance the simulation. With combat=False enemies freeze and none spawn."""
        self.clock += dt
        self.achieve_timer -= dt
        if self.achieve_timer <= 0:
            self.achieve_timer = 1.0
            self.check_achievements()
        if self.collapse is not None:   # The Void Maw has fallen: the shaft comes down (nothing else goes on)
            self.update_collapse(dt)
            self.update_effects(dt)
            return
        if self.boss_return > 0:   # the bottom's boss, back for another try
            self.boss_return -= dt
            if self.boss_return <= 0:
                self.spawn_boss()
        self.sync_miners()
        self.sync_ghosts()
        if self.rise < 0:
            self.rise = min(0.0, self.rise + dt * 2.5)
        self.second_wind = max(0.0, self.second_wind - dt)
        if self.lv("coffee"):
            self.coffee_timer += dt
            if self.coffee_timer >= coffee_interval(self.lv("coffee")) / self.tick():
                self.coffee_timer = 0.0
                self.coffee_break()
        speed = walk_speed(self.lv("boots")) * self.art_mult("walk")
        swing = self.miner_swing_time()
        regen = miner_regen(self.lv("firstaid")) * self.art_mult("regen")
        boss = self.foreman()
        boss_here = boss if boss and boss.state == "working" else None
        holdout = None if self.current else self.boss_target()   # layer cleared, boss still standing
        shades = [e for e in self.enemies if e.spec.get("aura") and e.targetable]   # (Abyssal Shades)
        self.plant_banner()   # (Rocco's banner: who's under it, see under_banner)
        for m in self.miners + self.ghosts:   # (ghosts dig with the rest)
            if m.state == "down":
                m.respawn -= dt
                if m.respawn <= 0:
                    if getattr(m, "ko", False):
                        self.revive(m)
                    else:
                        self.respawn_miner(m)
                continue
            if m.state == "grabbed":
                if random.random() < dt * 5:   # panicked sweat
                    px, py = self.entity_screen(m, 36)
                    self.particles.append(Particle(px, py, (150, 200, 255)))
                if combat and m.role == "guard":   # guards always fight back, and hard
                    m.swing -= dt
                    if m.swing <= 0:
                        m.swing += GUARD_SWING
                        self.guard_strike(m, m.attacker)
                elif combat and self.lv("defense"):   # Self Defense: a strike at the attacker every second
                    m.swing -= dt   # (a steady rhythm: faster picks don't make for faster fighting)
                    if m.swing <= 0:
                        m.swing += DEFENSE_STRIKE_SECS
                        self.miner_strike(m)
                continue
            if self.clock - m.last_hurt >= REGEN_DELAY:   # (no healing in the thick of it)
                m.hp = min(m.max_hp, m.hp + regen * m.max_hp * dt)
            mspeed = speed * self.web_slow(m)
            if getattr(m, "held", None):   # caged by the Bone Tyrant, or entranced by the Vampire Lord
                self.update_held(m, dt, mspeed)
                continue
            if m.stun > 0:   # reeling from the Fanged Behemoth's screech
                m.stun = max(0.0, m.stun - dt)
                m.anim = 0.0
                continue
            if m.role == "hero" and self.update_hero(m, dt, mspeed * ROLES["hero"]["speed"]):   # off to a rescue
                m.draw_z += (self.column_height(*self.cell_of(m.x, m.y)) - m.draw_z) * min(1.0, dt * 10)
                continue
            if not m.digs:   # specialists with their own jobs
                {"foreman": self.update_foreman, "guard": self.update_guard, "medic": self.update_medic,
                 "demolitionist": self.update_demolitionist, "engineer": self.update_engineer,
                 "archer": self.update_archer, "taxman": self.update_taxman, "claygolem": self.update_clay_golem,
                 }[m.role](m, dt, mspeed * ROLES[m.role]["speed"])
                m.draw_z += (self.column_height(*self.cell_of(m.x, m.y)) - m.draw_z) * min(1.0, dt * 10)
                continue
            m.sharp = max(0.0, m.sharp - dt)
            m.forged = max(0.0, getattr(m, "forged", 0.0) - dt)
            m.coffee = max(0.0, m.coffee - dt)
            if m.task in ("whetstone", "sharpening"):   # off to the sharpening wheel
                self.update_whetstone_trip(m, dt, mspeed)
                m.draw_z += (self.column_height(*self.cell_of(m.x, m.y)) - m.draw_z) * min(1.0, dt * 10)
                continue
            if holdout:   # nothing left to dig: keep moving, and pelt the boss with rocks from a distance
                self.update_skirmish(m, holdout, dt, mspeed * ROLES[m.role]["speed"])
                m.draw_z += (self.column_height(*self.cell_of(m.x, m.y)) - m.draw_z) * min(1.0, dt * 10)
                continue
            my_swing = swing   # pep talk: miners near the foreman swing faster still
            if boss_here and math.hypot(m.x - boss_here.x, m.y - boss_here.y) <= PEP_TALK_RADIUS:
                my_swing = swing / (1 + (PEP_TALK_BOOST - 1) * level_mult(boss_here.level))
            if m.coffee > 0:   # Coffee Break
                my_swing /= 1 + COFFEE_BOOST
            if getattr(m, "forged", 0) > 0 and "toolkit" in self.camp_items:   # (rigged and wound up)
                my_swing /= 1 + WOUND_UP
            if self.under_banner(m):   # under Rocco's banner
                my_swing /= 1 + BANNER_BOOST
            drag = self.flare_drag(m, shades) if shades or self.void_pools else 1.0
            m.shaded = drag > 1.0
            my_swing *= drag   # an Abyssal Shade's darkness: every swing drags
            if m.target is None or m.target not in self.current:
                m.target = self.pick_target(m)
            m.anim = max(0.0, m.anim - dt * 4)
            m.crit = max(0.0, m.crit - dt)
            if m.target:
                tx, ty = m.target[0] + 0.5, m.target[1] + 0.5
                dx, dy = tx - m.x, ty - m.y
                dist = math.hypot(dx, dy)
                if dist > 0.05:
                    step = min(dist, mspeed * ROLES[m.role]["speed"] * dt)
                    m.x += dx / dist * step
                    m.y += dy / dist * step
                    m.facing = 1 if (dx - dy) >= 0 else -1
                elif m.role == "driller":   # jackhammer: many small hits, no crits
                    m.swing -= dt
                    m.anim = 0.6
                    while m.swing <= 0 and m.target in self.current:
                        m.swing += my_swing / DRILL_HITS_PER_SWING
                        self.driller_hit(m.target, m)
                else:
                    m.swing -= dt
                    if m.swing <= 0:
                        m.swing += my_swing
                        m.anim = 1.0
                        self.miner_hit(m.target, m)
            target_z = self.column_height(*self.cell_of(m.x, m.y))
            m.draw_z += (target_z - m.draw_z) * min(1.0, dt * 10)

        if self.notice:
            self.notice[1] -= dt
            if self.notice[1] <= 0:
                self.notice = None
        if self.announcement:
            self.announcement[1] -= dt
            if self.announcement[1] <= 0:
                self.announcement = None
        if self.reveals:
            self.reveals[0][1] += dt
        self.update_upgrade_systems(dt, combat)
        if combat and "watch" in self.camp_items:   # (the Pocket Watch: now and then, time stops)
            self.pocket_watch(dt)
        if combat and self.time_stop > 0:   # time stopped: the monsters (and everything they're up to) wait
            self.time_stop = max(0.0, self.time_stop - dt)
        elif combat:
            for e in self.enemies:
                self.ward(e)
            for e in [e for e in self.enemies if e.kind == "slimeling"]:
                self.shrivel(e, dt)
            for e in [e for e in self.enemies if e.kind == "shade"]:
                self.flare_burn(e, dt)
            self.shade_chill(dt)
            self.boss_auras()
            self.update_boss_tricks(dt)
            for e in list(self.enemies):
                e.update(self, dt)
            # waves keep coming while enemies remain (but a boss fight is just the boss and its own monsters)
            if self.depth >= ENEMY_START_DEPTH and not self.boss() and self.lv("miners"):   # (none till a miner's hired)
                self.enemy_timer -= dt
                if self.enemy_timer <= 0:
                    self.enemy_timer = self.wave_interval()
                    self.spawn_wave()

        if self.lv("autotap"):
            self.tap_timer += dt * self.lv("autotap")
            while self.tap_timer >= 1 and self.current:
                self.tap_timer -= 1
                self.player_hit(random.choice(list(self.current)), sparks=3,
                                ring_color=BRANCHES["hands"]["color"])
        if self.lv("phantom"):
            self.update_phantom(dt)
        if self.lv("boiler"):   # Steam Boiler: pressure builds slowly
            was = self.boiler
            self.boiler = min(1.0, self.boiler + dt / boiler_charge(self.lv("boiler")))
            if was < 1.0 <= self.boiler:   # a whistle when it's ready
                px, py = iso(BOILER_POS[0], BOILER_POS[1], self.column_height(*self.cell_of(*BOILER_POS)) + self.rise)
                self.floaters.append(Floater("Steam's up! Click the boiler", px, py - 70, (225, 235, 245),
                                             life=2.4, size=24))
        if self.steam is not None:
            self.steam += dt
            if self.steam >= STEAM_SECS:
                self.steam = None
        if self.lv("dynamite"):
            self.dynamite_timer += dt
            if self.dynamite_timer >= dynamite_interval(self.lv("dynamite")) / self.tick():
                self.dynamite_timer = 0.0
                self.throw_dynamite()
        for bomb in list(self.bombs):
            bomb.age += dt
            if bomb.landed and not getattr(bomb, "hissing", False):   # the fuse is lit: it hisses...
                bomb.hissing = True
                if not any(b is not bomb and b.landed for b in self.bombs):   # ...one hiss at a time, not a static
                    self.cues.append("fuse")
            if bomb.landed and random.random() < dt * 30:   # sparks fizzing off the fuse
                sx, sy = bomb_fuse_tip(bomb, self)
                self.particles.append(Particle(sx, sy, random.choice([(255, 230, 120), (255, 160, 60)])))
            if bomb.done:
                self.bombs.remove(bomb)
                self.detonate(bomb)
        self.update_arrows(dt)
        self.update_effects(dt)

    def update_effects(self, dt):
        """Fireballs, smoke, shake, particles, floating text and the rest of the eye candy."""
        for ex in self.explosions:
            ex[2] += dt
        self.explosions = [ex for ex in self.explosions if ex[2] < EXPLOSION_SECS]
        for s in self.smoke:
            s.update(dt)
        self.smoke = [s for s in self.smoke if s.life > 0]
        self.shake = max(0.0, self.shake - dt)
        self.flash = max(0.0, self.flash - dt)
        for b in self.crit_bursts:
            b[2] += dt
        self.crit_bursts = [b for b in self.crit_bursts if b[2] < CRIT_BURST_SECS]
        for q in self.quakes:
            q[2] += dt
            front = q[2] * QUAKE_SPEED
            for cell in self.current:   # kick up dust as the wave front rolls over each block
                if cell not in q[3] and math.hypot(cell[0] + 0.5 - q[0], cell[1] + 0.5 - q[1]) <= front:
                    q[3].add(cell)
                    if front <= q[4]:
                        px, py = self.cell_screen(cell)
                        for _ in range(2):
                            self.particles.append(Particle(px, py, random.choice([(150, 120, 90), (110, 88, 66)])))
        self.quakes = [q for q in self.quakes if q[2] < q[4] / QUAKE_SPEED + 0.25]
        for c in self.coins:
            c.update(dt)
            if c.arrived:
                self.gold_bump = 0.18
        self.coins = [c for c in self.coins if not c.arrived]
        self.gold_bump = max(0.0, self.gold_bump - dt)

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for f in self.floaters:
            f.update(dt)
        self.floaters = [f for f in self.floaters if f.life > 0]
        for r in self.rings:
            r[2] += dt
        self.rings = [r for r in self.rings if r[2] < 0.4]

    # ----- persistence ----------------------------------------------------
    def to_dict(self):
        pack = lambda layer: [[x, y, b.kind, b.hp, b.chest, b.artifact, b.bones] for (x, y), b in layer.items()]
        return dict(gold=self.gold, depth=self.depth, levels=self.levels,
                    total_blocks=self.total_blocks, current=pack(self.current),
                    next=pack(self.next), gps=self.gold_per_sec(),
                    version=SAVE_VERSION, layer_value=self.layer_value,
                    crew=[m.to_dict() for m in self.miners], graveyard=self.graveyard,
                    clock=self.clock, grid=GRID, artifacts=self.artifacts, boss_done=self.boss_done,
                    expedition=self.expedition, camp=self.camp, lifetime=self.lifetime,
                    camp_ready=self.camp_ready or self.collapse is not None, visit_hire=self.visit_hire,
                    camp_items=self.camp_items, achievements=self.achievements, feats=self.feats, run=self.run,
                    casual=self.casual)

    @classmethod
    def from_dict(cls, d):
        w = cls(casual=d.get("casual", False))
        w.gold = d["gold"]
        w.depth = d["depth"]
        w.expedition = d.get("expedition", 0)
        w.camp = [k for k in (RENAMED_ROLES.get(k, k) for k in d.get("camp", [])) if k in HIRES]
        # (older camps' buildings are gone)
        w.lifetime.update(d.get("lifetime", {}))
        w.camp_ready = d.get("camp_ready", False)
        w.visit_hire = RENAMED_ROLES.get(d.get("visit_hire"), d.get("visit_hire")) if w.camp_ready else None
        w.camp_items = [k for k in d.get("camp_items", []) if k in ITEMS]
        w.achievements = [k for k in d.get("achievements", []) if k in ACHIEVEMENTS]
        w.feats.update(d.get("feats", {}))
        w.levels.update({k: v for k, v in d["levels"].items() if k in w.levels})
        for up in UPGRADES:   # (an upgrade's cap was lowered since: e.g. Spirit Lantern's 3 levels became 1)
            if up["max"] and w.levels[up["key"]] > up["max"]:
                w.levels[up["key"]] = up["max"]
        if "nightshift" in d["levels"]:   # Night Shift became the Graveyard Shift: same slot and price
            w.levels["graveyardshift"] = d["levels"]["nightshift"]
        if "pockets" in d["levels"]:   # Deep Pockets (offline income) became Gold Dust: same slot and price
            w.levels["golddust"] = d["levels"]["pockets"]
        if d.get("version", 1) < 2:   # v1: Hire Miner level 0 meant one miner; now it means none
            w.levels["miners"] += 1
        w.total_blocks = d.get("total_blocks", 0)
        w.clock = d.get("clock", 0.0)
        w.graveyard = d.get("graveyard", [])
        renamed = {"idol": "medal", "goldtooth": "broclaw", "jawbone": "femur"}
        # (retired: the Cursed Idol, the Hoard's Golden Tooth, the Tyrant's Jawbone)
        w.artifacts = [k for k in (renamed.get(k, k) for k in d.get("artifacts", [])) if k in ARTIFACTS]
        w.refresh_artifacts()
        w.boss_done = d.get("boss_done", w.depth if boss_for(w.depth) else -1)   # older saves: no boss mid-layer
        if d.get("grid", 8) == GRID:
            # (older saves have no chest / artifact / bones flags: [x, y, kind, hp])
            # (each block's hp was saved; its toughness and worth come from the expedition)
            w.current = {(x, y): Block(k, w.depth, hp, *rest) for x, y, k, hp, *rest in d["current"]}
            w.next = {(x, y): Block(k, w.depth + 1, hp, *rest) for x, y, k, hp, *rest in d["next"]}
        else:   # saved on a different board size: start the current layer fresh
            w.current = w.new_layer(w.depth)
            prospector = w.lv("prospector")
            w.next = w.new_layer(w.depth + 1, ore_mult(prospector), richness=ore_richness(prospector))
        w.layer_value = d.get("layer_value") or layer_value(w.current)   # older saves: what's left of it
        if not w.current and not (boss_for(w.depth) and w.boss_done < w.depth):   # (a boss still bars the way)
            w.descend(award=False)
        w.miners = []
        w.sync_miners()
        saved_crew = [dict(c, role=RENAMED_ROLES.get(c.get("role", "miner"), c.get("role", "miner")))
                      for c in d.get("crew", [])]   # older saves have no crew: keep random looks
        for role in ROLES:   # match by role: specialists can sit anywhere in the list
            ours = [m for m in w.miners if m.role == role]
            theirs = [c for c in saved_crew if c.get("role", "miner") == role]
            for miner, data in zip(ours, theirs):
                miner.apply_saved(data)
        w.sync_ghosts(announce=False)
        w.gps_cached = d.get("gps", 0.0)
        w.enemy_timer = w.wave_interval()   # first wave on the saved depth's schedule, not depth 1's
        if boss_for(w.depth) and w.boss_done < w.depth and not w.camp_ready:   # saved mid boss fight: it comes back
            w.spawn_boss()
        w.run = d.get("run") or dict(new_run(w.clock), clean=w.depth <= 1)   # (older saves: from here on, if at all)
        if "achievements" not in d:   # a save from before achievements: what it's already done, quietly
            w.check_achievements(quiet=True)

        return w
