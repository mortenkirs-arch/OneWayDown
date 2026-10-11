"""Enemies that invade the dig site and attack miners.

Enemies only act while the player is on the dig site (see Scene.combat), so nothing
can kill the crew while you are browsing menus.

Each enemy type is data in ENEMY_TYPES:
  hp, bounty    base values, scaled by depth when the enemy appears
  speed, dps    tiles/s, and damage per second to a grabbed miner near the surface (MINER_MAX_HP = 10);
                past GRIP_FROM metres it grows with a typical crew member's health (crew_hp_at)
  min_depth     shallowest depth it can spawn at; weight = relative spawn chance (0 = never spawns directly)
  reach         how close it must get to grab a miner
  entrance      spawn animation: "dig" (claws out of the ground), "drop" (silk thread), "swoop" (flies in),
                "fade" (materialises out of cold mist)
  grab          "side" (stands beside the miner), "head" (rides the head), "neck" (latches onto the neck),
                "orbit" (circles the miner's head), "engulf" (wraps around the whole miner)
  arrival       wording for the wave banner
  altitude      blocks above the ground it floats at (0 / missing = walks)
  wobble        dict(amount, freq): zig-zag while flying towards a target
  phase         dict(every, duration): turns intangible (unclickable) for `duration` of every `every`
                seconds while hunting
  lifesteal     fraction of its own max hp healed by draining a whole miner
  transform     dict(into, min_depth, after): turns into another enemy after flying `after` seconds
  split         dict(into, count): at half health it bursts into `count` smaller `into` (slimes)
  lurk          (Mimic) it turns up sitting on a block, disguised as a treasure chest, until the block is hit,
                it is hit, or LURK_SECS pass - then it springs, biting whoever was digging there
  armour        (Rock Golem) stone armour: every hit lands at GOLEM_ARMOUR until a heavy one (a Charged Slam,
                dynamite, a demolitionist's charge) cracks it for good
  burrow        (Burrower) it tunnels in unseen - a moving mound of earth - and bursts up under a miner to grab
                them; any hit on the mound digs it out first
  aura          (Abyssal Shade) never grabs: it drifts to where the crew are thickest, and crew within
                SHADE_RADIUS swing SHADE_SLOW times slower and take SHADE_DPS damage a second
  slam, slam_radius   (non-bosses: Slime King chunks) it winds up and slams like a boss, only smaller
  pct_scale     how much "share of max health" damage lands on it (default: all of it; see Enemy.pct_scale)
  tint          colour a grabbed miner's face fades towards
  gore          colour of the particles when it is hit

Bosses (boss=True) never grab: they stalk the crew, wind up and slam the ground around them, and
call in minions. Extra keys:
  scale         how much bigger it is drawn than its sprite (see boss_sprites.py)
  look          (Zombie King) draw it with this regular enemy's sprite, scaled up and crowned
  slam          damage to every crew member in reach when the slam lands, as a share of a typical crew
                member's health at the boss's depth (crew_hp_at): so slams keep pace with Hard Hats
  minion        dict(kind, count, every): summoned around the boss every `every` seconds (and `plus`: one of
                those alongside them)
  dive          (flying bosses) instead of walking up and slamming, it marks a crew member's spot and
                swoops onto it when the wind-up ends
Each boss also has a trick of its own, run by World.boss_special (see the BOSS TRICKS constants below):
  Zombie King   rallies nearby zombies (faster, tougher) and goes into a rage below half health
  Broodmother   her slams leave webs that slow the crew; she lays egg sacs that hatch into spiders
  Vampire Lord  turns into a swarm of bats, flies to a crew member and bites them to heal
  Fanged Behemoth  dive-bombs a crew member from the air instead of slamming, and screeches to stun the crew
  Bone Tyrant   after each slam it strides off and hurls a volley of bones at the crew, then marches back in;
                its first "death" leaves a bone pile you must smash quickly
  Slime King    at half health it bursts into chunks that each creep up and slam; beat them all to win
  Archlich      curses a crew member (click them to lift it before it explodes); his wisps shield him
  Burrow Brothers  two giant burrowers sharing one health bar: one fights while the other tunnels under the
                crew as a mound, then they swap - the mound bursting up in a slam. Only the one above takes hits
  The Mountain  stone plates only heavy hits knock off (until then blows barely land); its stomps heave up blocks
  The Void Maw  only a blow to its one open eye lands properly; pools of darkness spread under the crew and eat
                at them (click a pool away), and every so often it inhales, dragging the crew in to bite them
                (strike the open eye to choke it)

...and a second trick (World.boss_second_trick, every so often): the Zombie King's hands burst up under the crew
and hold them; the Broodmother lashes silk at the furthest and reels them in; the Fanged Behemoth's wingbeat blows
the crew back; the Bone Tyrant cages one in ribs (click them free); the Slime King belly-flops onto a marked spot;
the Vampire Lord mesmerises one (a click snaps them out); the Archlich raises skeletons; the Burrow Brothers open
sinkholes; The Mountain brings down a rockslide; The Void Maw's eye fixes its gaze on one (strike the eye).

Egg sacs (hatch=...) don't move: they hatch into `count` of `kind` after `after` seconds unless broken.
entrance="none" means the enemy is simply there, with no spawn-in animation.
"""
import math
import random

from .blocks import hp_scale, value_scale
from .config import GRID
from .miners import MINER_MAX_HP

ENEMY_TYPES = {
    "zombie": dict(name="Zombie", hp=14, speed=0.55, dps=1.3, bounty=12, min_depth=1, weight=3,
                   reach=0.3, entrance="dig", grab="side", arrival="crawls out",
                   tint=(150, 130, 210), gore=(120, 190, 80)),
    "spider": dict(name="Cave Spider", hp=7, speed=1.5, dps=2.4, bounty=8, min_depth=6, weight=2,
                   reach=0.25, entrance="drop", grab="head", arrival="drops in",
                   tint=(150, 200, 120), gore=(90, 60, 120)),
    "bat": dict(name="Bat", hp=5, speed=1.9, dps=1.5, bounty=6, min_depth=3, weight=2,
                reach=0.3, entrance="swoop", grab="neck", arrival="swoops in",
                altitude=1.1, wobble=dict(amount=0.9, freq=6),
                transform=dict(into="vampire", min_depth=16, after=3.0),
                tint=(228, 228, 238), gore=(70, 50, 80)),
    "vampire": dict(name="Vampire", hp=28, speed=0.9, dps=2.0, bounty=26, min_depth=16, weight=0,
                    reach=0.3, entrance="dig", grab="side", arrival="rises", lifesteal=0.5,
                    tint=(228, 228, 238), gore=(160, 30, 45)),
    "skeleton": dict(name="Skeleton", hp=12, speed=0.75, dps=1.5, bounty=11, min_depth=9, weight=3,
                     reach=0.3, entrance="dig", grab="side", arrival="rattles out",
                     tint=(200, 200, 220), gore=(232, 226, 205)),
    "wisp": dict(name="Wisp", hp=5, speed=2.6, dps=1.0, bounty=8, min_depth=13, weight=2,
                 reach=0.3, entrance="fade", grab="orbit", arrival="flickers in",
                 altitude=0.8, wobble=dict(amount=1.3, freq=9),
                 tint=(170, 210, 255), gore=(150, 215, 255)),
    "slime": dict(name="Slime", hp=16, speed=0.5, dps=1.7, bounty=14, min_depth=34, weight=2,
                  reach=0.3, entrance="dig", grab="side", arrival="oozes up",
                  split=dict(into="slimeling", count=2),
                  tint=(160, 230, 130), gore=(120, 220, 90)),
    "slimeling": dict(name="Slimeling", hp=6, speed=0.8, dps=1.0, bounty=6, min_depth=0, weight=0,
                      reach=0.25, entrance="none", grab="side", arrival="",
                      tint=(160, 230, 130), gore=(120, 220, 90)),
    "ghost": dict(name="Ghost", hp=24, speed=0.45, dps=1.6, bounty=20, min_depth=19, weight=2,
                  reach=0.3, entrance="fade", grab="engulf", arrival="materialises",
                  altitude=0.35, wobble=dict(amount=0.35, freq=1.5), phase=dict(every=4.0, duration=1.2),
                  tint=(160, 190, 230), gore=(220, 230, 255)),

    # ----- bosses: one every BOSS_EVERY metres, in this order, then round again ----------------
    "zombieking": dict(name="Zombie King", hp=2200, speed=0.45, dps=0, bounty=360, min_depth=0, weight=0,
                       reach=0.9, entrance="dig", grab="side", arrival="rises", boss=True,
                       look="zombie", scale=2.2, slam=0.32, minion=dict(kind="zombie", count=2, every=14.0),
                       tint=(150, 130, 210), gore=(120, 190, 80)),
    "broodmother": dict(name="Broodmother", hp=2000, speed=0.8, dps=0, bounty=360, min_depth=0, weight=0,
                        reach=0.9, entrance="drop", grab="head", arrival="descends", boss=True,
                        scale=1.2, slam=0.25,
                        minion=dict(kind="eggsac", count=2, every=9.0, plus="spider"),
                        tint=(150, 200, 120), gore=(90, 60, 120)),
    "greatbat": dict(name="Fanged Behemoth", hp=2400, speed=1.0, dps=0, bounty=380, min_depth=0, weight=0,
                     reach=0.9, entrance="swoop", grab="neck", arrival="swoops in", boss=True, dive=True,
                     altitude=1.1, scale=1.2, slam=0.30,
                     minion=dict(kind="bat", count=3, every=11.0),
                     tint=(228, 228, 238), gore=(70, 50, 80)),
    "bonetyrant": dict(name="Bone Tyrant", hp=2400, speed=0.5, dps=0, bounty=400, min_depth=0, weight=0,
                       reach=0.9, entrance="dig", grab="side", arrival="rises", boss=True,
                       scale=1.1, slam=0.33, minion=dict(kind="skeleton", count=2, every=12.0),
                       tint=(200, 200, 220), gore=(232, 226, 205)),
    "slimeking": dict(name="Slime King", hp=3200, speed=0.5, dps=0, bounty=400, min_depth=0, weight=0,
                      reach=0.9, entrance="dig", grab="side", arrival="oozes up", boss=True,
                      scale=1.2, slam=0.30, split=dict(into="slimechunk", count=8),
                      pct_scale=0.025,
                      minion=dict(kind="slime", count=2, every=12.0),
                      tint=(160, 230, 130), gore=(120, 220, 90)),
    "slimechunk": dict(name="Slime Chunk", hp=160, speed=0.75, dps=0, bounty=18, min_depth=0, weight=0,
                       reach=0.6, entrance="none", grab="side", arrival="", slam=0.06, slam_radius=0.9, scale=1.4,
                       pct_scale=0.2, tint=(160, 230, 130), gore=(150, 220, 70)),
    "vampirelord": dict(name="Vampire Lord", hp=2800, speed=0.6, dps=0, bounty=400, min_depth=0, weight=0,
                        reach=0.9, entrance="dig", grab="side", arrival="awakens", boss=True, lifesteal=0.03,
                        scale=1.2, slam=0.28, minion=dict(kind="bat", count=2, every=12.0),
                        tint=(228, 228, 238), gore=(160, 30, 45)),
    "lich": dict(name="Archlich", hp=2600, speed=0.4, dps=0, bounty=420, min_depth=0, weight=0,
                 reach=0.9, entrance="fade", grab="engulf", arrival="materialises", boss=True,
                 altitude=0.35, wobble=dict(amount=0.2, freq=1.0),
                 scale=1.15, slam=0.33, minion=dict(kind="wisp", count=3, every=10.0),
                 tint=(160, 190, 230), gore=(200, 170, 255)),
    "burrower": dict(name="Burrower", hp=26, speed=0.8, dps=2.2, bounty=26, min_depth=45, weight=2,
                     reach=0.35, entrance="none", grab="side", arrival="tunnels in", burrow=True,
                     tint=(150, 110, 80), gore=(120, 90, 60)),
    # ----- the deep: 60m and below -------------------------------------------------------------------
    "mimic": dict(name="Mimic", hp=34, speed=0.9, dps=2.6, bounty=34, min_depth=60, weight=1.5,
                  reach=0.3, entrance="none", grab="side", arrival="lurks among the blocks", lurk=True,
                  tint=(200, 150, 90), gore=(150, 100, 60)),
    "golem": dict(name="Rock Golem", hp=70, speed=0.35, dps=2.8, bounty=55, min_depth=70, weight=1.5,
                  reach=0.35, entrance="dig", grab="side", arrival="heaves itself up", armour=True,
                  tint=(150, 150, 160), gore=(130, 128, 140)),
    "shade": dict(name="Abyssal Shade", hp=40, speed=0.5, dps=0, bounty=40, min_depth=85, weight=1.5,
                  reach=0.0, entrance="fade", grab="engulf", arrival="seeps in", aura=True,
                  altitude=0.5, wobble=dict(amount=0.3, freq=1.2),
                  tint=(60, 50, 90), gore=(40, 30, 70)),
    # ----- the deep's bosses -------------------------------------------------------------------------
    "burrowbros": dict(name="The Burrow Brothers", hp=3200, speed=0.55, dps=0, bounty=440, min_depth=0, weight=0,
                       reach=0.9, entrance="dig", grab="side", arrival="burst up out of the rock", boss=True,
                       scale=1.1, slam=0.30, minion=dict(kind="burrower", count=2, every=14.0),
                       tint=(150, 110, 80), gore=(120, 90, 60)),
    "mountain": dict(name="The Mountain", hp=3400, speed=0.35, dps=0, bounty=460, min_depth=0, weight=0,
                     reach=0.9, entrance="dig", grab="side", arrival="heaves itself up", boss=True,
                     scale=1.1, slam=0.36, plates=4, minion=dict(kind="golem", count=1, every=16.0),
                     tint=(150, 150, 160), gore=(130, 128, 140)),
    "voidmaw": dict(name="The Void Maw", hp=3600, speed=0.25, dps=0, bounty=500, min_depth=0, weight=0,
                    reach=0.9, entrance="fade", grab="engulf", arrival="rises out of the dark", boss=True,
                    scale=1.15, slam=0.36, minion=dict(kind="shade", count=1, every=15.0),
                    tint=(60, 50, 90), gore=(120, 80, 200)),
    "eggsac": dict(name="Egg Sac", hp=10, speed=0, dps=0, bounty=4, min_depth=0, weight=0,
                   reach=0, entrance="none", grab="head", arrival="", hatch=dict(kind="spider", count=2, after=6.0),
                   tint=(230, 230, 210), gore=(225, 225, 200)),
}
FLY_ALTITUDE = ENEMY_TYPES["bat"]["altitude"]   # bat swoop-in / transformation height

BOSSES = ["zombieking", "broodmother", "greatbat", "bonetyrant", "slimeking", "vampirelord", "lich",
          "burrowbros", "mountain", "voidmaw"]
BOSS_EVERY = 10              # a boss guards every 10th metre
BOSS_TIME_LIMIT = 150.0      # seconds before an unbeaten boss retreats (no reward, but the dig goes on)
BOSS_PCT_SCALE = 0.04        # bosses shrug off "share of max health" damage (Executioner, guards, ballista...)
BOSS_WINDUP = 1.3            # seconds of warning before a slam lands
BOSS_SLAM_RADIUS = 1.4       # tiles: crew this close to the boss when it slams get hit
BOSS_SLAM_COOLDOWN = 3.5     # seconds after a slam before it can wind up again
BOSS_MAX_MINIONS = 4         # it stops calling for help with this many minions alive (down to BOSS_CROWD_FROM)...
BOSS_CROWD_FROM = 20         # ...below which the cap grows a little - and each call brings a few more - up to...
BOSS_CROWD_CAP = 8           # ...this many by 40m. (Boss fights are only ever the boss and its own monsters.)
DIVE_SECS = 0.35             # a diving boss swoops onto its marked spot over the last moments of the wind-up

# ----- BOSS TRICKS ------------------------------------------------------------------------------
RALLY_RADIUS = 2.5           # Zombie King: zombies this close to him are rallied...
RALLY_SPEED = 1.6            # ...moving this much faster...
RALLY_TOUGH = 0.5            # ...and taking only this share of damage
ENRAGE_AT = 0.5              # below this share of his health he rages:
ENRAGE_PACE = 0.55           # wind-ups and cool-downs shrink to this share
WEB_SECS = 9.0               # Broodmother: webs left by her slam last this long...
WEB_SLOW = 0.35              # ...and crew crossing them move at this share of their speed
BAT_FORM_EVERY = 14.0        # Vampire Lord: seconds between turning into a swarm of bats
BAT_FORM_SPEED = 3.2         # tiles/s the swarm flies (nothing can hit it)
BITE_SECS = 3.5              # how long he feeds on the crew member he lands on...
BITE_SHARE = 0.08           # ...draining this share of a typical crew member's health a second...
BITE_HEAL = 0.012            # ...and healing this share of his max health a second
BITE_BREAK = 0.04            # taking this share of his max health while biting makes him let go
CURSE_EVERY = 9.0            # Archlich: seconds between curses
CURSE_SECS = 4.5             # a curse bursts this long after it lands, unless you click the crew member
CURSE_SHARE = 0.4           # damage to every crew member within CURSE_RADIUS when it bursts (share, as above)
CURSE_RADIUS = 1.5
SHIELD_PER_WISP = 0.25       # each wisp alive takes this share off the damage the Archlich takes...
SHIELD_MAX = 0.75            # ...up to this much
SCREECH_EVERY = 13.0         # Fanged Behemoth: seconds between screeches...
SCREECH_RADIUS = 3.5         # ...stunning the crew within this many tiles...
SCREECH_STUN = 2.2           # ...for this long
BONE_VOLLEY = 4              # Bone Tyrant: after each slam it strides off and throws this many bones...
BONE_VOLLEY_HURT = 6         # ...(this many below half health)...
BONE_THROW_SHARE = 0.12      # ...each hitting for this share of a typical crew member's health
BONE_THROW_SECS = 0.8        # (flight time)
THROW_ANIM_SECS = 0.5        # one throw: the arm swings back, then whips forward...
THROW_RELEASE = 0.6          # ...letting go of the bone this far through
VOLLEY_GAP = 0.15            # pause between throws
STRIDE_SPEED = 1.3           # tiles/s it strides off at, to get some distance...
STRIDE_RANGE = 3.5           # ...stopping about this far from the nearest crew member
STALK_PATIENCE = 8.0         # stalking this long without landing a slam, it throws a volley from where it stands
SLIME_SPLIT_AT = 0.5         # slimes burst apart at this share of their health...
SLIME_SPLIT_HP = 0.35        # ...into blobs with this share of the slime's max health each
CHUNK_SPLIT_HP = 0.8         # the Slime King's chunks share this much of his max health between them
CHUNK_WINDUP = 1.1           # a chunk's wind-up...
CHUNK_COOLDOWN = 3.0         # ...and its rest after slamming (a little random, so they don't slam together)
CHUNK_FLING = (2.5, 4.5)     # the split flings the chunks this far out across the board (tiles)...
CHUNK_FLING_SPEED = 7.0      # ...sliding there this fast, and lying there dazed this long once it lands...
CHUNK_DAZE = 1.5
CHUNK_APART = 1.2            # ...landing at least this far from each other...
CHUNK_CROWD = 2.5            # ...and each goes for a crew member the others aren't after (another chunk already on
                             # them counts as this many tiles further off)...
CHUNK_SPACE = 0.8            # ...and edges away from any other chunk closer than this, so their slams don't pile up
PILE_SECS = 5.0              # its first "death" leaves a bone pile: smash it within this long...
PILE_HP = 0.2                # ...(the pile has this share of its max health)...
REFORM_HP = 0.5              # ...or it pulls itself together with this share


def crew_hp_at(depth):
    """A typical crew member's health at this depth (with the Hard Hats a player has usually bought by then):
    what boss attacks are measured against, so they stay a threat all the way down."""
    return MINER_MAX_HP * (1 + 0.035 * min(depth, 60))


def boss_minion_cap(depth):
    """Minions a boss keeps on the board: 4 down to 20m, then a few more - 6 at 30m, 8 from 40m."""
    return min(BOSS_CROWD_CAP, BOSS_MAX_MINIONS + max(0, depth - BOSS_CROWD_FROM) // 5)


def boss_minion_mult(depth):
    """How many more minions each call brings than the boss's own count: 1x down to 20m, rising to 2x by 40m."""
    return 1 + min(1.0, max(0, depth - BOSS_CROWD_FROM) / 20)


def boss_for(depth):
    """The boss guarding this depth, or None if it isn't a boss depth."""
    if depth < BOSS_EVERY or depth % BOSS_EVERY:
        return None
    return BOSSES[(depth // BOSS_EVERY - 1) % len(BOSSES)]

GRIP_FROM = 10                # monsters' grabs hit as designed down to here, then harder with depth

# Waves: every spawn_interval(depth) seconds the board is topped up to max_enemies(depth).
ENEMY_START_DEPTH = 1          # monsters arrive the moment you reach this depth (none above it)
WAVE_INTERVAL_START = 15.0     # seconds between waves at ENEMY_START_DEPTH (small waves, often: a lively start)...
WAVE_INTERVAL_MIN = 20.0       # ...easing to this by WAVE_FASTEST_DEPTH, then staying there (bigger waves by then)
WAVE_FASTEST_DEPTH = 10
WAVE_HASTE = 0.75             # waves come this much sooner once you're deep, easing in from ENEMY_START_DEPTH...
WAVE_HASTE_DEPTH = 17         # ...to the full amount here
MAX_ENEMIES_CAP = 8           # monsters alive after a wave, reached at 21m...
DEEP_CAP = 12                 # ...then +1 every DEEP_CAP_EVERY metres, up to this (at 45m)...
DEEP_CAP_EVERY = 6
ABYSS_FROM = 70               # ...and again past here, +1 every DEEP_CAP_EVERY metres...
ABYSS_CAP = 16                # ...up to this (at 94m)
LURK_SECS = 18.0              # Mimic: springs by itself after sitting this long unnoticed
GOLEM_ARMOUR = 0.25           # Rock Golem: share of each hit that gets through its armour, until it's cracked
SHADE_RADIUS = 1.6            # Abyssal Shade: crew this close (tiles) are in its darkness...
SHADE_SLOW = 1.8              # ...and take this many times longer over each swing...
SHADE_DPS = 0.6               # ...while it eats at them this fast (scaled with depth like a grab; one shade's worth,
                              # however many they're standing under)
BRO_NAMES = ("Dig", "Delve")   # The Burrow Brothers: one fights above, the other tunnels below...
BRO_SWAP = 9.0                # ...and they swap this often...
BRO_MOUND_SPEED = 0.9         # ...the tunneller's mound creeping towards the crew this fast (tiles/s)...
BRO_SURFACE_RADIUS = 1.1      # ...and bursting up in a slam that hurts crew this close
BRO_PEEK_SECS = 1.5           # now and then the tunneller pops his head up out of the mound for this long...
BRO_PEEK_CHANCE = 0.5         # ...on this share of swaps (and always once early on, so you see there are two)
MOUNTAIN_ARMOUR = 0.1         # The Mountain: share of a blow that gets through while it still has plates
MOUNTAIN_HEAVE = 4            # ...and stone blocks its stomps heave up around it
VOID_GLANCE = 0.2             # The Void Maw: share of a blow that lands anywhere but its open eye...
VOID_EYE = 1.5                # ...and how hard a click on the open eye lands
VOID_EYE_OPEN, VOID_EYE_SHUT = 4.5, 1.5   # ...an eye stays open this long, then all blink shut this long
VOID_POOL_EVERY = 9.0         # ...a pool of darkness spreads under a crew member this often...
VOID_POOL_SECS = 24.0         # ...lasting this long (up to VOID_POOLS at once)
VOID_POOLS = 4
VOID_POOL_DRAIN = 0.02        # ...eating this share of a crew member's own max health a second (click one away)...
VOID_INHALE_EVERY = 22.0      # ...and this often it inhales: its eye flies open wide...
VOID_INHALE_SECS = 2.6        # ...and for this long it drags in crew within VOID_INHALE_RADIUS...
VOID_INHALE_RADIUS = 3.0
VOID_INHALE_PULL = 1.3        # ...at this many tiles a second...
VOID_BITE_RADIUS = 1.6        # ...then bites everyone this close for VOID_BITE of their own max health
VOID_BITE = 0.2               # (a blow to the open eye while it inhales chokes it: no bite)
ELITE_FROM = 25               # elite monsters: from this depth...
ELITE_CHANCE = (0.10, 0.25)   # ...this chance per wave monster, rising over ELITE_RAMP metres...
ELITE_RAMP = 25
ELITE_DEEP = 0.35             # ...then on up to this by 100m, from ABYSS_FROM
ELITE_HP = 4.0                # much tougher...
ELITE_GRIP = 1.6              # ...grab harder...
ELITE_BOUNTY = 4.0            # ...and pay more
ELITE_PCT_SCALE = 0.4         # they shrug off "share of max health" damage: this much of it lands
ELITE_SCALE = 1.35            # drawn this much bigger, in a red glow
HUMBLE_SECS = 0.5             # Cut Down to Size: how long an elite takes to shrink back


def spawn_interval(depth):
    t = (depth - ENEMY_START_DEPTH) / (WAVE_FASTEST_DEPTH - ENEMY_START_DEPTH)
    t = min(1.0, max(0.0, t))
    haste = min(1.0, max(0.0, (depth - ENEMY_START_DEPTH) / (WAVE_HASTE_DEPTH - ENEMY_START_DEPTH)))
    return (WAVE_INTERVAL_START + (WAVE_INTERVAL_MIN - WAVE_INTERVAL_START) * t) * (1 + (WAVE_HASTE - 1) * haste)


def max_enemies(depth):
    """Enemies alive after each wave: 1 at depth 1, +1 every 3 levels up to MAX_ENEMIES_CAP (at 21m), then +1
    every DEEP_CAP_EVERY metres up to DEEP_CAP."""
    cap = min(MAX_ENEMIES_CAP, 1 + depth // 3)
    if cap == MAX_ENEMIES_CAP:
        cap = min(DEEP_CAP, MAX_ENEMIES_CAP + max(0, depth - 21) // DEEP_CAP_EVERY)
    if depth > ABYSS_FROM:   # the deep gets busier again
        cap = min(ABYSS_CAP, DEEP_CAP + (depth - ABYSS_FROM) // DEEP_CAP_EVERY)
    return cap


def elite_chance(depth):
    """Chance a wave monster at this depth is an elite."""
    if depth < ELITE_FROM:
        return 0.0
    lo, hi = ELITE_CHANCE
    chance = lo + (hi - lo) * min(1.0, (depth - ELITE_FROM) / ELITE_RAMP)
    if depth > ABYSS_FROM:
        chance = hi + (ELITE_DEEP - hi) * min(1.0, (depth - ABYSS_FROM) / 30)
    return chance


def choose_kind(depth):
    options = [(k, s["weight"]) for k, s in ENEMY_TYPES.items() if s["weight"] > 0 and depth >= s["min_depth"]]
    if not options:
        return None
    return random.choices([k for k, _ in options], weights=[w for _, w in options])[0]


EDGE_CELLS = sorted({c for i in range(GRID) for c in ((i, 0), (i, GRID - 1), (0, i), (GRID - 1, i))})


def edge_cells(count):
    """`count` distinct random cells on the board's outer ring."""
    return random.sample(EDGE_CELLS, min(count, len(EDGE_CELLS)))


TELEGRAPH_SECS = 0.7   # warning before the enemy appears (cracks / silk strand / eyes in the dark)
ENTRANCE_SECS = 1.0    # the entrance animation itself
TRANSFORM_SECS = 0.8   # bat -> vampire smoke transformation


class Enemy:
    def __init__(self, kind, depth, cell, ground_z, delay=0.0, hp_mult=1.0, elite=False):
        self.depth = depth
        self.elite = elite            # a bigger, tougher, harder-gripping version (deep waves only)
        self.hp_mult = hp_mult        # (Zombie King's Crown)
        self.become(kind)
        self.x, self.y = cell[0] + 0.5, cell[1] + 0.5
        self.draw_z = ground_z
        self.state = "emerging"       # emerging | hunting | attacking | transforming
        self.timer = -delay           # state clock; negative = not started yet (staggered waves)
        self.victim = None
        self.grab_offset = (0.0, 0.0)
        self.facing = 1
        self.flash = 0.0              # white hit-flash timer
        self.anim_t = random.uniform(0, 10)
        self.flight_time = 0.0        # seconds spent flying free (drives bat -> vampire)
        self.hunt_time = 0.0          # seconds spent hunting (drives ghost phasing)
        self.heading = (1.0, 0.0)     # last movement direction in grid space (wisp trails)
        self.windup = 0.0             # boss: seconds until the slam lands (0 = not winding up)
        self.windup_total = BOSS_WINDUP   # boss: how long this wind-up lasts in all (shorter when enraged)
        self.cooldown = BOSS_SLAM_COOLDOWN   # boss: seconds before it can wind up again
        self.summon_timer = 4.0       # boss: seconds until it calls in minions
        self.fight_time = 0.0         # boss: seconds since it arrived (it retreats at BOSS_TIME_LIMIT)
        self.dmg_taken = 1.0          # share of incoming damage that lands (rallied zombies, shielded Archlich)
        self.enraged = False          # Zombie King: below ENRAGE_AT health
        self.mode = "stalk"           # Vampire Lord: stalk | bats (flying, untouchable) | bite
        self.trick_timer = 6.0        # seconds until the boss's own trick (bat form, curse)
        self.goal = None              # Vampire Lord: the crew member the swarm is flying at
        self.bite_hp = 0.0            # his health when the bite began (to tell when he's been hit enough)
        self.slam_at = None           # Fanged Behemoth: the spot it will dive onto when the wind-up ends
        self.reformed = False         # Bone Tyrant: already pulled itself back together once
        self.pile_timer = 0.0         # ...seconds left to smash its bone pile
        self.volley = 0               # ...bones left to throw in this volley
        self.throw_anim = 0.0         # ...seconds left of the current throw's animation
        self.throw_at = None          # ...the crew member this bone is for
        self.chunks = []              # Slime King: the chunks it burst into (the fight ends when they're all gone)
        if ENEMY_TYPES[kind]["entrance"] == "none":
            self.state = "burrowing" if ENEMY_TYPES[kind].get("burrow") else "hunting"
        self.plates = ENEMY_TYPES[kind].get("plates", 0)   # The Mountain: stone plates left
        self.eye, self.eye_timer = None, 2.0      # The Void Maw: which eye is open (None: all shut), and for how long...
        self.inhale = None                        # ...seconds into an inhale (None: not inhaling)...
        self.inhale_timer = VOID_INHALE_EVERY * 0.6   # ...and until the next one
        self.bro_hp = None                        # The Burrow Brothers: each brother's health...
        self.up = 0                               # ...which of them is above ground...
        self.mound = None                         # ...where the other's mound is, tunnelling...
        self.swap_timer = BRO_SWAP                # ...seconds until they swap...
        self.surface_t = 9.0                      # ...and since the one above burst up...
        self.peek = None                          # ...seconds into the tunneller popping up for a look (None: not)...
        self.peek_at = BRO_SWAP * 0.6             # ...and the swap_timer when he next does (None: not this time)
        self.tunnel_t = 0.0                       # Burrower: seconds spent tunnelling (Tremor Bells)
        self.etch = 0                             # Rock Golem: hits the acid has eaten into its armour (Acid Edge)
        self.humbled = None                       # an elite cut down to size: anim_t when it happened

    def become(self, kind):
        """Set the enemy type, with full health for that type at this depth."""
        spec = ENEMY_TYPES[kind]
        self.kind = kind
        self.max_hp = spec["hp"] * hp_scale(self.depth) * self.hp_mult * (ELITE_HP if self.elite else 1)
        self.hp = self.max_hp
        self.bounty_base = spec["bounty"] * 2 * value_scale(self.depth) * (ELITE_BOUNTY if self.elite else 1)

    @property
    def boss(self):
        return self.spec.get("boss", False)

    @property
    def draw_scale(self):
        """How much bigger than its regular sprite this one is drawn (bosses and elites), or None."""
        if self.humbled is not None and not self.boss:   # cut down to size: shrinking back to normal
            k = min(1.0, (self.anim_t - self.humbled) / HUMBLE_SECS)
            return ELITE_SCALE + (1 - ELITE_SCALE) * k if k < 1 else None
        return self.spec.get("scale") or (ELITE_SCALE if self.elite else None)

    @property
    def name(self):
        return ("Elite " if self.elite else "") + self.spec["name"]

    @property
    def pct_scale(self):
        """How much of any "share of max health" damage actually lands (bosses and elites resist it): guards,
        traps, the ballista, Self Defense, charges and Executioner's minimum all go through this."""
        if self.boss:
            return self.spec.get("pct_scale", BOSS_PCT_SCALE)
        return self.spec.get("pct_scale", ELITE_PCT_SCALE if self.elite and self.humbled is None else 1.0)

    @property
    def look(self):
        """The sprite this enemy is drawn with (the Zombie King borrows the zombie's, scaled up)."""
        return self.spec.get("look", self.kind)

    @property
    def spec(self):
        return ENEMY_TYPES[self.kind]

    @property
    def altitude(self):
        return self.spec.get("altitude", 0.0)

    @property
    def flying(self):
        return self.altitude > 0

    @property
    def phased(self):
        """Intangible right now (ghosts fade out for part of every cycle while hunting)."""
        phase = self.spec.get("phase")
        if not phase or self.state != "hunting" or getattr(self, "warded", False):   # Spirit Lantern
            return False
        return self.hunt_time % phase["every"] >= phase["every"] - phase["duration"]

    def entrance_progress(self):
        """<0 while waiting/telegraphing, 0..1 during the entrance animation, >=1 once done."""
        return (self.timer - TELEGRAPH_SECS) / ENTRANCE_SECS

    @property
    def targetable(self):
        return (self.state not in ("emerging", "transforming") and not self.phased
                and self.mode not in ("bats", "split"))

    def release(self):
        self.victim = None
        self.state = "hunting"

    def update(self, world, dt):
        self.anim_t += dt
        self.flash = max(0.0, self.flash - dt)
        ground = world.column_height(*world.cell_of(self.x, self.y))
        self.draw_z += (ground - self.draw_z) * min(1.0, dt * 10)

        if self.state == "emerging":   # spawn animation; the sprite code reads entrance_progress()
            before = self.timer
            self.timer += dt
            if before < TELEGRAPH_SECS <= self.timer:
                if self.spec["entrance"] == "dig":
                    world.enemy_burst(self)        # ground bursts open
                elif self.spec["entrance"] == "fade":
                    world.enemy_materialise(self)  # puff of cold mist
            if self.timer >= TELEGRAPH_SECS + ENTRANCE_SECS:
                self.state = "hunting"
                if self.spec["entrance"] == "drop":
                    world.enemy_landed(self)   # thud on landing
            return

        if self.state == "transforming":
            self.timer += dt
            if self.timer >= TRANSFORM_SECS:
                self.state = "hunting"
            return

        if self.state == "burrowing":   # Burrower: tunnelling under the blocks towards a miner
            if world.tremor_bells(self, dt):
                return
            target = world.nearest_free_miner(self.x, self.y)
            if target is None:
                return
            if math.hypot(target.x - self.x, target.y - self.y) <= self.spec["reach"]:
                world.surface_burrower(self, target)
            else:
                self.step_to(target.x, target.y, dt)
            return

        if self.state == "lurking":   # Mimic: sitting on its block, passing for a treasure chest
            self.timer += dt
            if self.lurk_cell not in world.current or self.timer >= LURK_SECS:
                world.spring_mimic(self)
            return

        if self.boss:
            self.update_boss(world, dt)
            return
        if self.spec.get("slam"):   # a Slime King chunk: a little slammer of its own
            self.update_chunk(world, dt)
            return
        hatch = self.spec.get("hatch")
        if hatch:
            self.timer += dt
            if self.timer >= hatch["after"]:
                world.hatch(self)
            return

        if self.state == "attacking":
            v = self.victim
            if v is None or v.state != "grabbed" or v.attacker is not self:
                self.release()
                return
            self.x, self.y = v.x + self.grab_offset[0], v.y + self.grab_offset[1]
            # the grip tightens past GRIP_FROM metres: drains keep pace with a typical crew member's health
            dps = self.spec["dps"] * max(1.0, crew_hp_at(self.depth) / crew_hp_at(GRIP_FROM))
            if self.elite and self.humbled is None:
                dps *= ELITE_GRIP
            dps *= world.grip_ward(self)   # (Garlic Garlands, Torches)
            drained = min(v.hp, dps * dt * world.art_mult("grab_dmg"))   # (Broodmother's Silk)
            v.hp -= drained
            v.last_hurt = world.clock
            if self.spec.get("lifesteal"):
                heal = drained / v.max_hp * self.max_hp * self.spec["lifesteal"] * world.grip_ward(self)
                self.hp = min(self.max_hp, self.hp + heal)
                world.blood_drip(v, self)
            if v.hp <= 0:
                world.miner_down(v, killer=self)
                self.release()
            return

        # hunting
        self.hunt_time += dt
        transform = self.spec.get("transform")
        if transform and self.depth >= transform["min_depth"]:
            self.flight_time += dt
            if self.flight_time >= transform["after"] * world.turn_delay():   # (Garlic Garlands)
                world.transform_enemy(self, transform["into"])
                return
        if self.spec.get("aura"):   # Abyssal Shade: drift to where the crew are thickest; it never grabs
            tx, ty = world.shade_target(self)
            if math.hypot(tx - self.x, ty - self.y) > 0.15:
                self.step_to(tx, ty, dt)
            return
        dummy = world.lure(self)   # (Wren's Target Dummy: close by, it's the first thing they go for)
        if dummy:
            if math.hypot(dummy.x - self.x, dummy.y - self.y) <= self.spec["reach"] + 0.15:
                world.dummy_grabbed(dummy, self)
            else:
                self.step_to(dummy.x, dummy.y, dt)
            return
        target = world.nearest_free_miner(self.x, self.y)
        if not target:
            return
        if math.hypot(target.x - self.x, target.y - self.y) <= self.spec["reach"]:
            self.facing = 1 if (target.x - self.x) - (target.y - self.y) >= 0 else -1
            world.grab(self, target)
            return
        self.step_to(target.x, target.y, dt)

    def step_to(self, tx, ty, dt):
        """Move towards (tx, ty) at its speed (zig-zagging if it flies that way)."""
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        self.facing = 1 if (dx - dy) >= 0 else -1
        ux, uy = dx / dist, dy / dist
        wob = self.spec.get("wobble")
        if wob and dist > 0.8:   # zig-zag flight
            wobble = math.sin(self.anim_t * wob["freq"]) * wob["amount"]
            ux, uy = ux - uy * wobble, uy + ux * wobble
            norm = math.hypot(ux, uy)
            ux, uy = ux / norm, uy / norm
        self.heading = (ux, uy)
        step = min(dist, self.spec["speed"] * getattr(self, "speed_mult", 1.0) * dt)   # (Spirit Lantern)
        self.x = min(GRID - 0.05, max(0.05, self.x + ux * step))
        self.y = min(GRID - 0.05, max(0.05, self.y + uy * step))

    def update_boss(self, world, dt):
        """Stalk the nearest crew member, wind up, slam the ground around itself; call in minions."""
        self.hunt_time += dt
        self.fight_time += dt
        if self.fight_time >= world.boss_time_limit():
            world.boss_retreat(self)
            return
        if self.mode == "split":   # the Slime King in pieces: its chunks do the fighting
            world.update_split_boss(self)
            return
        self.summon_timer -= dt
        if self.summon_timer <= 0:
            self.summon_timer = self.spec["minion"]["every"]
            world.boss_summon(self)
        if world.boss_special(self, dt):   # busy with its own trick (flying as bats, feeding)
            return
        pace = ENRAGE_PACE if self.enraged else 1.0
        if self.windup > 0:   # rooted to the spot, about to slam (or, diving, about to swoop)
            if self.slam_at and self.windup <= DIVE_SECS:
                tx, ty = self.slam_at
                share = min(1.0, dt / max(self.windup, dt))
                self.x += (tx - self.x) * share
                self.y += (ty - self.y) * share
            self.windup -= dt
            if self.windup <= 0:
                self.windup = 0.0
                self.cooldown = BOSS_SLAM_COOLDOWN * pace
                world.boss_slam(self)
                self.slam_at = None
            return
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.spec.get("dive"):
            self.hover_and_dive(world, dt, pace)
            return
        target = world.nearest_crew(self.x, self.y)
        if not target:
            return
        dx, dy = target.x - self.x, target.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0.03:
            self.facing = 1 if (dx - dy) >= 0 else -1
        if dist <= self.spec["reach"]:
            if self.cooldown <= 0:
                self.windup = self.windup_total = BOSS_WINDUP * pace
                world.cues.append("windup")   # the boss strains (its growl)
            return
        ux, uy = dx / dist, dy / dist
        self.heading = (ux, uy)
        step = min(dist - self.spec["reach"] * 0.8, self.spec["speed"] * getattr(self, "speed_mult", 1.0) * dt)
        self.x = min(GRID - 0.05, max(0.05, self.x + ux * step))
        self.y = min(GRID - 0.05, max(0.05, self.y + uy * step))

    def update_chunk(self, world, dt):
        """A Slime King chunk: flung out across the board by the split, it creeps up to a crew member of its own
        (not one the other chunks are after), winds up and slams (smaller than the King's)."""
        self.hunt_time += dt
        fling = getattr(self, "fling_to", None)
        if fling:   # still sliding out to where the split threw it
            dx, dy = fling[0] - self.x, fling[1] - self.y
            dist = math.hypot(dx, dy)
            if dist <= CHUNK_FLING_SPEED * dt:
                self.x, self.y, self.fling_to = fling[0], fling[1], None
                self.daze = CHUNK_DAZE
                world.chunk_landed(self)
            else:
                self.x += dx / dist * CHUNK_FLING_SPEED * dt
                self.y += dy / dist * CHUNK_FLING_SPEED * dt
            return
        if self.windup > 0:
            self.windup -= dt
            if self.windup <= 0:
                self.windup = 0.0
                self.cooldown = CHUNK_COOLDOWN * random.uniform(0.8, 1.3)
                world.chunk_slam(self)
            return
        if getattr(self, "daze", 0) > 0:   # (flung across the board: a moment to pull itself together)
            self.daze -= dt
            return
        self.cooldown = max(0.0, self.cooldown - dt)
        target = world.chunk_target(self)
        if not target:
            return
        dx, dy = target.x - self.x, target.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0.03:
            self.facing = 1 if (dx - dy) >= 0 else -1
        if dist <= self.spec["reach"]:
            if self.cooldown <= 0:
                self.windup = self.windup_total = CHUNK_WINDUP
            return
        step = min(dist - self.spec["reach"] * 0.8, self.spec["speed"] * getattr(self, "speed_mult", 1.0) * dt)
        mx, my = dx / dist * step, dy / dist * step
        for other in world.enemies:   # (and edging away from any chunk it's bumping into)
            if other is not self and other.kind == self.kind:
                ox, oy = self.x - other.x, self.y - other.y
                gap = math.hypot(ox, oy)
                if 0.001 < gap < CHUNK_SPACE:
                    push = (CHUNK_SPACE - gap) / CHUNK_SPACE * self.spec["speed"] * dt
                    mx, my = mx + ox / gap * push, my + oy / gap * push
        self.x = min(GRID - 0.05, max(0.05, self.x + mx))
        self.y = min(GRID - 0.05, max(0.05, self.y + my))

    def hover_and_dive(self, world, dt, pace):
        """A flying boss: drift about over the board, and when ready mark a crew member's spot to dive onto."""
        if self.cooldown <= 0:
            crew = [m for m in world.miners if m.state != "down"]
            if crew:
                target = random.choice(crew)
                self.slam_at = (target.x, target.y)
                self.windup = self.windup_total = BOSS_WINDUP * pace
                world.cues.append("windup")   # the boss strains (its growl)
                return
        if self.goal is None or math.hypot(self.goal[0] - self.x, self.goal[1] - self.y) < 0.2:
            self.goal = (random.uniform(1.5, GRID - 1.5), random.uniform(1.5, GRID - 1.5))
        dx, dy = self.goal[0] - self.x, self.goal[1] - self.y
        dist = math.hypot(dx, dy)
        if dist > 0.03:
            self.facing = 1 if (dx - dy) >= 0 else -1
            step = min(dist, self.spec["speed"] * dt)
            self.x += dx / dist * step
            self.y += dy / dist * step
