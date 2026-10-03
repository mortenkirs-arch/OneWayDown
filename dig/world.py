"""Game simulation: the dig site, miners, mining rules and save data."""
import math
import random
import time

from .blocks import BLOCKS, Block, generate_layer, layer_value
from .config import BAD, GOLD, GOLD_HUD_COIN, GOOD, GRID, TEXT, W
from .dynamite import EXPLOSION_SECS, Bomb
from .effects import (CRIT_BURST_SECS, QUAKE_RADIUS, QUAKE_SECS, QUAKE_SPEED, CoinFly, Floater, Particle,
                      Smoke)
from .enemies import (ENEMY_START_DEPTH, ENEMY_TYPES, Enemy, choose_kind, edge_cells, max_enemies,
                      spawn_interval)
from .iso import iso
from .world_layout import BALLISTA_POS, BOLT_SECS, CHEST_FX_SECS, SPIKE_FX_SECS, WHETSTONE_POS
from .miners import CRIT_ANIM_SECS, ROLES, Miner, base_name, new_stats, numbered_name
from .sprites import bomb_fuse_tip, enemy_anchor
from .upgrades import (BRANCHES, UPGRADES, ballista_interval, ballista_share, chest_chance, clear_share,
                       combo_step, golden_interval, golden_payout, milestone_mult, slam_mult, streak_bonus,
                       trap_share, vault_rate, vein_share, whetstone_boost, wisp_slow,
                       bounty_mult, click_damage, depth_reached, dynamite_interval,
                       enemy_hit_floor, is_maxed, is_unlocked, masterwork_mult, midas_mult, miner_count, miner_damage,
                       miner_max_hp, miner_regen, miner_strike, monster_damage, ore_damage_mult, ore_mult,
                       demo_interval, respawn_secs, second_wind_boost, swing_time, upgrade_cost, value_mult,
                       walk_speed)
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
GUARD_SHARE = 0.14           # each blow takes this share of a monster's max health (~5s to fell one alone)
GUARD_RUSH = 1.4             # guards break into a run when there's a monster to fight
GUARD_REACH = 0.45           # how close a guard gets before swinging
CHARGE_SPLASH_SHARE = 0.35   # a demolitionist's charge destroys its target and takes this share
CHARGE_SPLASH_PER_LV = 0.05  # (+ this per level) of max health off the blocks around it
MAX_FLYING_COINS = 40
MILESTONE_EVERY = 5          # every 5th metre is a milestone with a bigger clear bonus (see Surveyor's Contract)
STREAK_CAP = 10              # Hot Streak: up to this many hits in a row count
COMBO_WINDOW = 0.9           # Combo Clicks: seconds you can pause between clicks before it drops
COMBO_CAP = 20               # ...and the most clicks that count
GOLDEN_SECS = 6.0            # Golden Blocks: how long a golden block lasts
CHEST_PAYOUT = 15            # Buried Treasure: chest worth this many times its block's value
VAULT_PERIOD = 60.0          # Gold Vault: interest is paid this often (seconds)
WHET_SHARPEN_SECS = 1.5      # time spent at the wheel
WHET_SHARP_SECS = 20.0       # how long a sharpened pick stays sharp
WHET_GAP = 3.0               # seconds between sending miners to the wheel
LANTERN_RADIUS = 2.5         # Spirit Lantern: wisps this close to the crew are slowed
SAVE_VERSION = 2         # bump when the save format changes meaning (see from_dict migrations)
   # cap on coins in the air at once (late game breaks blocks very fast)


class _Spot:
    """A bare position, for effects at a fixed spot on the board."""

    def __init__(self, x, y, z):
        self.x, self.y, self.draw_z = x, y, z


def is_ore(block):
    return BLOCKS[block.kind]["ore"] is not None


class World:
    def __init__(self):
        self.gold = 0.0
        self.depth = 0                     # depth index of the current (top) layer
        self.levels = {u["key"]: 0 for u in UPGRADES}
        self.total_blocks = 0
        self.current = generate_layer(0)
        self.next = generate_layer(1)
        self.layer_value = layer_value(self.current)   # base value of the layer being dug (for its clear bonus)
        self.clock = 0.0                   # game-time seconds; stands still while paused
        self.graveyard = []                # records of every miner who has died (see bury())
        self.miners = []
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
        self.in_vein = False                                    # Vein Follower: chain guard
        self.bombs = []                                         # dynamite in flight / on a lit fuse
        self.explosions = []                                    # [x, y, age, size_px] fireballs
        self.smoke = []
        self.shake = 0.0                                        # screen-shake seconds left
        self.shake_power = 0.0                                  # max shake offset in px
        self.flash = 0.0                                        # white flash seconds left
        self.coins = []                                         # earned coins flying to the HUD counter
        self.crit_bursts = []                                   # [x, y, age] critical-strike impact flashes
        self.quakes = []                                        # [x, y, age, cells dusted] Seismic Strike waves
        self.gold_bump = 0.0                                    # HUD counter pulse when coins land
        self.notice = None                                      # [text, seconds left] milestone banner
        self.combo = 0                                          # Combo Clicks: clicks in a row...
        self.combo_timer = 0.0                                  # ...and time left before it drops
        self.golden = None                                      # Golden Blocks: [cell, seconds left]
        self.golden_timer = 20.0                                # seconds until the next golden block
        self.vault_timer = 0.0                                  # Gold Vault: seconds towards the next payout
        self.whet_timer = 4.0                                   # Whetstone: seconds until the next miner goes
        self.ballista_timer = 2.0                               # Ballista: seconds until the next bolt
        self.ballista_aim = 0.0                                 # direction the ballista is pointing (radians)
        self.bolts = []                                         # [start (x, y), enemy, age] in flight
        self.chest_fx = []                                      # [x, y, age] treasure chests bursting open
        self.spike_fx = []                                      # [cell, age] Booby Traps springing
        self.new_unlocks = set()                                # upgrades opened up by depth, not yet looked at

    # ----- stats ----------------------------------------------------------
    def lv(self, key): return self.levels[key]

    def crew_size(self):
        """How many diggers (the foreman is extra)."""
        return miner_count(self.lv("miners")) + self.lv("nightshift")

    def workers(self):
        """Everyone the foreman supervises (the whole crew apart from the foreman)."""
        return [m for m in self.miners if not m.is_foreman]

    def diggers(self):
        """Crew who mine blocks: miners and drillers."""
        return [m for m in self.miners if m.digs]

    def wanted_crew(self):
        """How many of each role the upgrades call for."""
        return {"miner": self.crew_size(), "driller": self.lv("driller"), "guard": self.lv("guard"),
                "demolitionist": 1 if self.lv("demolition") else 0, "foreman": 1 if self.lv("foreman") else 0}

    def foreman(self):
        """The foreman on site and alive, or None (their bonuses only apply while they are)."""
        return next((m for m in self.miners if m.is_foreman and m.state != "down"), None)

    def miner_hit_damage(self):
        """Miner damage to blocks (before the Diamond Tips bonus on ore)."""
        team = 1 + 0.03 * self.lv("teamwork") * len(self.diggers())
        return miner_damage(self.lv("power")) * team * masterwork_mult(self.lv("masterwork"))

    def miner_swing_time(self):
        t = swing_time(self.lv("speed"))
        if self.foreman():   # Foreman's crew-wide bonus only while the foreman is alive
            t *= 0.9 ** self.lv("foreman")
        if self.second_wind > 0:
            t /= 1 + second_wind_boost(self.lv("secondwind"))
        return max(0.1, t)

    def click_hit_damage(self):
        """Your click damage to blocks."""
        return click_damage(self.lv("click"))

    def monster_hit_damage(self):
        """Your click damage to monsters (Combat menu), before the Executioner minimum."""
        return monster_damage(self.lv("slayer"))

    def fly_coins(self, x, y, count):
        """Send little coins arcing from (x, y) up into the HUD gold counter."""
        room = MAX_FLYING_COINS - len(self.coins)
        for i in range(min(count, room)):
            self.coins.append(CoinFly((x, y), GOLD_HUD_COIN, delay=i * 0.06))

    def earn(self, amount):
        """Add gold from any source (Midas Touch applies to all of it). Returns the amount added."""
        amount *= midas_mult(self.lv("midas"))
        self.gold += amount
        self.earn_log.append((self.clock, amount))
        return amount

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

    def max_hp_for(self, role):
        return miner_max_hp(self.lv("hardhats")) * ROLES[role]["hp"]

    def recruit(self, role="miner"):
        """A brand-new miner. Shares a fallen miner's name? They become 'Gus II', 'Gus III', ..."""
        miner = Miner(taken_names={base_name(m.name) for m in self.miners}, role=role)
        fallen = sum(1 for g in self.graveyard if base_name(g["name"]) == miner.name)
        if fallen:
            miner.name = numbered_name(miner.name, fallen)
        miner.max_hp = miner.hp = self.max_hp_for(role)
        miner.stats = new_stats(self.depth, self.clock)
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
        for i, cell in enumerate(edge_cells(count)):
            # stagger the emergence so a big wave pops out one after another
            enemy = Enemy(kinds[i], self.depth, cell, self.column_height(*cell), delay=i * 0.35)
            self.enemies.append(enemy)
        if count == 1:
            spec = ENEMY_TYPES[kinds[0]]
            msg = f"A {spec['name'].upper()} {spec['arrival'].upper()}!"
        else:
            msg = f"WAVE INCOMING: {count} ENEMIES!"
        self.announcement = [msg, 2.5]   # shown as the HUD banner title
        return count

    def spring_trap(self, enemy):
        """Booby Traps: spikes punch up into a monster arriving on the ground."""
        if not self.lv("traps") or enemy not in self.enemies:
            return
        self.spike_fx.append([self.cell_of(enemy.x, enemy.y), 0.0])
        self.hit_enemy(enemy, enemy.max_hp * trap_share(self.lv("traps")), floor=False, ring=(200, 200, 210))

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
        miner.state = "grabbed"
        miner.attacker = enemy
        px, py = self.entity_screen(miner, 60)
        self.floaters.append(Floater(f"{miner.name}: HELP!", px, py, BAD, life=1.2, size=26))

    def miner_down(self, miner, killer=None):
        """Death is permanent: the miner is buried, and a new recruit arrives when the timer runs out."""
        miner.state = "down"
        miner.respawn = respawn_secs(self.lv("firstaid"))
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
            "died_depth": self.depth,
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
        return max(dmg, enemy.max_hp * enemy_hit_floor(self.lv("executioner")))

    def hit_enemy(self, enemy, dmg, floor=True, ring=BAD, by=None):
        """Apply damage to an enemy. `floor` applies the player's Executioner minimum.
        `by` is the miner landing the hit (None = you / your dynamite), credited with the kill."""
        if enemy not in self.enemies:
            return
        enemy.hp -= self.enemy_hit_damage(enemy, dmg) if floor else dmg
        enemy.flash = 0.12
        px, py = enemy_anchor(enemy, self.rise, time.time())
        self.rings.append([px, py + 18, 0.0, 30, ring])
        for _ in range(6):
            self.particles.append(Particle(px, py, enemy.spec["gore"]))
        if enemy.hp <= 0:
            self.kill_enemy(enemy, by)

    def player_hit_enemy(self, enemy):
        """You click a monster: Monster Slayer damage, Critical Smite, then Cleave onto neighbours."""
        dmg = self.monster_hit_damage() * self.combo_mult()
        if random.random() < 0.05 * self.lv("smite"):
            dmg *= 3
            px, py = enemy_anchor(enemy, self.rise, time.time())
            self.floaters.append(Floater("SMITE!", px, py - 30, (255, 120, 120), life=0.7, size=24))
        dealt = self.enemy_hit_damage(enemy, dmg)
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
            share *= 1 + self.lv("laststand")
        miner.anim = 1.0
        self.hit_enemy(enemy, enemy.max_hp * share, floor=False, ring=miner.shirt, by=miner)

    def kill_enemy(self, enemy, by=None):
        self.enemies.remove(enemy)
        bounty = self.earn(enemy.bounty_base * value_mult(self.lv("value")) * bounty_mult(self.lv("bounty")))
        if by:   # a miner fought it off themselves
            by.stats["monsters"] += 1
            by.stats["gold"] += bounty
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
            if by is victim:
                self.floaters.append(Floater("Fought it off!", vx, vy, GOOD, life=1.3, size=26))
            else:
                victim.stats["saved"] += 1
                self.floaters.append(Floater("Saved!", vx, vy, GOOD, life=1.3, size=28))

    # ----- upgrades -------------------------------------------------------
    def available(self, up):
        """Prerequisites owned and depth milestone reached."""
        return is_unlocked(up, self.levels) and depth_reached(up, self.depth)

    def can_buy(self, up):
        return self.available(up) and not is_maxed(up, self.levels) and self.gold >= self.cost(up)

    def cost(self, up):
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
        block.hp -= dmg
        px, py = self.cell_screen(cell)
        spec = BLOCKS[block.kind]
        for _ in range(sparks):
            self.particles.append(Particle(px, py, spec.get("fleck") or spec["color"]))
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
        dmg = self.miner_hit_damage() * self.pick_bonus(miner, cell, 1.0)
        if is_ore(block):
            dmg *= ore_damage_mult(self.lv("diamond"))
        crit = random.random() < 0.05 * self.lv("crit")
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
        """The look of a critical strike: the miner's overhead slam, an impact starburst, and with
        Seismic Strikes an earthquake wave rippling out across the board."""
        px, py = self.cell_screen(cell)
        if miner:
            miner.crit = CRIT_ANIM_SECS
        self.crit_bursts.append([px, py, 0.0])
        self.floaters.append(Floater("CRIT!", px, py - 78, (255, 150, 90), life=0.9, size=32))   # clear of the slam
        for _ in range(16):
            color = random.choice([(255, 230, 150), (255, 160, 70), (255, 255, 255)])
            self.particles.append(Particle(px, py, color, big=True))
        if self.lv("quake"):
            self.quakes.append([cell[0] + 0.5, cell[1] + 0.5, 0.0, set()])
            if self.shake < 0.15:   # a small jolt (dynamite's bigger shake wins if both happen)
                self.shake, self.shake_power = 0.15, 3

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
            self.floaters.append(Floater("CRIT!", px, py - 30, (220, 160, 255), life=0.7, size=22))
        if manual and self.lv("golden"):   # Golden Touch: your own clicks earn as you dig
            self.earn(block.value * value_mult(self.lv("value")) * 0.05 * self.lv("golden"))
            for _ in range(3):
                self.particles.append(Particle(px, py, GOLD))
        self.rings.append([px, py, 0.0, 26, ring_color])
        if self.damage(cell, dmg, sparks) and self.lv("shockwave"):
            self.splash(cell, dmg * 0.2 * self.lv("shockwave"), BRANCHES["hands"]["color"])

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
        jackpot = self.earn(block.value * value_mult(self.lv("value")) * golden_payout(self.lv("goldblock")))
        px, py = self.cell_screen(cell)
        self.floaters.append(Floater(f"JACKPOT! +{fmt(jackpot)}", px, py - 50, GOLD, life=2.2, size=36, coin=True))
        self.fly_coins(px, py, 14)
        self.rings.append([px, py, 0.0, 120, GOLD])
        for _ in range(24):
            self.particles.append(Particle(px, py, random.choice([GOLD, (255, 240, 170), (255, 255, 255)]), big=True))
        self.golden = None

    def slam(self, cell, charge):
        """Charged Slam: a huge hit on `cell` (charge 0..1) that shakes the blocks around it."""
        if cell not in self.current:
            return
        dmg = self.click_hit_damage() * slam_mult(self.lv("slam")) * (0.3 + 0.7 * charge)
        px, py = self.cell_screen(cell)
        self.crit_bursts.append([px, py, 0.0])
        self.quakes.append([cell[0] + 0.5, cell[1] + 0.5, 0.0, set()])
        self.shake, self.shake_power = 0.25, 4 + 4 * charge
        self.floaters.append(Floater("SLAM!", px, py - 70, (220, 160, 255), life=1.0, size=30 + int(14 * charge)))
        depth = self.depth
        around = [(cell[0] + dx, cell[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
        if not self.damage(cell, dmg, sparks=10):
            return
        for c in around:   # the shock rolls into the blocks around it at half strength
            if self.depth != depth:
                return
            self.damage(c, dmg * 0.5, sparks=2)

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
                    self.hit_enemy(e, e.max_hp * 0.25, floor=False, by=bomb.owner)
                else:
                    self.hit_enemy(e, self.monster_hit_damage() * 3)
        depth = self.depth
        if charge:   # target destroyed outright, neighbours cracked by a share of their health
            splash = CHARGE_SPLASH_SHARE + CHARGE_SPLASH_PER_LV * self.lv("demolition")
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    block = self.current.get((cx + dx, cy + dy))
                    if self.depth != depth:
                        return
                    if block:
                        share = 1.0 if (dx, dy) == (0, 0) else splash
                        self.damage((cx + dx, cy + dy), block.max_hp * share + 1e-9, sparks=2, by=bomb.owner)
            return
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if self.depth != depth:
                    return
                self.damage((cx + dx, cy + dy), dmg, sparks=2)

    def break_block(self, cell, block, by=None):
        del self.current[cell]
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
            self.particles.append(Particle(px, py, spec["color"], big=True))
            if spec.get("fleck"):
                self.particles.append(Particle(px, py, spec["fleck"], big=True))
        self.floaters.append(Floater(f"+{fmt(earned)}", px, py - 10, GOLD, coin=True))
        self.fly_coins(px, py, 2 if is_ore(block) else 1)
        for m in self.miners:
            if m.target == cell:
                m.target = None
        if by and by.digs and is_ore(block) and self.lv("vein") and not self.in_vein:
            self.follow_vein(cell, block.kind, by)
        if not self.current:
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
                    self.damage(n, block.max_hp * vein_share(self.lv("vein")), sparks=4, by=miner)
        finally:
            self.in_vein = False

    def descend(self, award=True):
        if award:
            self.layer_clear_bonus(self.depth + 1)
        self.depth += 1
        self.current = self.next
        self.layer_value = layer_value(self.current)
        self.next = generate_layer(self.depth + 1, ore_mult(self.lv("prospector")),
                                   chest_chance(self.lv("chests")))
        self.rise = -1.0
        for m in self.miners:
            m.draw_z += 1
            m.target = None
        for e in self.enemies:
            e.draw_z += 1
        self.floaters.append(Floater(f"Depth {self.depth}m", W / 2, 120, TEXT, life=2.0, size=40))
        unlocked = [u for u in UPGRADES if u["depth"] == self.depth]
        if unlocked:   # depth milestone: new upgrades open up
            self.new_unlocks.update(u["key"] for u in unlocked)
            names = ", ".join(u["name"] for u in unlocked)
            self.notice = [f"{self.depth}m reached - new upgrades: {names}", 5.0]
        if self.depth == ENEMY_START_DEPTH:   # first time this deep: the monsters find you, right away
            self.enemy_timer = 0.0
        if self.lv("secondwind"):
            self.second_wind = SECOND_WIND_SECS
            self.floaters.append(Floater("Second wind!", W / 2, 160, BRANCHES["crew"]["color"], life=1.6, size=28))

    def layer_clear_bonus(self, new_depth):
        """Gold for clearing a layer: a share of everything it held, doubled on every 5th metre."""
        milestone = new_depth % MILESTONE_EVERY == 0
        surveyor = self.lv("surveyor")
        share = clear_share(surveyor) * (milestone_mult(surveyor) if milestone else 1)
        bonus = self.earn(self.layer_value * value_mult(self.lv("value")) * share)
        title = f"{new_depth}m MILESTONE!" if milestone else "LAYER CLEAR!"
        self.floaters.append(Floater(f"{title} +{fmt(bonus)}", W / 2, 168, GOLD, life=2.6,
                                     size=40 if milestone else 34, coin=True))
        self.fly_coins(W / 2, 168, 16 if milestone else 10)
        self.rings.append([W / 2, 176, 0.0, 160 if milestone else 110, GOLD])

    def pick_target(self, miner):
        if not self.current:
            return None
        claimed = {m.target for m in self.miners if m is not miner and m.target}
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
        dmg = self.miner_hit_damage() * DRILL_SHARE * self.pick_bonus(driller, cell, 1 / DRILL_HITS_PER_SWING)
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

    def guard_strike(self, guard, enemy):
        if not enemy or enemy not in self.enemies or not enemy.targetable:
            return
        guard.anim = 1.0
        self.hit_enemy(enemy, enemy.max_hp * GUARD_SHARE, floor=False, ring=(120, 150, 220), by=guard)

    def update_demolitionist(self, demo, dt, speed):
        """Every so often: pick the toughest block, walk over, plant a charge, run for cover."""
        demo.anim = max(0.0, demo.anim - dt * 2)
        if demo.task == "idle":
            demo.task_timer -= dt
            if demo.task_timer <= 0 and self.current:
                toughness = lambda c: self.current[c].hp * (1.5 if is_ore(self.current[c]) else 1)
                demo.task, demo.charge_cell = "walking", max(self.current, key=toughness)
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
                demo.task, demo.task_timer = "taking cover", demo_interval(self.lv("demolition"))
        elif demo.task == "taking cover":
            if self.walk_to(demo, *demo.goal, speed * 1.3, dt):
                demo.task, demo.goal = "idle", None

    # ----- middle-path upgrade systems -----------------------------------------
    def ward(self, enemy):
        """Spirit Lantern: ghosts can't phase out, wisps near the crew are slowed."""
        lv = self.lv("spiritlantern")
        enemy.warded = lv > 0
        enemy.speed_mult = 1.0
        if lv and enemy.kind == "wisp":
            if any(math.hypot(m.x - enemy.x, m.y - enemy.y) <= LANTERN_RADIUS
                   for m in self.miners if m.state != "down"):
                enemy.speed_mult = 1 - wisp_slow(lv)

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
        # Combo Clicks: drops if you stop clicking
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
        for bolt in self.bolts:
            bolt[2] += dt
            if bolt[2] >= BOLT_SECS:
                enemy = bolt[1]
                if enemy in self.enemies and enemy.targetable:
                    self.hit_enemy(enemy, enemy.max_hp * ballista_share(self.lv("ballista")), floor=False,
                                   ring=(220, 190, 130))
        self.bolts = [b for b in self.bolts if b[2] < BOLT_SECS]
        for fx in self.chest_fx:
            fx[2] += dt
        self.chest_fx = [fx for fx in self.chest_fx if fx[2] < CHEST_FX_SECS]
        for fx in self.spike_fx:
            fx[1] += dt
        self.spike_fx = [fx for fx in self.spike_fx if fx[1] < SPIKE_FX_SECS]

    def ballista_screen(self):
        """Where bolts leave the ballista on screen."""
        bx, by = BALLISTA_POS
        x, y = iso(bx, by, self.column_height(*self.cell_of(bx, by)) + self.rise)
        return x, y - 18

    # ----- update ---------------------------------------------------------
    def update(self, dt, combat=True):
        """Advance the simulation. With combat=False enemies freeze and none spawn."""
        self.clock += dt
        self.sync_miners()
        if self.rise < 0:
            self.rise = min(0.0, self.rise + dt * 2.5)
        self.second_wind = max(0.0, self.second_wind - dt)
        speed = walk_speed(self.lv("boots"))
        swing = self.miner_swing_time()
        regen = miner_regen(self.lv("firstaid"))
        boss = self.foreman()
        boss_here = boss if boss and boss.state == "working" else None
        for m in self.miners:
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
                elif combat and self.lv("defense"):   # Self Defense: swing at the attacker
                    m.swing -= dt
                    if m.swing <= 0:
                        m.swing += swing
                        self.miner_strike(m)
                continue
            m.hp = min(m.max_hp, m.hp + regen * dt)
            if not m.digs:   # specialists with their own jobs
                {"foreman": self.update_foreman, "guard": self.update_guard,
                 "demolitionist": self.update_demolitionist}[m.role](m, dt, speed * ROLES[m.role]["speed"])
                m.draw_z += (self.column_height(*self.cell_of(m.x, m.y)) - m.draw_z) * min(1.0, dt * 10)
                continue
            m.sharp = max(0.0, m.sharp - dt)
            if m.task in ("whetstone", "sharpening"):   # off to the sharpening wheel
                self.update_whetstone_trip(m, dt, speed)
                m.draw_z += (self.column_height(*self.cell_of(m.x, m.y)) - m.draw_z) * min(1.0, dt * 10)
                continue
            my_swing = swing   # pep talk: miners near the foreman swing faster still
            if boss_here and math.hypot(m.x - boss_here.x, m.y - boss_here.y) <= PEP_TALK_RADIUS:
                my_swing = swing / PEP_TALK_BOOST
            if m.target is None or m.target not in self.current:
                m.target = self.pick_target(m)
            m.anim = max(0.0, m.anim - dt * 4)
            m.crit = max(0.0, m.crit - dt)
            if m.target:
                tx, ty = m.target[0] + 0.5, m.target[1] + 0.5
                dx, dy = tx - m.x, ty - m.y
                dist = math.hypot(dx, dy)
                if dist > 0.05:
                    step = min(dist, speed * ROLES[m.role]["speed"] * dt)
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
        self.update_upgrade_systems(dt, combat)
        if combat:
            for e in list(self.enemies):
                self.ward(e)
                e.update(self, dt)
            if self.depth >= ENEMY_START_DEPTH:   # waves keep coming even while enemies remain
                self.enemy_timer -= dt
                if self.enemy_timer <= 0:
                    self.enemy_timer = spawn_interval(self.depth)
                    self.spawn_wave()

        if self.lv("autotap"):
            self.tap_timer += dt * self.lv("autotap")
            while self.tap_timer >= 1 and self.current:
                self.tap_timer -= 1
                self.player_hit(random.choice(list(self.current)), sparks=3,
                                ring_color=BRANCHES["hands"]["color"])
        if self.lv("dynamite"):
            self.dynamite_timer += dt
            if self.dynamite_timer >= dynamite_interval(self.lv("dynamite")):
                self.dynamite_timer = 0.0
                self.throw_dynamite()
        for bomb in list(self.bombs):
            bomb.age += dt
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
                    if front <= QUAKE_RADIUS:
                        px, py = self.cell_screen(cell)
                        for _ in range(2):
                            self.particles.append(Particle(px, py, random.choice([(150, 120, 90), (110, 88, 66)])))
        self.quakes = [q for q in self.quakes if q[2] < QUAKE_SECS]
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
        pack = lambda layer: [[x, y, b.kind, b.hp, b.chest] for (x, y), b in layer.items()]
        return dict(gold=self.gold, depth=self.depth, levels=self.levels,
                    total_blocks=self.total_blocks, current=pack(self.current),
                    next=pack(self.next), saved_at=time.time(), gps=self.gold_per_sec(),
                    version=SAVE_VERSION, layer_value=self.layer_value,
                    crew=[m.to_dict() for m in self.miners], graveyard=self.graveyard,
                    clock=self.clock, grid=GRID)

    @classmethod
    def from_dict(cls, d):
        w = cls()
        w.gold = d["gold"]
        w.depth = d["depth"]
        w.levels.update({k: v for k, v in d["levels"].items() if k in w.levels})
        if d.get("version", 1) < 2:   # v1: Hire Miner level 0 meant one miner; now it means none
            w.levels["miners"] += 1
        w.total_blocks = d.get("total_blocks", 0)
        w.clock = d.get("clock", 0.0)
        w.graveyard = d.get("graveyard", [])
        if d.get("grid", 8) == GRID:
            # (older saves have no chest flag: [x, y, kind, hp])
            w.current = {(x, y): Block(k, w.depth, hp, *rest) for x, y, k, hp, *rest in d["current"]}
            w.next = {(x, y): Block(k, w.depth + 1, hp, *rest) for x, y, k, hp, *rest in d["next"]}
        else:   # saved on a different board size: start the current layer fresh
            w.current = generate_layer(w.depth)
            w.next = generate_layer(w.depth + 1, ore_mult(w.lv("prospector")))
        w.layer_value = d.get("layer_value") or layer_value(w.current)   # older saves: what's left of it
        if not w.current:
            w.descend(award=False)
        w.miners = []
        w.sync_miners()
        saved_crew = d.get("crew", [])   # older saves have no crew: keep random looks
        for role in ROLES:   # match by role: specialists can sit anywhere in the list
            ours = [m for m in w.miners if m.role == role]
            theirs = [c for c in saved_crew if c.get("role", "miner") == role]
            for miner, data in zip(ours, theirs):
                miner.apply_saved(data)
        w.gps_cached = d.get("gps", 0.0)
        w.enemy_timer = spawn_interval(w.depth)   # first wave on the saved depth's schedule, not depth 1's

        return w
