"""Game simulation: the dig site, miners, mining rules and save data."""
import math
import random
import time

from .artifacts import (ARTIFACT_CHANCE, ARTIFACT_MIN_DEPTH, ARTIFACTS, COMMON, FIRST_ARTIFACT_BY, STAT_KIND,
                        TROPHY_OF)
from .biomes import biome_at, block_color
from .blocks import BLOCKS, DEEP_ROCK_FROM, HP_GROWTH, Block, crack_share, generate_layer, layer_value
from .camp import CAMP, COLLAPSE_DELAY, CYCLE_GROWTH, EXPEDITION_DEPTH
from .config import BAD, GOLD, GOLD_HUD_COIN, GOOD, GRID, TEXT, TILE_H, TILE_W, W
from .dynamite import EXPLOSION_SECS, Bomb
from .effects import (CRIT_BURST_SECS, QUAKE_RADIUS, QUAKE_SPEED, CoinFly, Floater, Particle,
                      Smoke)
from .enemies import (ELITE_HP, boss_minion_cap, boss_minion_mult,
                      BAT_FORM_EVERY, BAT_FORM_SPEED, BITE_BREAK, BITE_HEAL, BITE_SECS, BITE_SHARE,
                      BONE_THROW_SHARE, BONE_THROW_SECS, BONE_VOLLEY, BONE_VOLLEY_HURT, CHUNK_SPLIT_HP,
                      PILE_HP, PILE_SECS, REFORM_HP, SLIME_SPLIT_AT, SLIME_SPLIT_HP, STALK_PATIENCE, STRIDE_RANGE,
                      STRIDE_SPEED, THROW_ANIM_SECS, THROW_RELEASE, VOLLEY_GAP,
                      SCREECH_EVERY, SCREECH_RADIUS, SCREECH_STUN,
                      BOSS_MAX_MINIONS, BOSS_SLAM_RADIUS, BOSS_TIME_LIMIT, CURSE_EVERY, CURSE_RADIUS, CURSE_SHARE,
                      CURSE_SECS, ENEMY_START_DEPTH, ENEMY_TYPES, ENRAGE_AT, RALLY_RADIUS, RALLY_SPEED,
                      RALLY_TOUGH, SHIELD_MAX, SHIELD_PER_WISP, WEB_SECS, WEB_SLOW, Enemy, boss_for, choose_kind,
                      crew_hp_at, elite_chance,
                      edge_cells, max_enemies, spawn_interval,
                      GOLEM_ARMOUR, SHADE_RADIUS, SHADE_SLOW, BRO_MOUND_SPEED, BRO_NAMES, BRO_SURFACE_RADIUS,
                      BRO_SWAP, MOUNTAIN_ARMOUR, MOUNTAIN_HEAVE,
                      VOID_EYE, VOID_EYE_OPEN, VOID_EYE_SHUT, VOID_GLANCE, VOID_BITE, VOID_BITE_RADIUS, VOID_INHALE_EVERY, VOID_INHALE_PULL, VOID_INHALE_RADIUS,
                      VOID_INHALE_SECS, VOID_POOL_DRAIN, VOID_POOL_EVERY,
                      VOID_POOL_SECS, VOID_POOLS)
from .iso import iso
from .world_layout import (BALLISTA_POS, BOILER_POS, BOLT_SECS, CHEST_FX_SECS, ROCK_SECS, SPIKE_FX_SECS,
                           STEAM_SECS, WHETSTONE_POS)
from .miners import (CRIT_ANIM_SECS, MAX_LEVEL, ROLES, Miner, base_name, level_mult, new_stats, numbered_name,
                     xp_to_next)
from .sprites import bomb_fuse_tip, enemy_anchor
from .upgrades import (BRANCHES, UPGRADES, ballista_interval, ballista_share, chest_chance, clear_share,
                       combo_step, dust_share, golden_interval, golden_payout, milestone_mult, slam_mult, streak_bonus,
                       PHANTOM_CHARGE, PHANTOM_WINDUP, phantom_interval,
                       trap_share, vault_rate, vein_share, whetstone_boost,
                       ACID_HITS, CUTDOWN_AT, VOLATILE_BLAST, flare_burn, flare_ease, pole_share,
                       garlic_delay, garlic_ward, holy_bonus, salt_shrivel, salt_single, torch_grip, torch_singe,
                       SPREE_CAP, SPREE_WINDOW, spree_step, trophy_mult, boiler_charge,
                       bounty_mult, click_damage, depth_reached, dynamite_interval,
                       enemy_hit_floor, is_maxed, is_unlocked, masterwork_mult, midas_mult, miner_count, miner_damage,
                       miner_max_hp, last_stand_mult, miner_regen, miner_strike, monster_damage, ore_damage_mult,
                       ore_mult, ore_richness,
                       COFFEE_BOOST, COFFEE_SECS, coffee_cups, coffee_interval, demo_interval, medic_heal, second_wind_boost, swing_time, upgrade_cost, value_mult,
                       veteran_level, walk_speed)
from .util import fmt

NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))
SECOND_WIND_SECS = 8.0
LAST_STAND_HP = 0.3     # miners below this share of their health get the Last Stand bonus
PEP_TALK_RADIUS = 2.5    # tiles: miners this close to the foreman get the pep-talk boost
PEP_TALK_BOOST = 1.15    # their swings are this much faster
FOREMAN_STAND_OFF = 0.7  # how close the foreman walks up to the miner they're supervising
FOREMAN_BARKS = ["Faster!", "Put your backs into it!", "That ore won't dig itself!", "Break's over!",
                 "Mind the monsters!", "Deeper!", "Swing, swing, swing!", "Good work, {name}!",
                 "Is that a nap, {name}?", "Gold doesn't wait!"]
DRILL_HITS_PER_SWING = 7.5   # a driller lands this many small hits in the time a miner swings once...
DRILL_SHARE = 0.25           # ...each worth this much of a miner's hit: ~1.9x a miner's digging
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
SKIRMISH_KEEP_AWAY = 2.6     # diggers keep at least this far from the boss (clear of its slam)
MAX_FLYING_COINS = 40
MILESTONE_EVERY = 5          # every 5th metre is a milestone with a bigger clear bonus (see Surveyor's Contract)
STREAK_CAP = 10              # Hot Streak: up to this many hits in a row count
CRIT_TEXT_GAP = 0.5          # crits: a new "CRIT!" label at most this often (crits between add to its count)...
CRIT_QUAKE_REACH = 1.3       # ...a miner's Seismic Strikes wave only reaches the blocks it shakes (a slam's goes further)...
CRIT_QUAKES_SHOWN = 3        # ...and only this many of those waves show at once
COMBO_WINDOW = 0.9           # Combo Clicks: seconds you can pause between clicks before it drops
COMBO_CAP = 20               # ...and the most clicks that count
GOLDEN_SECS = 6.0            # Golden Blocks: how long a golden block lasts
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


class World:
    def __init__(self):
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
        self.camp = []                     # what's been built at Base Camp, in order (it survives every reset)
        self.collapse = None               # seconds until the shaft comes down (The Void Maw just fell), or None
        self.camp_ready = False            # the shaft has come down: time to build at camp
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
        self.crit_label = [None, -9.0, 0]                       # the "CRIT!" on show: [floater, when, crits it counts]
        self.click_crit_label = [None, -9.0, 0]                 # ...and the one for your own (Steady Hands) crits
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
        self.cues = []                                          # sound effects to play this frame (see Game.update)
        self.grab_sound_at = -1e9                               # when the last "crew grabbed" alert sounded

    # ----- stats ----------------------------------------------------------
    def lv(self, key): return self.levels[key]

    def refresh_artifacts(self):
        """Combine the effects of every artifact found (multiply 'mult' stats, add 'add' stats)."""
        stats = {}
        effects = [ARTIFACTS[k]["effects"] for k in self.artifacts] + [CAMP[k]["effects"] for k in self.camp]
        for fx in effects:   # (Base Camp's buildings count too)
            for stat, v in fx.items():
                if STAT_KIND[stat] == "add":
                    stats[stat] = stats.get(stat, 0.0) + v
                else:
                    stats[stat] = stats.get(stat, 1.0) * v
        cycle = self.cycle()   # later expeditions: tougher monsters, bigger bounties
        stats["enemy_hp"] = stats.get("enemy_hp", 1.0) * cycle
        stats["bounty"] = stats.get("bounty", 1.0) * cycle
        self.art_stats = stats

    # ----- expeditions ----------------------------------------------------------------------------------------
    def cycle(self):
        """How much tougher (and richer) this expedition's blocks and monsters are than the first's."""
        return CYCLE_GROWTH ** self.expedition

    @property
    def display_depth(self):
        """The depth the player sees: it keeps counting across expeditions (101m, 102m...)."""
        return self.depth + EXPEDITION_DEPTH * self.expedition

    def shown(self, depth):
        """An expedition depth (an upgrade's unlock, say) as the player sees it."""
        return depth + EXPEDITION_DEPTH * self.expedition

    def new_layer(self, depth, *args, **kw):
        """A fresh layer, toughened (and enriched) for this expedition."""
        return self.toughen(generate_layer(depth, *args, **kw))

    def toughen(self, layer, keep_hp=False):
        k = self.cycle()
        for b in layer.values():
            b.max_hp *= k
            b.value *= k
            if not keep_hp:
                b.hp *= k
        return layer

    def boss_time_limit(self):
        return BOSS_TIME_LIMIT + self.art_add("boss_time")

    @classmethod
    def next_expedition(cls, old, build):
        """The shaft has come down: `build` goes up at Base Camp, and a fresh expedition starts beneath it with
        nothing but the camp, the graveyard and the lifetime record."""
        w = cls()
        w.expedition = old.expedition + 1
        w.camp = old.camp + [build]
        w.graveyard = old.graveyard
        w.lifetime = dict(old.lifetime)
        w.lifetime["expeditions"] = w.expedition
        w.clock = old.clock
        w.refresh_artifacts()
        w.depth = 1   # (just below the camp: 101m)
        w.current, w.next = w.new_layer(1), w.new_layer(2)
        w.layer_value = layer_value(w.current)
        w.boss_done = 0
        w.gold = w.art_add("start_gold")
        w.miners = []
        w.sync_miners()
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
                "medic": 1 if self.lv("medic") else 0}   # (only ever one medic: levels make them better)

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
        built on one) grows as the blocks do, and with each expedition's tougher rock. Not with the endgame's deep
        rock, though - past 70m your hands slow down along with the crew."""
        return HP_GROWTH ** max(0, self.depth - GLOVES_TOUGHEN_FROM) * self.cycle()

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
        # (Veterans and Base Camp's Drill Yard: they turn up already trained)
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
        free = [m for m in self.miners if m.state == "working"]
        return min(free, key=lambda m: (m.x - x) ** 2 + (m.y - y) ** 2, default=None)

    def spawn_wave(self):
        """Top the board up to the enemy cap for this depth. Returns how many spawned."""
        count = max_enemies(self.depth) - len(self.enemies)
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
        per_click = self.enemy_hit_damage(boss, self.monster_hit_damage()) * self.art_mult("boss_dmg")
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
        self.enemies.append(Enemy(kind, self.depth, cell, self.column_height(*cell), delay=1.2,
                                  hp_mult=self.art_mult("enemy_hp")))
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
        count = min(round(minion["count"] * boss_minion_mult(self.depth)), boss_minion_cap(self.depth) - alive)
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
            if e.spec.get("lifesteal"):   # the Vampire Lord feeds on every crew member it hits
                e.hp = min(e.max_hp, e.hp + e.max_hp * e.spec["lifesteal"])
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
        children = []
        for i in range(count):
            a = i / count * math.tau + random.uniform(-0.3, 0.3)
            child = Enemy(split["into"], self.depth, cell, self.column_height(*cell), elite=slime.elite)
            child.max_hp = child.hp = slime.max_hp * share
            child.state = "hunting"
            child.x = min(GRID - 0.05, max(0.05, slime.x + math.cos(a) * spread))
            child.y = min(GRID - 0.05, max(0.05, slime.y + math.sin(a) * spread))
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

    # ----- the deep's bosses --------------------------------------------------------------------------------------
    def update_burrow_bros(self, boss, dt):
        """The Burrow Brothers: one fights above while the other's mound tunnels towards the crew; every BRO_SWAP
        seconds they swap, the tunneller bursting up in a slam. Once one has fallen, the other fights on above."""
        if boss.bro_hp is None:   # (each brother has half the health)
            boss.bro_hp = [boss.max_hp / 2, boss.max_hp / 2]
            boss.mound = [min(GRID - 0.5, boss.x + 2.5), boss.y]
        boss.surface_t += dt
        if boss.bro_hp[1 - boss.up] <= 0:   # the other's fallen: no more tunnelling
            boss.mound = None
            return
        crew = [m for m in self.miners if m.state == "working"]
        if crew:   # the mound creeps towards whoever is nearest
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
            self.current[cell] = self.toughen({cell: Block("stone", self.depth)})[cell]
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

    def collapse(self, boss):
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
        """A cursed crew member under the mouse, or None."""
        for m in self.miners:
            if m.curse > 0 and m.state != "down":
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
        self.finish_boss_fight()
        if self.depth >= EXPEDITION_DEPTH:   # the bottom of the expedition: the shaft is about to come down
            self.collapse = COLLAPSE_DELAY
            self.notice = ["The ground is shaking... the shaft is coming down!", COLLAPSE_DELAY + 2, ""]

    def finish_boss_fight(self):
        """The boss is gone (beaten or fled): waves resume, and an already-cleared layer gives way."""
        self.boss_done = self.depth
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
        return [k for k in COMMON if k not in self.artifacts]

    def bury_artifact(self, layer, depth):
        """Now and then a new layer hides an artifact in one of its blocks (a glint gives it away). The layer at
        FIRST_ARTIFACT_BY always does if none has turned up yet, so every player finds one early on."""
        if depth < ARTIFACT_MIN_DEPTH or not layer or not self.undiscovered():
            return
        first = depth == FIRST_ARTIFACT_BY and not self.artifacts
        if not first and random.random() >= ARTIFACT_CHANCE:
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
        """Death is permanent: the miner is buried, and a new recruit arrives when the timer runs out."""
        miner.state = "down"
        miner.curse = 0.0
        miner.respawn = RESPAWN_SECS
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

    def bury(self, miner, killer=None):
        self.graveyard.append({
            **miner.to_dict(),
            "killer": killer.spec["name"] if killer else "Unknown",
            "died_depth": self.display_depth,
            "died_clock": self.clock,
        })

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
                 * self.armour(enemy, heavy) * (self.art_mult("boss_dmg") if enemy.boss else 1))
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
                self.collapse(enemy)
                return
            self.kill_enemy(enemy, by)

    def player_hit_enemy(self, enemy, pos=None):
        """You click a monster: Monster Slayer damage, Critical Smite, then Cleave onto neighbours.
        `pos` is where you clicked (The Void Maw only really feels a click on its open eye)."""
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
                text = f"Saved by {credit.name}!" if credit and credit.role == "guard" else "Saved!"
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
        """Prerequisites owned and depth milestone reached."""
        return is_unlocked(up, self.levels) and depth_reached(up, self.depth)

    def can_buy(self, up):
        return self.available(up) and not is_maxed(up, self.levels) and self.gold >= self.cost(up)

    def cost(self, up):
        return math.ceil(self.base_cost(up) * self.art_mult("cost"))   # (Base Camp's Trading Post)

    def base_cost(self, up):
        return upgrade_cost(up, self.levels)

    def buy(self, up):
        if not self.can_buy(up):
            return False
        self.gold -= self.cost(up)
        self.levels[up["key"]] += 1
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
        if is_ore(block):
            dmg *= ore_damage_mult(self.lv("diamond"))
        crit = random.random() < 0.05 * self.lv("crit") + self.art_add("crit")
        if crit:
            dmg *= 3
            self.crit_effects(cell, miner)
        below = self.next.get(cell)
        if below and self.lv("deepstrike"):   # Deep Strike: crack the block underneath (never breaks it)
            below.hp = max(below.max_hp * 0.05, below.hp - dmg * 0.1 * self.lv("deepstrike"))
        if self.damage(cell, dmg, by=miner) and crit and self.lv("quake"):
            self.splash(cell, dmg * 0.25 * self.lv("quake"), BRANCHES["tools"]["color"], by=miner)

    def pick_bonus(self, miner, cell, weight):
        """Hot Streak (hits in a row on one block) and a freshly sharpened pick (Whetstone).
        `weight` = how much one hit counts towards the streak (a drill's rattle is a fraction)."""
        if not miner:
            return 1.0
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
        return bonus

    def crit_effects(self, cell, miner):
        """The look of a critical strike: the miner's overhead slam, an impact starburst, and with Seismic Strikes
        a small wave rippling out to the blocks it shakes. A late crew crits dozens of times a second, so it's kept
        light: one "CRIT!" label at a time (counting the crits it stands for), a few waves at once, no screen jolt."""
        px, py = self.cell_screen(cell)
        if miner:
            miner.crit = CRIT_ANIM_SECS
        self.crit_bursts.append([px, py, 0.0])
        self.crit_text(self.crit_label, "CRIT", px, py - 78, (255, 150, 90), 32)   # (clear of the slam)
        for _ in range(6):
            color = random.choice([(255, 230, 150), (255, 160, 70), (255, 255, 255)])
            self.particles.append(Particle(px, py, color, big=True))
        if self.lv("quake") and sum(1 for q in self.quakes if q[4] == CRIT_QUAKE_REACH) < CRIT_QUAKES_SHOWN:
            self.quakes.append([cell[0] + 0.5, cell[1] + 0.5, 0.0, set(), CRIT_QUAKE_REACH])

    def crit_text(self, label, word, x, y, color, size):
        """A crit's floating label - one at a time: crits landing while it's still fresh add to its count instead
        ("CRIT x7"), so a crew critting every few frames doesn't bury the screen in text."""
        floater, when, count = label
        if floater is not None and floater.life > 0 and self.clock - when < CRIT_TEXT_GAP:
            label[2] = count + 1
            floater.text = f"{word} x{label[2]}"
            floater.life = max(floater.life, 0.6)
            return
        floater = Floater(f"{word}!", x, y, color, life=0.9, size=size)
        self.floaters.append(floater)
        label[:] = [floater, self.clock, 1]

    def player_hit(self, cell, sparks=6, ring_color=(255, 255, 255), manual=False):
        """A click on a block - yours (manual) or the Auto-Tapper's."""
        block = self.current.get(cell)
        if not block:
            return
        dmg = self.click_hit_damage()
        px, py = self.cell_screen(cell)
        if manual:
            dmg *= self.combo_mult()
            if self.golden and self.golden[0] == cell:
                self.golden_jackpot(cell, block)
        if random.random() < 0.05 * self.lv("steady"):
            dmg *= 3
            self.crit_text(self.click_crit_label, "CRIT", px, py - 30, (220, 160, 255), 22)
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

    def combo_click(self):
        """Count one of your clicks towards the combo - any click, hit or miss, keeps it going."""
        if not self.lv("combo"):
            return
        self.combo = self.combo + 1 if self.combo_timer > 0 else 1
        self.combo_timer = COMBO_WINDOW

    def combo_mult(self):
        """Damage multiplier the current combo gives your clicks."""
        if not self.lv("combo"):
            return 1.0
        return 1 + combo_step(self.lv("combo")) * min(self.combo, COMBO_CAP)

    def golden_jackpot(self, cell, block):
        self.cues.append("jackpot")
        jackpot = self.earn(block.value * value_mult(self.lv("value")) * golden_payout(self.lv("goldblock")))
        px, py = self.cell_screen(cell)
        self.floaters.append(Floater(f"JACKPOT! +{fmt(jackpot)}", px, py - 50, GOLD, life=2.2, size=36, coin=True))
        self.fly_coins(px, py, 14)
        self.rings.append([px, py, 0.0, 120, GOLD])
        for _ in range(24):
            self.particles.append(Particle(px, py, random.choice([GOLD, (255, 240, 170), (255, 255, 255)]), big=True))
        self.golden = None

    def slam(self, cell, charge, target=None):
        """Charged Slam: a huge hit on `cell` (charge 0..1) that shakes the blocks around it.
        Monsters in the blast - and `target`, the one under the cursor - take up to 2x a monster click."""
        if cell not in self.current:
            return
        power = 0.3 + 0.7 * charge
        dmg = self.click_hit_damage() * slam_mult(self.lv("slam")) * power
        click = self.monster_hit_damage() * self.combo_mult()
        for e in list(self.enemies):
            in_blast = max(abs(e.x - (cell[0] + 0.5)), abs(e.y - (cell[1] + 0.5))) <= 1.5
            if e.targetable and (in_blast or e is target):
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

    def vent_boiler(self):
        """Steam Boiler: a full head of steam scalds every monster on the board (bosses, and the Slime King's
        chunks, stand firm). Bounties are paid, anyone grabbed is freed, and the next wave holds back."""
        if self.boiler < 1.0:
            return False
        self.boiler, self.steam = 0.0, 0.0
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
        interval = phantom_interval(self.lv("phantom"))
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
                else:
                    self.hit_enemy(e, self.monster_hit_damage() * 3, heavy=True)
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
        unlocked = [u for u in UPGRADES if u["depth"] == self.depth]
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
        best, best_d = None, 1e9
        for cell, block in self.current.items():
            d = (cell[0] + 0.5 - miner.x) ** 2 + (cell[1] + 0.5 - miner.y) ** 2
            if cell in claimed:
                d += 6
            if seek_ore and is_ore(block) and cell not in claimed:   # Treasure Map: unclaimed ore first
                d -= 1000
            if self.golden and self.golden[0] == cell:   # leave the golden block for the player
                d += 5000
            d += random.random() * 0.3
            if d < best_d:
                best, best_d = cell, d
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
                demo.task_timer = demo_interval(self.lv("demolition")) / level_mult(demo.level)
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
        if m.task != "skirmish":
            m.task, m.task_timer = "skirmish", random.uniform(*ROCK_EVERY)
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
                self.golden_timer = golden_interval(self.lv("goldblock"))
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
                    self.ballista_timer = ballista_interval(self.lv("ballista"))
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
    def update(self, dt, combat=True):
        """Advance the simulation. With combat=False enemies freeze and none spawn."""
        self.clock += dt
        if self.collapse is not None:   # The Void Maw has fallen: the shaft comes down
            self.collapse -= dt
            self.shake, self.shake_power = 0.2, 3 + 5 * (1 - max(0.0, self.collapse) / COLLAPSE_DELAY)
            if self.collapse <= 0:
                self.collapse, self.camp_ready = None, True
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
            if self.coffee_timer >= coffee_interval(self.lv("coffee")):
                self.coffee_timer = 0.0
                self.coffee_break()
        speed = walk_speed(self.lv("boots")) * self.art_mult("walk")
        swing = self.miner_swing_time()
        regen = miner_regen(self.lv("firstaid")) * self.art_mult("regen")
        boss = self.foreman()
        boss_here = boss if boss and boss.state == "working" else None
        holdout = None if self.current else self.boss_target()   # layer cleared, boss still standing
        shades = [e for e in self.enemies if e.spec.get("aura") and e.targetable]   # (Abyssal Shades)
        for m in self.miners + self.ghosts:   # (ghosts dig with the rest)
            if m.state == "down":
                m.respawn -= dt
                if m.respawn <= 0:
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
            if m.stun > 0:   # reeling from the Fanged Behemoth's screech
                m.stun = max(0.0, m.stun - dt)
                m.anim = 0.0
                continue
            if not m.digs:   # specialists with their own jobs
                {"foreman": self.update_foreman, "guard": self.update_guard, "medic": self.update_medic,
                 "demolitionist": self.update_demolitionist}[m.role](m, dt, mspeed * ROLES[m.role]["speed"])
                m.draw_z += (self.column_height(*self.cell_of(m.x, m.y)) - m.draw_z) * min(1.0, dt * 10)
                continue
            m.sharp = max(0.0, m.sharp - dt)
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
        if combat:
            for e in self.enemies:
                self.ward(e)
            for e in [e for e in self.enemies if e.kind == "slimeling"]:
                self.shrivel(e, dt)
            for e in [e for e in self.enemies if e.kind == "shade"]:
                self.flare_burn(e, dt)
            self.boss_auras()
            for e in list(self.enemies):
                e.update(self, dt)
            # waves keep coming while enemies remain (but a boss fight is just the boss and its own monsters)
            if self.depth >= ENEMY_START_DEPTH and not self.boss():
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
            if self.dynamite_timer >= dynamite_interval(self.lv("dynamite")):
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
                    camp_ready=self.camp_ready or self.collapse is not None)

    @classmethod
    def from_dict(cls, d):
        w = cls()
        w.gold = d["gold"]
        w.depth = d["depth"]
        w.expedition = d.get("expedition", 0)
        w.camp = [k for k in d.get("camp", []) if k in CAMP]
        w.lifetime.update(d.get("lifetime", {}))
        w.camp_ready = d.get("camp_ready", False)
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
        renamed = {"idol": "medal", "goldtooth": "broclaw"}   # (retired: the Cursed Idol, the Hoard's Golden Tooth)
        w.artifacts = [k for k in (renamed.get(k, k) for k in d.get("artifacts", [])) if k in ARTIFACTS]
        w.refresh_artifacts()   # (with the camp's buildings and the expedition's toughness)
        w.boss_done = d.get("boss_done", w.depth if boss_for(w.depth) else -1)   # older saves: no boss mid-layer
        if d.get("grid", 8) == GRID:
            # (older saves have no chest / artifact / bones flags: [x, y, kind, hp])
            # (each block's hp was saved; its toughness and worth come from the expedition)
            w.current = w.toughen({(x, y): Block(k, w.depth, hp, *rest) for x, y, k, hp, *rest in d["current"]},
                                  keep_hp=True)
            w.next = w.toughen({(x, y): Block(k, w.depth + 1, hp, *rest) for x, y, k, hp, *rest in d["next"]},
                               keep_hp=True)
        else:   # saved on a different board size: start the current layer fresh
            w.current = w.new_layer(w.depth)
            prospector = w.lv("prospector")
            w.next = w.new_layer(w.depth + 1, ore_mult(prospector), richness=ore_richness(prospector))
        w.layer_value = d.get("layer_value") or layer_value(w.current)   # older saves: what's left of it
        if not w.current and not (boss_for(w.depth) and w.boss_done < w.depth):   # (a boss still bars the way)
            w.descend(award=False)
        w.miners = []
        w.sync_miners()
        saved_crew = d.get("crew", [])   # older saves have no crew: keep random looks
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

        return w
